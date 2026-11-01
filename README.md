# ReliefLink

Hill-road supply resilience: rain is taken automatically from the 72-hour forecast (with an optional What-if mode to test heavier storms); see which roads break, which villages run short first, the safest route and the nearest reachable depot. Fictional data, no login, nothing is ever sent to anyone. Not a replacement for 112.

```
relieflink/
├── backend/   FastAPI: app/engine.py (risk, routing, ranking, plan), ai_service.py (Gemini report reading), main.py (API), tests/
├── frontend/  React + Vite UI (src/App.jsx, draw.js, styles.css)
├── README.md
└── .gitignore
```

## Run (Windows)
Backend (port 8000):
```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
Frontend (port 5173), in a second terminal:
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. API docs: http://localhost:8000/docs. Tests: `cd backend && pytest`.

## AI (optional)
Put your key in `backend/.env` (`GEMINI_API_KEY`) and restart uvicorn. If the AI still says it is off, open http://localhost:8000/api/health: `ai_configured` must be true, and `ai_last_error` (also printed in the uvicorn terminal) says why Gemini failed, for example a rate limit. Gemini does four jobs, all in `backend/app/ai_service.py`:
1. **Reads reports** (Report tab): Hindi, Hinglish or English text becomes a status (Blocked / Watch / Clear) and, if you skip the road, finds the road too.
2. **Relief briefing** (Routes tab): a short English + Hindi summary of the plan.
3. **Village alert** (Check area tab): the village's alert in English + Hindi.
4. **Tell us your problem** (Advice tab): someone describes what they face ("दवा खत्म हो गई है और सड़क बंद है") and gets a short "what the flood could do here" part plus 4 to 6 action steps for their village, in English + Hindi. The AI may use general flood and landslide safety knowledge, answers differently each time, and runs with Gemini's thinking pause off so it is fast. Links, phone numbers (other than 112), medicine doses and long invented numbers are removed point by point; if the AI fails, the checklist fallback covers medicine, fuel, food, rescue, landslide, flood, water, roads and phone/power.

With no key, or if Gemini fails or times out, plain rules and templates are used and nothing breaks. The AI never computes a village number: all risk, distance and ranking maths is plain Python, jobs 2 and 3 only word facts Python computed, and any AI text with a number that is not in those facts is dropped. Job 4 (advice) is the one freer job, as described above.

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Status and `ai_configured` |
| GET | `/api/state` (add `?rain=70` for a what-if) | Roads, villages, ranking, plan, forecast, reports |
| GET | `/api/route?src=kheri&dst=nadi&rain=70` | Usual vs safest route. |
| GET | `/api/brief?rain=70` | English + Hindi relief briefing (`source`: gemini or template) |
| GET | `/api/alert?village=nadi&rain=70` | English + Hindi alert for one village |
| POST | `/api/advice` | `{village, problem, rain}` → `{en: [...], hi: [...], impact_en: [...], impact_hi: [...], source}` flood impact and steps for that village |
| POST | `/api/reports` | `{road, text}` → Blocked / Watch / Clear. `road` is optional: the road is found from the text |
| POST | `/api/help` | `{type, village, people}` → saved locally, never sent |

## Demo flow
1. Home uses the forecast (70 mm) automatically: banner Critical, 5 villages affected, 3 roads cut, 3.0 t fruit at risk. 2. Press What-if and drag the slider to 0, then 160; press Forecast to go back. 3. Routes: Kheri to Nadi Pur is 185 km by the safe road. 4. Read the relief plan. 5. Report `पत्थर गिर रहे हैं` on Nadi Pur – Sagar Gaon once (one Blocked report is already seeded) and watch it turn Cut. 6. Save a help request. 7. Routes tab: press "Write briefing" for English + Hindi. Check area tab: press "Show in Hindi + English". 8. Report tab: leave the road empty and write `Nadi Pur aur Sagar Gaon ke beech pathar gir rahe hain`.

## Troubleshooting
Frontend cannot connect: start the backend first. Port in use: set `VITE_API_URL` in `frontend/.env`. Reports and requests live in memory and reset when the backend restarts.
