from app.engine import build_state, names, route, triage_rules
from app.sample_data import SEED_REPORTS
S = build_state(70, SEED_REPORTS)

def test_roads():
    m = {r["k"]: (r["status"], r["risk"]) for r in S["roads"]}
    assert m["kheri-nadi"] == ("Cut", 100) and m["ghat-nadi"] == ("Watch", 44) and m["kheri-dev"][0] == "Open"
    assert m["dev-dharkot"][0] == "Cut" and m["ghat-bhojpur"][0] == "Cut"  # more than one road is cut in the demo

def test_kpi_and_banner():
    assert S["kpi"]["affected"] == 5 and S["kpi"]["fruit_t"] == 3.0 and S["banner"]["level"] == "Critical"

def test_rank():
    assert [v["id"] for v in S["villages"]][:5] == ["nadi", "tal", "dharkot", "sagar", "bhojpur"]

def test_route():
    r = route(S["roads"], "kheri", "nadi")
    assert r["usual"]["km"] == 60 and r["safe"]["km"] == 185

def test_plan():
    assert [(p["name"], p["km"]) for p in S["plan"]] == [("Nadi Pur", 80), ("Tal Pur", 130), ("Dhar Kot", None), ("Sagar Gaon", 135), ("Bhoj Pur", None)]  # cut-off villages have no safe depot

def test_zero_rain():
    z = build_state(0, [])
    assert z["plan"] == [] and all(r["status"] == "Open" for r in z["roads"])

def test_two_blocked_reports_cut_a_road():
    z = build_state(0, [{"road": "dev-ghat", "status": "Blocked"}] * 2)
    assert next(r for r in z["roads"] if r["k"] == "dev-ghat")["status"] == "Cut"


def _status(state, vid): return next(v for v in state["villages"] if v["id"] == vid)

def test_depot_b_still_supplies_when_depot_a_link_is_cut():
    z = build_state(70, [{"road": "dev-ghat", "status": "Blocked"}] * 2)
    n = _status(z, "nadi")
    assert n["status"] == "Detour" and n["depots"][0]["id"] == "ghat"  # not "Isolated": Depot B reaches it

def test_isolated_outranks_detour():
    z = build_state(160, [])
    assert [v["status"] for v in z["villages"]][:3] == ["Isolated"] * 3

def test_old_blocked_reports_expire():
    z = build_state(0, [{"road": "dev-ghat", "status": "Blocked", "age": 400}] * 2)
    assert next(r for r in z["roads"] if r["k"] == "dev-ghat")["status"] == "Open"

def test_triage_rules():
    t = lambda s: triage_rules(s)[0]
    assert t("Rocks falling, vehicles cannot pass") == "Blocked" and t("पत्थर गिर रहे हैं") == "Blocked"
    assert t("road clear, traffic moving") == "Clear"
    assert t("road is not clear") == "Watch" and t("unclear, maybe ok") == "Watch"
    assert t("took a shortcut, my husband drove") == "Watch"  # no false hit on "cut" or "band"
    assert t("Slush and fog, drive slowly") == "Watch"


def test_names_reads_well():
    assert names(["A"]) == "A" and names(["A", "B"]) == "A and B" and names(["A", "B", "C"]) == "A, B and C"
    assert names(list("ABCDE")) == "A, B, C and 2 more"

def test_banner_with_many_cut_roads_stays_short():
    assert len(S["banner"]["text"]) < 260 and "Kheri – Nadi Pur, Dev Nagar – Dhar Kot and Ghat Pur – Bhoj Pur are cut" in S["banner"]["text"]
