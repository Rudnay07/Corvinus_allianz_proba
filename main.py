from __future__ import annotations

import io
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from google import genai
except ImportError:  # App can still run without AI configured/installed during setup.
    genai = None

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
PORT = int(os.getenv("PORT", "3000"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Startup Intelligence API", version="1.0.0")
origin = os.getenv("CORS_ORIGIN", "").strip()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin] if origin else ["*"],
    allow_credentials=bool(origin),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)
startups: list[dict[str, Any]] = []
last_import: dict[str, Any] | None = None


def number(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)) or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace("\u00a0", "").replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def text(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and not (isinstance(value, float) and math.isnan(value)):
            return str(value).strip()
    return ""


def normalize_row(row: dict) -> dict[str, Any]:
    return {
        "id": text(row, "Startup ID", "ID", "id"),
        "name": text(row, "Cégnév", "name", "Név"),
        "sector": text(row, "Szektor", "sector"),
        "city": text(row, "Város", "city"),
        "founded": text(row, "Alapítás", "founded"),
        "stage": text(row, "Finanszírozási fázis", "stage"),
        "employees": number(row.get("Munkavállalók (fő)", row.get("employees"))),
        "customers": number(row.get("Ügyfelek száma", row.get("customers"))),
        "revenue2023": number(row.get("Árbevétel 2023 (M Ft)", row.get("revenue2023"))),
        "revenue2024": number(row.get("Árbevétel 2024 (M Ft)", row.get("revenue2024"))),
        "revenue2025": number(row.get("Árbevétel 2025 (M Ft)", row.get("revenue2025"))),
        "growth": number(row.get("Éves növekedés 2025 (%)", row.get("growth"))),
        "grossMargin": number(row.get("Bruttó árrés (%)", row.get("grossMargin"))),
        "grossProfit": number(row.get("Bruttó eredmény 2025 (M Ft)", row.get("grossProfit"))),
        "ebitda": number(row.get("EBITDA 2025 (M Ft)", row.get("ebitda"))),
        "ebitdaMargin": number(row.get("EBITDA-marzs (%)", row.get("ebitdaMargin"))),
        "funding": number(row.get("Összes bevont tőke (M Ft)", row.get("funding"))),
        "valuation": number(row.get("Becsült értékelés (M Ft)", row.get("valuation"))),
        "cash": number(row.get("Készpénzállomány (M Ft)", row.get("cash"))),
        "burn": number(row.get("Havi cash burn (M Ft)", row.get("burn"))),
        "runway": number(row.get("Runway (hónap)", row.get("runway"))),
        "debt": number(row.get("Adósság (M Ft)", row.get("debt"))),
        "churn": number(row.get("Ügyféllemorzsolódás (%)", row.get("churn"))),
    }


def clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


# A pontozás alapértelmezett súlyai (összegük 1.0). A felületen és a végpontokon
# felülírhatók; a tényleges számítás a súlyok összegével normalizál, így a részarányok
# tetszőleges értékek is lehetnek – a 0–100 skála mindig megmarad.
WEIGHT_KEYS = ("growth", "ebitda", "grossMargin", "runway", "retention", "funding")
DEFAULT_WEIGHTS: dict[str, float] = {
    "growth": 0.25,
    "ebitda": 0.20,
    "grossMargin": 0.15,
    "runway": 0.20,
    "retention": 0.10,
    "funding": 0.10,
}


def score_components(s: dict[str, Any]) -> dict[str, float]:
    """Az egyes mutatók 0–100 skálára normalizált részpontszámai.

    A konstansok magyarázata (demonstrációs modell, a beadandóban validálandó):
    - growth:     +10 eltolás a kis negatív növekedés kezelésére, /1.2 skálázás.
    - ebitda:     az EBITDA-marzs +30 eltolással és *2 szorzóval 0–100 közé emelve.
    - grossMargin: a bruttó árrés százaléka közvetlenül (0–100).
    - runway:     24 hónap runway = 100 pont (afölött telített).
    - retention:  1% lemorzsolódás 8 pont levonást jelent a 100-ból.
    - funding:    a bevont tőke logaritmikus skálán (a nagyságrend számít, nem a pontos összeg).
    """
    return {
        "growth": clamp((s["growth"] + 10) / 1.2),
        "ebitda": clamp((s["ebitdaMargin"] + 30) * 2),
        "grossMargin": clamp(s["grossMargin"]),
        "runway": clamp(s["runway"] / 24 * 100),
        "retention": clamp(100 - s["churn"] * 8),
        "funding": clamp(math.log10(max(1, s["funding"]) + 1) * 25),
    }


def risk_of(s: dict[str, Any]) -> str:
    return "Magas" if s["runway"] < 6 or (s["ebitda"] < 0 and s["burn"] > 30) or s["churn"] > 9 else (
        "Közepes" if s["runway"] < 12 or s["ebitda"] < 0 or s["churn"] > 6 else "Alacsony")


def enrich(startup: dict[str, Any], weights: dict[str, float] | None = None) -> dict[str, Any]:
    w = weights or DEFAULT_WEIGHTS
    s = dict(startup)
    components = score_components(s)
    total = sum(w.get(k, 0.0) for k in WEIGHT_KEYS) or 1.0
    s["components"] = {k: round(components[k], 1) for k in WEIGHT_KEYS}
    s["score"] = round(sum(components[k] * w.get(k, 0.0) for k in WEIGHT_KEYS) / total, 1)
    s["risk"] = risk_of(s)
    return s


def resolve_weights(**provided: float | None) -> dict[str, float]:
    """A query-paraméterként kapott súlyokat egészíti ki alapértelmezettekkel és
    védi a negatív / csupa nulla bemenettől."""
    w = {k: (DEFAULT_WEIGHTS[k] if provided.get(k) is None else max(0.0, float(provided[k]))) for k in WEIGHT_KEYS}
    return w if sum(w.values()) > 0 else dict(DEFAULT_WEIGHTS)


def weights_percent(w: dict[str, float]) -> dict[str, float]:
    """A súlyokat 100-ra normalizált százalékként adja vissza megjelenítéshez."""
    total = sum(w.values()) or 1.0
    return {k: round(w[k] / total * 100, 1) for k in WEIGHT_KEYS}


def rank_startups(weights: dict[str, float]) -> list[dict[str, Any]]:
    return sorted((enrich(s, weights) for s in startups), key=lambda item: item["score"], reverse=True)


def require_data() -> None:
    if not startups:
        raise HTTPException(status_code=409, detail="Még nincs startup-adatbázis. Először tölts fel egy Excel-fájlt.")


def get_gemini_client():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or genai is None:
        return None
    return genai.Client(api_key=key)


class ChatRequest(BaseModel):
    message: str | None = None
    question: str | None = None


class CompareRequest(BaseModel):
    ids: list[str] = Field(min_length=2, max_length=10)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Startup Intelligence API", "geminiConfigured": bool(os.getenv("GEMINI_API_KEY")), "model": MODEL, "startupCount": len(startups)}


@app.get("/api/settings/status")
def settings_status():
    return {"provider": "Google Gemini", "configured": bool(os.getenv("GEMINI_API_KEY")), "model": MODEL}


@app.post("/api/startups/import")
async def import_startups(file: UploadFile = File(...)):
    global startups, last_import
    filename = file.filename or ""
    if Path(filename).suffix.lower() not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Csak .xlsx vagy .xls fájl tölthető fel.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="A fájl mérete legfeljebb 10 MB lehet.")
    try:
        frame = pd.read_excel(io.BytesIO(content), sheet_name=0).fillna("")
        parsed = [normalize_row(row) for row in frame.to_dict(orient="records")]
        parsed = [item for item in parsed if item["name"]]
        if not parsed:
            raise HTTPException(status_code=422, detail="Nem található feldolgozható startup-adat az első munkalapon.")
        for index, item in enumerate(parsed, start=1):
            if not item["id"]:
                item["id"] = f"ST{index:04d}"
        startups = [enrich(item) for item in parsed]
        last_import = {"filename": filename, "importedAt": datetime.now(timezone.utc).isoformat(), "count": len(startups)}
        return {"message": "Import sikeres.", "count": len(startups), "import": last_import}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Nem sikerült beolvasni az Excelt: {exc}") from exc


@app.get("/api/startups")
def list_startups(search: str = "", sector: str = "", limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    require_data()
    filtered = [s for s in startups if (not search or search.lower() in f"{s['name']} {s['sector']} {s['city']}".lower()) and (not sector or s["sector"].lower() == sector.lower())]
    return {"total": len(filtered), "limit": limit, "offset": offset, "data": filtered[offset:offset + limit]}


@app.get("/api/startups/{startup_id}")
def get_startup(startup_id: str):
    require_data()
    item = next((s for s in startups if s["id"] == startup_id or s["name"] == startup_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="A startup nem található.")
    return item


@app.get("/api/analysis/summary")
def summary(
    growth: float | None = Query(None, ge=0),
    ebitda: float | None = Query(None, ge=0),
    grossMargin: float | None = Query(None, ge=0),
    runway: float | None = Query(None, ge=0),
    retention: float | None = Query(None, ge=0),
    funding: float | None = Query(None, ge=0),
):
    require_data()
    weights = resolve_weights(growth=growth, ebitda=ebitda, grossMargin=grossMargin, runway=runway, retention=retention, funding=funding)
    ranked = rank_startups(weights)
    sectors: dict[str, int] = {}
    for item in startups:
        sectors[item["sector"]] = sectors.get(item["sector"], 0) + 1
    return {"startupCount": len(startups), "totalRevenue2025": round(sum(s["revenue2025"] for s in startups), 1), "averageGrowth": round(sum(s["growth"] for s in startups) / len(startups), 1), "topStartup": ranked[0], "top5": ranked[:5], "sectorCounts": sectors, "scoringWeights": weights_percent(weights), "lastImport": last_import}


@app.get("/api/analysis/ranking")
def ranking(
    limit: int = Query(10, ge=1, le=1000),
    growth: float | None = Query(None, ge=0),
    ebitda: float | None = Query(None, ge=0),
    grossMargin: float | None = Query(None, ge=0),
    runway: float | None = Query(None, ge=0),
    retention: float | None = Query(None, ge=0),
    funding: float | None = Query(None, ge=0),
):
    require_data()
    weights = resolve_weights(growth=growth, ebitda=ebitda, grossMargin=grossMargin, runway=runway, retention=retention, funding=funding)
    return {"weights": weights_percent(weights), "data": rank_startups(weights)[:limit]}


@app.post("/api/compare")
def compare(payload: CompareRequest):
    require_data()
    found = [next((s for s in startups if s["id"] == str(item_id)), None) for item_id in payload.ids]
    if any(item is None for item in found):
        raise HTTPException(status_code=404, detail="Legalább egy megadott startup ID nem található.")
    return {"data": found}


async def answer_with_gemini(question: str):
    require_data()
    client = get_gemini_client()
    if client is None:
        raise HTTPException(status_code=503, detail="A Gemini API nincs konfigurálva. Állítsd be a GEMINI_API_KEY változót a .env fájlban, és telepítsd a google-genai csomagot.")
    context = [{k: s.get(k) for k in ("id", "name", "sector", "revenue2025", "growth", "grossMargin", "ebitda", "ebitdaMargin", "funding", "valuation", "cash", "burn", "runway", "debt", "customers", "churn", "score", "risk")} for s in startups]
    prompt = ("Te egy pénzügyi elemző asszisztens vagy. Kizárólag az alábbi feltöltött szintetikus startup-adatokból dolgozz. "
              "Ne találj ki adatot; hiányzó adatnál jelezd. A pontszám döntéstámogató becslés, nem befektetési tanács. "
              "Válaszolj magyarul, számokkal és indoklással.\n\nADATOK JSON-BAN:\n" + json.dumps(context, ensure_ascii=False) + "\n\nKÉRDÉS:\n" + question)
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return {"answer": response.text or "Nem érkezett szöveges válasz.", "model": MODEL}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"A Gemini kérés sikertelen: {exc}") from exc


@app.post("/api/analysis/ask")
async def ask(payload: ChatRequest):
    question = (payload.question or payload.message or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="A kérdés megadása kötelező.")
    return await answer_with_gemini(question)


@app.post("/api/chat")
async def chat(payload: ChatRequest):
    question = (payload.message or payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="A kérdés megadása kötelező.")
    return await answer_with_gemini(question)


@app.get("/")
def frontend():
    index = PUBLIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Startup Intelligence API"}
