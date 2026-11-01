from app import ai_service
from app.engine import advice_template, brief_facts, brief_template, build_state, road_from_text

S = build_state(70, [])
F = brief_facts(S)
GOOD = dict(en="At 70 mm Kheri \u2013 Nadi Pur is cut. In danger? Dial 112.", hi="70 \u092e\u093f\u092e\u0940 \u092c\u093e\u0930\u093f\u0936 \u092a\u0930 \u0938\u0921\u093c\u0915 \u0915\u091f \u091c\u093e\u0924\u0940 \u0939\u0948\u0964")


def _ai(monkeypatch, reply):  # pretend Gemini is on and answers with `reply`
    ai_service._cache.clear()
    monkeypatch.setattr(ai_service, "_gemini", lambda prompt, **kw: reply)


def test_road_from_text():
    assert road_from_text("Nadi Pur aur Sagar Gaon ke beech pathar") == "nadi-sagar"
    assert road_from_text("kheri nadi road band hai") == "kheri-nadi"
    assert road_from_text("pathar gir rahe hain") == "" and road_from_text("Nadi Pur ke paas") == ""

def test_template_has_both_languages():
    en, hi = brief_template(F)
    assert "70" in en and "70" in hi and "Kheri" in en

def test_no_ai_uses_template(monkeypatch):
    ai_service._cache.clear(); monkeypatch.setattr(ai_service, "configured", lambda: False)
    r = ai_service.brief(F)
    assert r["source"] == "template" and r["en"] and r["hi"]

def test_good_ai_text_is_kept(monkeypatch):
    _ai(monkeypatch, GOOD)
    assert ai_service.brief(F)["source"] == "gemini"

def test_invented_number_is_rejected(monkeypatch):
    _ai(monkeypatch, dict(GOOD, en="At 70 mm, 500 people are cut off."))
    assert ai_service.brief(F)["source"] == "template"

def test_hindi_must_be_hindi(monkeypatch):
    _ai(monkeypatch, dict(GOOD, hi="Road is cut at 70 mm."))
    assert ai_service.brief(F)["source"] == "template"

def test_village_alert_falls_back_per_status(monkeypatch):
    ai_service._cache.clear(); monkeypatch.setattr(ai_service, "configured", lambda: False)
    nadi = next(v for v in S["villages"] if v["id"] == "nadi")
    r = ai_service.village_alert(nadi)
    assert r["source"] == "template" and "Nadi Pur" in r["hi"] and r["en"] == nadi["alert"]

def test_triage_uses_ai_road_only_if_real(monkeypatch):
    _ai(monkeypatch, {"road": "made-up", "status": "Blocked", "note": "rocks"})
    assert ai_service.triage("rocks", "")[3] == ""
    _ai(monkeypatch, {"road": "nadi-sagar", "status": "Blocked", "note": "rocks"})
    assert ai_service.triage("rocks", "") == ("Blocked", "rocks", "gemini", "nadi-sagar")
    assert ai_service.triage("rocks", "kheri-dev")[3] == "kheri-dev"  # the person's own choice wins

def test_triage_falls_back_to_rules_and_name_search(monkeypatch):
    ai_service._cache.clear(); monkeypatch.setattr(ai_service, "configured", lambda: False)
    assert ai_service.triage("Nadi Pur aur Sagar Gaon ke beech pathar gir rahe hain") == ("Blocked", "", "rules", "nadi-sagar")


NADI = next(v for v in S["villages"] if v["id"] == "nadi")
GOODPTS = dict(en=["Dial 112 if anyone is in danger.", "Send a help request for Medicine on the Report tab."],
               hi=["\u0915\u093f\u0938\u0940 \u0915\u094b \u0916\u0924\u0930\u093e \u0939\u094b \u0924\u094b 112 \u0921\u093e\u092f\u0932 \u0915\u0930\u0947\u0902\u0964",
                   "\u0930\u093f\u092a\u094b\u0930\u094d\u091f \u091f\u0948\u092c \u092a\u0930 \u0926\u0935\u093e \u0915\u0947 \u0932\u093f\u090f \u0905\u0928\u0941\u0930\u094b\u0927 \u092d\u0947\u091c\u0947\u0902\u0964"])


def test_advice_template_matches_the_problem():
    en, hi = advice_template(NADI, "dawa khatam ho gayi aur road band hai")
    assert any("Medicine" in p for p in en) and any("Routes tab" in p for p in en)
    assert en[-1] == "In danger? Dial 112." and len(en) == len(hi) <= 6
    en, _ = advice_template(NADI, "something odd")  # no topic: still gives a safe next step
    assert any("help request" in p for p in en)

def test_good_ai_advice_is_kept(monkeypatch):
    _ai(monkeypatch, GOODPTS)
    assert ai_service.advice(NADI, "dawa chahiye")["source"] == "gemini"

def test_bad_ai_advice_is_rejected(monkeypatch):  # the whole answer is dropped, the plain checklist is used
    for bad in (dict(GOODPTS, hi=["only english", "again english"]),                  # Hindi is not Hindi
                dict(GOODPTS, en=["just one point"])):                                # too short
        _ai(monkeypatch, bad)
        assert ai_service.advice(NADI, "dawa chahiye")["source"] == "template"

def test_bad_points_are_dropped_but_good_ones_stay(monkeypatch):
    bad = ["Call 9876543210 for help.", "See www.example.com", "Take 500 mg paracetamol.", "Take 2 tablets now."]
    _ai(monkeypatch, dict(GOODPTS, en=GOODPTS["en"] + bad))
    r = ai_service.advice(NADI, "dawa chahiye")
    assert r["source"] == "gemini" and r["en"] == GOODPTS["en"]  # only the unsafe points were removed

def test_free_safety_advice_with_small_numbers_is_kept(monkeypatch):
    extra = ["Never walk through water deeper than 15 cm if it is moving fast.", "Boil water for 1 minute before drinking."]
    _ai(monkeypatch, dict(GOODPTS, en=GOODPTS["en"] + extra))
    assert ai_service.advice(NADI, "paani aa raha hai")["en"][-2:] == extra

def test_advice_has_impact_points(monkeypatch):
    _ai(monkeypatch, GOODPTS)  # the AI forgot the impact part: the facts-based one fills in
    r = ai_service.advice(NADI, "dawa chahiye", S)
    assert r["impact_en"] and r["impact_hi"] and any("Nadi Pur" in x for x in r["impact_en"])
    monkeypatch.setattr(ai_service, "_gemini", lambda prompt, **kw: None)  # AI is down: plain checklist + plain impact
    r = ai_service.advice(NADI, "dawa chahiye", S)
    assert r["source"] == "template" and r["impact_en"] and len(r["impact_en"]) == len(r["impact_hi"])

def test_advice_prompt_gets_rain_and_roads(monkeypatch):
    seen = []
    monkeypatch.setattr(ai_service, "_gemini", lambda prompt, **kw: seen.append(prompt))
    ai_service.advice(NADI, "dawa chahiye", S)
    assert '"rain_mm": 70' in seen[0] and "Kheri – Nadi Pur" in seen[0]
