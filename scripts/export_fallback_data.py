"""
Exports all research artifacts and API responses from the running FastAPI instance
into web/src/data/fallbackData.js and web/public/api/ so that the web application
operates 100% smoothly with zero blank screens or network hangs on any host (Vercel, GitHub Pages, or offline).
"""
import os
import json
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
SRC_DATA_DIR = WEB_DIR / "src" / "data"
PUBLIC_API_DIR = WEB_DIR / "public" / "api"

SRC_DATA_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_API_DIR.mkdir(parents=True, exist_ok=True)

endpoints = [
    ("data/foundation", "/api/data/foundation"),
    ("integrity/tests", "/api/integrity/tests"),
    ("enrichment/stats", "/api/enrichment/stats"),
    ("taxonomy", "/api/taxonomy"),
    ("experiments", "/api/experiments"),
    ("models/registry", "/api/models/registry"),
    ("lab/simulation/years", "/api/lab/simulation/years"),
    ("brain/ledger", "/api/brain/ledger"),
    ("patterns/categorized", "/api/patterns/categorized"),
    ("surprise/events", "/api/surprise/events?limit=40"),
    ("eras", "/api/eras"),
    ("calibration", "/api/calibration"),
    ("forecast/2027", "/api/forecast/2027"),
    ("forecast/2027/spec", "/api/forecast/2027/spec"),
    ("mocks/blueprints", "/api/mocks/blueprints"),
    ("mocks/mock_1/questions", "/api/mocks/mock_1/questions"),
    ("mocks/mock_2/questions", "/api/mocks/mock_2/questions"),
    ("mocks/mock_3/questions", "/api/mocks/mock_3/questions"),
    ("mocks/mock_4/questions", "/api/mocks/mock_4/questions"),
    ("mocks/mock_5/questions", "/api/mocks/mock_5/questions"),
    ("reports/list", "/api/reports/list"),
    ("reports/data_quality", "/api/reports/data_quality"),
    ("reports/reconciliation", "/api/reports/reconciliation"),
    ("reports/calibration", "/api/reports/calibration"),
    ("reports/forecast_2027", "/api/reports/forecast_2027"),
    ("reports/paper_spec", "/api/reports/paper_spec"),
    ("reports/mock_blueprints", "/api/reports/mock_blueprints"),
    ("data/golden", "/api/data/golden?limit=100"),
    ("features", "/api/features?limit=100")
]

exported_data = {}

for name, path in endpoints:
    url = f"http://localhost:8000{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Exporter"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            exported_data[name] = data
            
            # Save static JSON file to web/public/api/{name}.json
            out_file = PUBLIC_API_DIR / f"{name}.json"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Exported {name} -> {out_file} ({len(json.dumps(data))} bytes)")
    except Exception as e:
        print(f"Error fetching {url}: {e}")

# Also fetch simulation data for sample years 2026, 2025, 2024
sim_years = [2026, 2025, 2024]
sim_data = {}
for yr in sim_years:
    url = f"http://localhost:8000/api/lab/simulation/{yr}"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
            sim_data[yr] = data
            out_file = PUBLIC_API_DIR / "lab" / "simulation" / f"{yr}.json"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Exported simulation {yr} ({len(json.dumps(data))} bytes)")
    except Exception as e:
        print(f"Error fetching simulation {yr}: {e}")

# Build fallbackData.js
js_content = f"""// AUTO-GENERATED FALLBACK DATA FOR RESEARCH LAB
// Guarantees zero blank screens and instant zero-latency loading on any hosting provider.

export const fallbackCalibration = {json.dumps(exported_data.get('calibration', {}), indent=2)};

export const fallbackFoundation = {json.dumps(exported_data.get('data/foundation', {}), indent=2)};

export const fallbackIntegrity = {json.dumps(exported_data.get('integrity/tests', {}), indent=2)};

export const fallbackEnrichmentStats = {json.dumps(exported_data.get('enrichment/stats', {}), indent=2)};

export const fallbackTaxonomy = {json.dumps(exported_data.get('taxonomy', {}), indent=2)};

export const fallbackExperiments = {json.dumps(exported_data.get('experiments', {}).get('experiments', []), indent=2)};

export const fallbackRegistry = {json.dumps(exported_data.get('models/registry', {}), indent=2)};

export const fallbackSimYears = {json.dumps(exported_data.get('lab/simulation/years', []), indent=2)};

export const fallbackBrainLedger = {json.dumps(exported_data.get('brain/ledger', {}).get('ledger', []), indent=2)};

export const fallbackPatterns = {json.dumps(exported_data.get('patterns/categorized', {}), indent=2)};

export const fallbackSurprises = {json.dumps(exported_data.get('surprise/events', {}).get('events', []), indent=2)};

export const fallbackEras = {json.dumps(exported_data.get('eras', {}), indent=2)};

export const fallbackForecast2027 = {json.dumps(exported_data.get('forecast/2027', {}), indent=2)};

export const fallbackForecast2027Spec = {json.dumps(exported_data.get('forecast/2027/spec', {}), indent=2)};

export const fallbackMockBlueprints = {json.dumps(exported_data.get('mocks/blueprints', {}), indent=2)};

export const fallbackMockQuestions = {{
  "mock_1": {json.dumps(exported_data.get('mocks/mock_1/questions', {}), indent=2)},
  "mock_2": {json.dumps(exported_data.get('mocks/mock_2/questions', {}), indent=2)},
  "mock_3": {json.dumps(exported_data.get('mocks/mock_3/questions', {}), indent=2)},
  "mock_4": {json.dumps(exported_data.get('mocks/mock_4/questions', {}), indent=2)},
  "mock_5": {json.dumps(exported_data.get('mocks/mock_5/questions', {}), indent=2)}
}};

export const fallbackGoldenSample = {json.dumps(exported_data.get('data/golden', {}).get('questions', []), indent=2)};

export const fallbackFeaturesSample = {json.dumps(exported_data.get('features', {}).get('features', []), indent=2)};

export const fallbackReportsList = {json.dumps(exported_data.get('reports/list', {}), indent=2)};

export const fallbackReports = {{
  "data_quality": {json.dumps(exported_data.get('reports/data_quality', {}), indent=2)},
  "reconciliation": {json.dumps(exported_data.get('reports/reconciliation', {}), indent=2)},
  "calibration": {json.dumps(exported_data.get('reports/calibration', {}), indent=2)},
  "forecast_2027": {json.dumps(exported_data.get('reports/forecast_2027', {}), indent=2)},
  "paper_spec": {json.dumps(exported_data.get('reports/paper_spec', {}), indent=2)},
  "mock_blueprints": {json.dumps(exported_data.get('reports/mock_blueprints', {}), indent=2)}
}};

export const fallbackSimulation = {json.dumps(sim_data, indent=2)};
"""

target_js_file = SRC_DATA_DIR / "fallbackData.js"
with open(target_js_file, "w", encoding="utf-8") as f:
    f.write(js_content)
print(f"\nSUCCESS: Exported all fallback data to {target_js_file} ({os.path.getsize(target_js_file) / 1024:.1f} KB)")
