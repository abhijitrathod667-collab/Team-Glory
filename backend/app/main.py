import os, time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # backend/.env, found even if uvicorn is started from another folder
from . import ai_service
from .engine import PLACES, REPORT_TTL_MIN, ROADS, VIL, brief_facts, build_state, road_view, route
from .sample_data import FORECAST, SEED_REPORTS

app = FastAPI(title="ReliefLink API")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173").split(",")],
                   allow_methods=["*"], allow_headers=["*"])
# in memory only; cleared on restart. Each report keeps a timestamp so its age is always real.
REPORTS = [dict(r, ts=time.time() - r["age"] * 60) for r in SEED_REPORTS]
MAX_REPORTS = 100
ROAD_NAME = {f"{a}-{b}": f"{PLACES[a]['n']} – {PLACES[b]['n']}" for a, b, _, _ in ROADS}
ROAD_KEYS = set(ROAD_NAME)


class ReportIn(BaseModel):
    road: str = ""
    text: str = ""

class AdviceIn(BaseModel):
    village: str = ""
    problem: str = ""
    rain: int | None = None  # None = use the forecast

class HelpIn(BaseModel):
    type: str = ""
    village: str = ""
    people: int = 0


def clamp(rain):  # no rain given = the forecast's expected 72h total; a number = a what-if scenario
    return max(0, min(160, max(FORECAST) if rain is None else rain))
def live(): now = time.time(); return [dict({k: v for k, v in r.items() if k != "ts"}, age=int((now - r["ts"]) / 60)) for r in REPORTS]
def reports_out(rep): return [dict(r, name=ROAD_NAME[r["road"]]) for r in rep]


@app.get("/api/health")
def health(): return {"status": "ok", "ai_configured": ai_service.configured(), "ai_last_error": ai_service.last_error}

@app.get("/api/state")
def state(rain: int | None = None):
    rep = live(); s = build_state(clamp(rain), rep); s["reports"] = reports_out(rep); s["forecast_mm"] = max(FORECAST); s["what_if"] = rain is not None; s["ai_configured"] = ai_service.configured(); return s

@app.get("/api/route")
def get_route(src: str, dst: str, rain: int | None = None):
    if src not in PLACES or dst not in PLACES: raise HTTPException(404, "Unknown place.")
    if src == dst: raise HTTPException(400, "Choose two different places.")
    rep = live(); return route([road_view(r, clamp(rain), rep) for r in ROADS], src, dst)

@app.get("/api/brief")
def brief(rain: int | None = None):  # English + Hindi relief briefing; the AI only words facts that Python computed
    return ai_service.brief(brief_facts(build_state(clamp(rain), live())))

@app.get("/api/alert")
def village_alert(village: str, rain: int | None = None):  # English + Hindi alert for one village
    if village not in VIL: raise HTTPException(404, "Unknown village.")
    return ai_service.village_alert(next(v for v in build_state(clamp(rain), live())["villages"] if v["id"] == village))

@app.post("/api/advice")
def advice(b: AdviceIn):  # "tell us your problem": specific steps in English + Hindi
    if b.village not in VIL: raise HTTPException(400, "Choose your village.")
    t = b.problem.strip()
    if not 3 <= len(t) <= 300: raise HTTPException(400, "Write 3 to 300 characters about your problem.")
    s = build_state(clamp(b.rain), live())
    return ai_service.advice(next(v for v in s["villages"] if v["id"] == b.village), t, s)

@app.post("/api/reports")
def add_report(b: ReportIn):
    if b.road and b.road not in ROAD_KEYS: raise HTTPException(400, "Choose the road you saw.")
    t = b.text.strip()
    if not 3 <= len(t) <= 300: raise HTTPException(400, "Write 3 to 300 characters about what you saw.")
    status, note, source, road = ai_service.triage(t, b.road)  # road may come from the AI or a name search when the form left it empty
    if not road: raise HTTPException(400, "Choose the road, or name both villages in your report (for example: Nadi Pur and Sagar Gaon).")
    REPORTS.insert(0, dict(road=road, text=t, status=status, ts=time.time(), source=source, note=note)); del REPORTS[MAX_REPORTS:]
    fresh = sum(1 for r in live() if r["road"] == road and r["status"] == "Blocked" and r["age"] < REPORT_TTL_MIN)
    return dict(status=status, note=note, source=source, road=road, road_name=ROAD_NAME[road], verified=fresh >= 2)

@app.post("/api/help")
def help_request(b: HelpIn):
    if b.type not in ("Medicine", "Fuel", "Rescue", "Food"): raise HTTPException(400, "Choose what you need.")
    if b.village not in VIL: raise HTTPException(400, "Choose your village.")
    if not 1 <= b.people <= 500: raise HTTPException(400, "Enter how many people, from 1 to 500.")
    return dict(saved=True, sent=False, message="Recorded in this demo only. Nothing was sent. In danger? Dial 112.")
