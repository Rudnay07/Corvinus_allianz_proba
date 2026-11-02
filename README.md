<div align="center">

# 📊 Startup Intelligence

**AI-alapú döntéstámogató rendszer startupok pénzügyi értékelésére**

Egyetemi projekt · 1000 fiktív startup · Python + FastAPI + Google Gemini

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/célja-oktatási-b7791f)

</div>

---

## Tartalomjegyzék

- [Áttekintés](#áttekintés)
- [Főbb funkciók](#főbb-funkciók)
- [Technológiai stack](#technológiai-stack)
- [Projektstruktúra](#projektstruktúra)
- [Telepítés és indítás](#telepítés-és-indítás)
- [Konfiguráció](#konfiguráció)
- [Adatmodell](#adatmodell)
- [API-végpontok](#api-végpontok)
- [Pontozási módszertan](#pontozási-módszertan)
- [Érzékenységvizsgálat](#érzékenységvizsgálat)
- [Korlátok és továbbfejlesztés](#korlátok-és-továbbfejlesztés)
- [Biztonság](#biztonság)
- [Jogi megjegyzés](#jogi-megjegyzés)

---

## Áttekintés

A **Startup Intelligence** egy döntéstámogató webalkalmazás, amely **1000 fiktív startup** gazdasági és pénzügyi adatait dolgozza fel, majd egy **súlyozott, paraméterezhető pontozási modell** és a **Google Gemini** nyelvi modell segítségével rangsorolja és értelmezi a vállalatokat.

A rendszer célja annak megválaszolása, hogy a megadott pénzügyi szempontok alapján **mely startupok tekinthetők a legígéretesebbnek** — nem pusztán az árbevétel, hanem a növekedés, a jövedelmezőség, a pénzügyi tartalék, az ügyfélmegtartás és a finanszírozási háttér együttes mérlegelésével.

> A pontszám döntéstámogató, demonstrációs célú becslés. **Nem befektetési tanács.** A vállalatok és az adatok mesterségesen generáltak.

---

## Főbb funkciók

| Funkció | Leírás |
|---|---|
| 📥 **Excel-import** | 1000 soros `.xlsx`/`.xls` adatbázis feltöltése, automatikus tisztítással és normalizálással |
| 📈 **Súlyozott pontozás** | 6 pénzügyi mutatóból képzett, 0–100 skálás összetett pontszám |
| 🎛️ **Paraméterezhető súlyok** | A pontozási súlyok a felületen és az API-n is **élőben átállíthatók** |
| 🏆 **Rangsor** | Pontszám szerinti rangsorolás, kockázati besorolással |
| ⚖️ **Összehasonlítás** | Két vagy több startup egymás melletti összevetése |
| 🤖 **AI-asszisztens** | Természetes nyelvű kérdések a feltöltött adatbázisról (Gemini) |
| 📊 **Dashboard** | Összesítő mutatók, top 5, szektormegoszlás |

---

## Technológiai stack

| Réteg | Technológia |
|---|---|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **Adatfeldolgozás** | pandas, openpyxl, xlrd |
| **AI** | Google Gemini (`google-genai`), alapértelmezett modell: `gemini-2.5-flash` |
| **Frontend** | Statikus HTML / CSS / vanilla JavaScript (keretrendszer nélkül) |
| **Konfiguráció** | `python-dotenv` (`.env`) |

---

## Projektstruktúra

```
Corvinus_allianz_proba/
├── main.py                       # FastAPI backend: import, pontozás, API-végpontok
├── public/
│   └── index.html                # Egyoldalas frontend (dashboard, chat, rangsor)
├── startup_adatok_1000_db.xlsx   # 1000 fiktív startup tesztadatbázis
├── requirements.txt              # Python-függőségek
├── .env                          # Környezeti változók (API-kulcs)
└── README.md
```

---

## Telepítés és indítás

> **Követelmény:** Python 3.10 vagy újabb, valamint egy Google AI Studio Gemini API-kulcs (az AI-funkciókhoz).

```bash
# 1. Virtuális környezet létrehozása és aktiválása
python -m venv .venv

#    Windows (PowerShell):
.venv\Scripts\Activate.ps1
#    macOS / Linux:
source .venv/bin/activate

# 2. Függőségek telepítése
pip install -r requirements.txt

# 3. API-kulcs beállítása (lásd a Konfiguráció szakaszt)

# 4. Szerver indítása
uvicorn main:app --reload --host 127.0.0.1 --port 3000
```

Ezután elérhető:

- 🌐 **Alkalmazás:** <http://127.0.0.1:3000>
- 📚 **Interaktív API-dokumentáció (Swagger):** <http://127.0.0.1:3000/docs>

**Használat:** `Adatimport` menü → töltsd fel a `startup_adatok_1000_db.xlsx` fájlt → `Elemzések és rangsor` vagy `AI asszisztens` menüben vizsgáld az eredményeket.

---

## Konfiguráció

A beállításokat a projekt gyökerében lévő **`.env`** fájl tartalmazza:

```ini
# Kötelező az AI-funkciókhoz – Google AI Studio: https://aistudio.google.com/apikey
GEMINI_API_KEY=ide_masold_a_valodi_kulcsot

# Opcionális
GEMINI_MODEL=gemini-2.5-flash   # használt Gemini modell
PORT=3000                       # szerver port
CORS_ORIGIN=                    # ha üres, minden origin engedélyezett (demó)
```

| Változó | Alapértelmezett | Szerep |
|---|---|---|
| `GEMINI_API_KEY` | – | Gemini hitelesítés (nélküle az AI-végpontok `503`-at adnak) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | A használt nyelvi modell |
| `PORT` | `3000` | A szerver portja |
| `CORS_ORIGIN` | `*` | Engedélyezett origin(ek) |

> Az AI-funkciók nélkül is **minden más működik** (import, pontozás, rangsor, összehasonlítás) — a Gemini csak a természetes nyelvű chathez kell.

---

## Adatmodell

A rendszer az Excel **első munkalapját** olvassa be; a mezőnevek a magyar startup-adatbázis oszlopaihoz igazodnak (angol fallback kulcsokkal). Az összes pénzügyi érték **millió forintban (M Ft)** értendő.

| Excel-oszlop | Belső mező | Típus |
|---|---|---|
| Startup ID | `id` | szöveg |
| Cégnév | `name` | szöveg |
| Szektor | `sector` | szöveg |
| Város | `city` | szöveg |
| Alapítás | `founded` | szöveg |
| Finanszírozási fázis | `stage` | szöveg |
| Munkavállalók (fő) | `employees` | szám |
| Ügyfelek száma | `customers` | szám |
| Árbevétel 2023 / 2024 / 2025 (M Ft) | `revenue2023/24/25` | szám |
| Éves növekedés 2025 (%) | `growth` | szám |
| Bruttó árrés (%) | `grossMargin` | szám |
| Bruttó eredmény 2025 (M Ft) | `grossProfit` | szám |
| EBITDA 2025 (M Ft) | `ebitda` | szám |
| EBITDA-marzs (%) | `ebitdaMargin` | szám |
| Összes bevont tőke (M Ft) | `funding` | szám |
| Becsült értékelés (M Ft) | `valuation` | szám |
| Készpénzállomány (M Ft) | `cash` | szám |
| Havi cash burn (M Ft) | `burn` | szám |
| Runway (hónap) | `runway` | szám |
| Adósság (M Ft) | `debt` | szám |
| Ügyféllemorzsolódás (%) | `churn` | szám |

---

## API-végpontok

| Metódus | Végpont | Funkció |
|---|---|---|
| `GET` | `/api/health` | Szerver- és Gemini-állapot |
| `GET` | `/api/settings/status` | AI-szolgáltató állapota (kulcs nélkül) |
| `POST` | `/api/startups/import` | Excel feltöltése (`multipart/form-data`, `file`) |
| `GET` | `/api/startups` | Lista: `search`, `sector`, `limit` (max 1000), `offset` |
| `GET` | `/api/startups/{id}` | Egy startup részletei |
| `GET` | `/api/analysis/summary` | Dashboard-összesítő és top 5 |
| `GET` | `/api/analysis/ranking` | Pontszám szerinti rangsor (**súlyparaméterekkel**) |
| `POST` | `/api/compare` | Startupok összehasonlítása: `{"ids":["ST0001","ST0002"]}` |
| `POST` | `/api/analysis/ask` | Gemini-elemzés: `{"question":"..."}` |
| `POST` | `/api/chat` | Chat: `{"message":"..."}` |

### Paraméterezhető rangsor

A `/api/analysis/ranking` és a `/api/analysis/summary` opcionális **súly-query-paramétereket** fogad. A rendszer a megadott súlyokat automatikusan normalizálja, így nem kell pontosan 100%-ot kiadniuk, és a pontszám mindig a 0–100 tartományban marad.

```http
GET /api/analysis/ranking?growth=40&ebitda=25&grossMargin=10&runway=10&retention=10&funding=5
```

A válasz tartalmazza a ténylegesen alkalmazott (normalizált) súlyokat is:

```json
{
  "weights": { "growth": 40.0, "ebitda": 25.0, "grossMargin": 10.0, "runway": 10.0, "retention": 10.0, "funding": 5.0 },
  "data": [ { "id": "ST0001", "name": "...", "score": 72.4, "risk": "Alacsony", "components": { ... } } ]
}
```

---

## Pontozási módszertan

Minden startup egy **0–100 közötti összetett pontszámot** kap, amely hat részmutató súlyozott átlaga. Az egyes mutatók először egy 0–100 skálás **részpontszámmá** normalizálódnak, majd súlyozottan összegződnek.

### 1. Részpontszámok

| Mutató | Normalizálás | Logika |
|---|---|---|
| **Növekedés** | `clamp((growth + 10) / 1.2)` | +10 eltolás a kis negatív növekedés kezelésére; 110% növekedés = 100 pont |
| **EBITDA-marzs** | `clamp((ebitdaMargin + 30) × 2)` | −30% marzs = 0, +20% marzs = 100 pont |
| **Bruttó árrés** | `clamp(grossMargin)` | a százalékos árrés közvetlenül |
| **Runway** | `clamp(runway / 24 × 100)` | 24 hónap tartalék = 100 pont |
| **Ügyfélmegtartás** | `clamp(100 − churn × 8)` | 1% lemorzsolódás = −8 pont |
| **Finanszírozás** | `clamp(log₁₀(funding + 1) × 25)` | logaritmikus: a nagyságrend számít, nem a pontos összeg |

*(`clamp` = 0 és 100 közé szorítás.)*

### 2. Alapértelmezett súlyok

| Mutató | Súly | Pénzügyi értelmezés |
|---|---|---|
| Növekedés | **25%** | Üzleti lendület, piaci elfogadottság |
| EBITDA-marzs | **20%** | Működési jövedelmezőség |
| Bruttó árrés | **15%** | Az üzleti modell fedezettermelő képessége |
| Runway | **20%** | Pénzügyi stabilitás, túlélőképesség |
| Ügyfélmegtartás | **10%** | Bevételi fenntarthatóság |
| Finanszírozás | **10%** | Tőkeerő, befektetői bizalom |

A súlyok a felületen (`Elemzések és rangsor` nézet) és az API-n át szabadon átállíthatók.

### 3. Kockázati besorolás

| Szint | Feltétel |
|---|---|
| 🔴 **Magas** | runway < 6 hó, **vagy** (negatív EBITDA **és** havi burn > 30 M Ft), **vagy** churn > 9% |
| 🟡 **Közepes** | runway < 12 hó, **vagy** negatív EBITDA, **vagy** churn > 6% |
| 🟢 **Alacsony** | minden más esetben |

### 4. A tesztadatbázis jellemzői

Az `startup_adatok_1000_db.xlsx` 1000 során mért eloszlás:

| Mutató | Min | Medián | Max |
|---|---:|---:|---:|
| Éves növekedés (%) | −14,8 | 63,5 | 139,4 |
| EBITDA-marzs (%) | −45,0 | −8,2 | 32,0 |
| Bruttó árrés (%) | 28,0 | 60,8 | 91,8 |
| Runway (hónap) | 0,4 | 19,6 | 680,7 |
| Ügyféllemorzsolódás (%) | 1,0 | 7,9 | 15,0 |
| Bevont tőke (M Ft) | 5,1 | 218,4 | 5914,5 |

**Módszertani megjegyzések (a beadandóban érdemes kiemelni):**

- A startupok **~60%-ának negatív az EBITDA-marzsa** — ez korai fázisú mintánál reális, és indokolja, hogy a jövedelmezőség mellett a növekedés és a runway is hangsúlyt kapjon.
- A **runway részpontszáma a minta ~39%-ánál telítődik** (24 hónap felett), mert a medián 19,6 hó, a maximum viszont 680 hó. A felső tartományban a runway kevéssé differenciál; ez a 24 hónapos vágási küszöb felemelésével (pl. 36 hó) vagy a súly csökkentésével orvosolható.
- A normalizálási konstansok **demonstrációs jellegűek**; éles használatban percentilis- vagy min-max-alapú normalizálás javasolt a tényleges eloszlásból.

---

## Érzékenységvizsgálat

Mivel a súlyok paraméterezhetők, a rangsor **stabilitása** közvetlenül vizsgálható — ez pénzügyi szempontból a modell egyik legfontosabb validációja:

1. Nyisd meg az `Elemzések és rangsor` nézetet.
2. Állítsd be a kiinduló súlyokat, majd `Rangsor újraszámítása`.
3. Változtass egy súlyt (pl. növekedés 25% → 50%), és figyeld, **hányadik helyen marad a top startup**.

Ha a rangsor élbolya robusztus a súlyváltozásra, az erősíti a modell hitelességét; ha egyetlen mutató átbillenti, az módszertani figyelmeztetés.

---

## Korlátok és továbbfejlesztés

- **Memóriás tárolás:** az importált adatok a szerver újraindításakor elvesznek. Tartós tároláshoz SQLite vagy PostgreSQL javasolt.
- **AI-kontextus mérete:** jelenleg a teljes adatbázis bekerül minden Gemini-prompt kontextusába; nagy adatnál érdemes csak a releváns (pl. top N) startupokra szűkíteni.
- **A pontozás kalibrálatlan:** a súlyok és normalizálási szabályok validálásra szorulnak (pl. korreláció a becsült értékeléssel).
- **Statikus dashboard-mutatók:** a dashboard egyes elemei minta-adatot mutatnak; az élő összesítők a `/api/analysis/summary` bekötésével aktiválhatók.

---

## Biztonság

- A **Gemini API-kulcs kizárólag a backend `.env` fájljában** legyen; soha ne kerüljön a HTML-be vagy a böngésző JavaScript-kódjába.
- A feltöltés korlátozva van: csak `.xlsx`/`.xls`, legfeljebb **10 MB**.
- Éles környezetben állítsd be a `CORS_ORIGIN` változót, és fontold meg az AI-végpontok rate-limitelését.

---

## Jogi megjegyzés

- A projekt **oktatási célú**; minden vállalat és pénzügyi adat **szintetikus**, nem valós beszámoló.
- A pontszámok és rangsorok **döntéstámogató becslések, nem befektetési tanácsok**, és nem helyettesítik a pénzügyi átvilágítást.
- Az **Allianz** név és logó nem része a projektnek; a felület kék-fehér, Allianz-ihletésű színvilágot használ hivatalos márkaelemek nélkül.
</content>
</invoke>
