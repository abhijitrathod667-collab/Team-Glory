"""Fictional ReliefLink data. Roads are (from, to, km, cut_mm): cut_mm = rain at which the road is cut.
Map coordinates are on a 720 x 480 canvas (see frontend/src/draw.js)."""
PLACES = {
    "kheri": dict(n="Kheri", kind="village", x=270, y=100, stock_days=11, fruit_t=0),
    "dev": dict(n="Dev Nagar", kind="depot", label="Depot A", x=170, y=265, stock=120),
    "ghat": dict(n="Ghat Pur", kind="depot", label="Depot B", x=290, y=385, stock=60),
    "nadi": dict(n="Nadi Pur", kind="village", x=480, y=235, stock_days=6, fruit_t=1.1),
    "tal": dict(n="Tal Pur", kind="village", x=630, y=370, stock_days=8, fruit_t=0.9),
    "sagar": dict(n="Sagar Gaon", kind="village", x=640, y=95, stock_days=5, fruit_t=0.3),
    "chirgaon": dict(n="Chir Gaon", kind="village", x=110, y=55, stock_days=10, fruit_t=0.2),
    "sonpur": dict(n="Son Pur", kind="village", x=45, y=190, stock_days=12, fruit_t=0),
    "dharkot": dict(n="Dhar Kot", kind="village", x=60, y=385, stock_days=9, fruit_t=0.4),
    "lalkot": dict(n="Lal Kot", kind="village", x=185, y=450, stock_days=11, fruit_t=0.1),
    "bhojpur": dict(n="Bhoj Pur", kind="village", x=450, y=440, stock_days=9, fruit_t=0.3),
}
# Demo scenario at the 70 mm forecast: Kheri-Nadi, Dev-Dhar Kot and Ghat-Bhoj Pur are cut; Ghat-Nadi, Ghat-Lal Kot and Kheri-Chir Gaon are on watch.
ROADS = [("kheri", "dev", 55, 226), ("dev", "ghat", 50, 200), ("ghat", "nadi", 80, 159),
         ("kheri", "nadi", 60, 58), ("nadi", "tal", 50, 190), ("nadi", "sagar", 55, 200),
         ("kheri", "chirgaon", 38, 140), ("dev", "sonpur", 40, 210), ("dev", "dharkot", 45, 64),
         ("ghat", "lalkot", 40, 120), ("ghat", "bhojpur", 48, 66)]
FORECAST = [3, 12, 28, 46, 63, 70, 66]  # cumulative mm at Now, +12h ... +72h
SEED_REPORTS = [
    dict(road="nadi-sagar", text="Rocks falling, vehicles cannot pass", status="Blocked", age=0, source="rules", note=""),
    dict(road="kheri-dev", text="Slush and fog, drive slowly", status="Watch", age=25, source="rules", note=""),
    dict(road="dev-ghat", text="Road clear, traffic moving", status="Clear", age=60, source="rules", note=""),
]
