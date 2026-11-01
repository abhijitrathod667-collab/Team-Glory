"""Deterministic engine: risk, routing, ranking, relief plan, rule-based triage. No AI computes any number here."""
import heapq, re
from .sample_data import PLACES, ROADS, FORECAST

REPORT_TTL_MIN = 360  # a Blocked report stops counting toward a cut after 6 hours

N = lambda i: PLACES[i]["n"]
VIL = [i for i, p in PLACES.items() if p["kind"] == "village"]
DEP = [i for i, p in PLACES.items() if p["kind"] == "depot"]


def names(items, limit=3, word="and", more="more"):
    """'A', 'A and B', 'A, B and C', 'A, B, C and 2 more'. For Hindi pass word='और', more='अन्य'."""
    items = list(items)
    if len(items) > limit:
        return ", ".join(items[:limit]) + f" {word} {len(items) - limit} {more}"
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + f" {word} " + items[-1]


def road_view(r, rain, reports):
    a, b, km, cut = r
    k = f"{a}-{b}"
    forced = sum(1 for x in reports if x["road"] == k and x["status"] == "Blocked" and x.get("age", 0) < REPORT_TTL_MIN) >= 2
    is_cut = rain >= cut or forced
    risk = 100 if is_cut else int(min(1, rain / cut) * 100 + .5)
    return dict(k=k, a=a, b=b, km=km, risk=risk, name=f"{N(a)} – {N(b)}",
                status="Cut" if is_cut else "Watch" if risk >= 40 else "Open")


def path(roads, a, b, safe):
    dist, prev, pq = {a: 0}, {}, [(0, a)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e9):
            continue
        for r in roads:
            if u not in (r["a"], r["b"]) or (safe and r["status"] == "Cut"):
                continue
            o = r["b"] if r["a"] == u else r["a"]
            if d + r["km"] < dist.get(o, 1e9):
                dist[o] = d + r["km"]; prev[o] = (u, r); heapq.heappush(pq, (dist[o], o))
    if b not in dist:
        return None
    nodes, legs, c = [b], [], b
    while c != a:
        p, r = prev[c]; legs.insert(0, r); nodes.insert(0, p); c = p
    return dict(km=dist[b], nodes=nodes, legs=legs)


def leg_views(p):
    return [dict(k=r["k"], **{"from": N(p["nodes"][i]), "to": N(p["nodes"][i + 1])}, km=r["km"], risk=r["risk"], status=r["status"])
            for i, r in enumerate(p["legs"])]


def best_safe(roads, v):
    """Nearest depot that can reach village v by a safe road: (depot_id, path) or None."""
    opts = [(d, path(roads, d, v, True)) for d in DEP]
    opts = [o for o in opts if o[1]]
    return min(opts, key=lambda o: o[1]["km"]) if opts else None


def village_status(roads, v):  # main supply route is from Depot A; Depot B can still rescue a village
    u, s = path(roads, "dev", v, False), path(roads, "dev", v, True)
    if s:
        return "Supplied" if s["nodes"] == u["nodes"] else "Detour"
    return "Detour" if best_safe(roads, v) else "Isolated"


def score(p, status):
    access = {"Supplied": 0, "Detour": 30, "Isolated": 40}[status]
    return min(100, int((14 - p["stock_days"]) / 14 * 40 + access + p["fruit_t"] / 1.1 * 30 + .5))


def route(roads, a, b):
    u, s = path(roads, a, b, False), path(roads, a, b, True)
    return dict(usual=dict(km=u["km"], cut=[r["name"] for r in u["legs"] if r["status"] == "Cut"]),
                safe=dict(km=s["km"], nodes=s["nodes"], legs=leg_views(s)) if s else None)


def make_plan(roads, vil):
    stock = {d: PLACES[d]["stock"] for d in DEP}
    out = []
    for v in sorted(vil, key=lambda v: -v["score"]):
        if v["status"] == "Supplied":
            continue
        opts = sorted(((d, path(roads, d, v["id"], True)) for d in DEP), key=lambda o: o[1]["km"] if o[1] else 1e9)
        pick = next(((d, p) for d, p in opts if p and stock[d] >= 3), None)  # each village needs 3 ration-days
        if pick:
            stock[pick[0]] -= 3
        out.append(dict(village=v["id"], name=v["name"], status=v["status"], days=v["stock_days"],
                        depot=f'{PLACES[pick[0]]["label"]} – {N(pick[0])}' if pick else None, km=pick[1]["km"] if pick else None))
    return out


def banner(roads, rain):
    cut, w = [r["name"] for r in roads if r["status"] == "Cut"], [r["name"] for r in roads if r["status"] == "Watch"]
    if cut:
        return dict(level="Critical", text=f"At {rain} mm, {names(cut)} {'are' if len(cut) > 1 else 'is'} cut. When a road breaks, relief shouldn’t stop: see who may run short and the safe way around.")
    if w:
        return dict(level="Warning", text=f"At {rain} mm, {names(w)} may become unsafe. Plan stock and trips ahead.")
    return dict(level="ok", text="No road is at risk at this rainfall. Try a what-if scenario to test heavier rain.")


def build_state(rain, reports):
    roads = [road_view(r, rain, reports) for r in ROADS]
    vil = []
    for i in VIL:
        p, st = PLACES[i], village_status(roads, i)
        s, alt = path(roads, "dev", i, True), best_safe(roads, i)
        use = s or (alt[1] if alt else path(roads, "dev", i, False))
        if st == "Supplied":
            alert = f"{p['n']}: the road is open. Normal deliveries continue."
        elif st == "Detour" and s:
            via = ", ".join(N(x) for x in s["nodes"][1:-1])
            alert = f"{p['n']}: the main road may be cut. Trucks will come by the longer link road via {via}. Shopkeepers and farmers, plan for delays."
        elif st == "Detour":
            alert = f"{p['n']}: the road from Depot A is cut. Supplies will come from {PLACES[alt[0]]['label']} ({N(alt[0])}). Shopkeepers and farmers, plan for delays."
        else:
            alert = f"{p['n']}: no safe road right now. Use the help request form and call the district helpline."
        depots = sorted(((d, path(roads, d, i, True)) for d in DEP), key=lambda o: o[1]["km"] if o[1] else 1e9)
        sc = score(p, st)
        vil.append(dict(id=i, name=p["n"], status=st, score=sc, priority="High" if sc >= 60 else "Normal", stock_days=p["stock_days"],
                        fruit_t=p["fruit_t"], alert=alert, legs=leg_views(use), depots=[dict(id=d, name=f'{PLACES[d]["label"]}, {N(d)}', stock=PLACES[d]["stock"], km=q["km"]) for d, q in depots if q]))
    aff = [v for v in vil if v["status"] != "Supplied"]
    return dict(rain=rain, banner=banner(roads, rain), roads=roads, forecast=FORECAST, weakest_cut_mm=min(r[3] for r in ROADS),
                places=[dict(id=i, name=p["n"], kind=p["kind"], label=p.get("label", ""), x=p["x"], y=p["y"]) for i, p in PLACES.items()],
                villages=sorted(vil, key=lambda v: -v["score"]), plan=make_plan(roads, vil),
                kpi=dict(affected=len(aff), villages=len(vil), depots=len(DEP), fruit_t=round(sum(v["fruit_t"] for v in aff), 1)))


NEG = re.compile(r"\b(not|no|never|nahi|nahin)\b|n't|नहीं")


def _has(t, words):  # English words match from a word start ("rock" hits "rocks", not "husband"/"shortcut"); Hindi matches anywhere
    return any(re.search(r"\b" + re.escape(w), t) if w.isascii() else w in t for w in words)


def triage_rules(text):
    t = text.lower(); has = lambda ws: _has(t, ws)
    if has(["band", "blocked", "cut", "landslide", "rock", "pathar", "patthar", "malba", "पत्थर", "मलबा", "बंद", "बाढ़", "slide"]): return "Blocked", ""
    if has(["clear", "khula", "खुला", "chal rahi", "चल रही"]):
        return ("Watch", "Unclear; please confirm.") if NEG.search(t) else ("Clear", "")  # "not clear" must never read as Clear
    if has(["slush", "fog", "slow", "dhire", "फिसल", "धीरे"]): return "Watch", ""
    return "Watch", "Unclear; please confirm."


# ---- facts and plain-text fallbacks for the AI writing features (ai_service.py) ----
ROAD_KEYS = {f"{a}-{b}" for a, b, _, _ in ROADS}
EMERGENCY = 112
ALERT_HI = {
    "Supplied": "{n}: सड़क खुली है। सामान्य आपूर्ति जारी है।",
    "Detour": "{n}: मुख्य सड़क कट सकती है। ट्रक लंबे रास्ते से आएँगे। दुकानदार और किसान देरी के लिए तैयार रहें।",
    "Isolated": "{n}: अभी कोई सुरक्षित सड़क नहीं है। मदद का फ़ॉर्म भरें और ज़िला हेल्पलाइन पर फ़ोन करें। खतरे में हों तो 112 डायल करें।",
}


def road_from_text(text):
    """Fallback road finder: the one road whose two villages are both named in the text. '' when unclear."""
    t = text.lower()
    named = {i for i, p in PLACES.items() if re.search(r"\b(" + re.escape(i) + "|" + re.escape(p["n"].lower()) + r")\b", t)}
    hit = [f"{a}-{b}" for a, b, _, _ in ROADS if a in named and b in named]
    return hit[0] if len(hit) == 1 else ""


def brief_facts(s):
    """The only facts the AI may use when it writes the relief briefing. Every number in them was computed above."""
    return dict(rain_mm=s["rain"], roads_cut=[r["name"] for r in s["roads"] if r["status"] == "Cut"],
                roads_watch=[r["name"] for r in s["roads"] if r["status"] == "Watch"],
                villages=[dict(name=v["name"], status=v["status"], days_of_stock=v["stock_days"], priority=v["priority"]) for v in s["villages"]],
                relief_plan=[dict(village=p["name"], from_depot=p["depot"], km=p["km"]) for p in s["plan"]],
                ration_days_per_village=3, emergency_number=EMERGENCY)


def brief_template(f):
    """Plain English + Hindi briefing used when the AI is off or its text fails the checks."""
    rain, cut, watch = f["rain_mm"], f["roads_cut"], f["roads_watch"]
    if cut:
        first = ", ".join(p["village"] for p in f["relief_plan"][:2])
        en = f"At {rain} mm, {names(cut)} {'is' if len(cut) == 1 else 'are'} cut. " + (f"Relief goes first to {first}. " if first else "") + f"In danger? Dial {EMERGENCY}."
        hi = f"{rain} मिमी बारिश पर {names(cut, word='और', more='अन्य')} {'कट जाती है' if len(cut) == 1 else 'कट जाती हैं'}। " + (f"सबसे पहले राहत {first} को जाएगी। " if first else "") + f"खतरे में हों तो {EMERGENCY} डायल करें।"
        return en, hi
    if watch:
        return (f"At {rain} mm, {names(watch)} may become unsafe. Plan stock and trips ahead.",
                f"{rain} मिमी बारिश पर {names(watch, word='और', more='अन्य')} {'असुरक्षित हो सकती है' if len(watch) == 1 else 'असुरक्षित हो सकती हैं'}। सामान और यात्रा की योजना पहले से बनाएँ।")
    return (f"At {rain} mm no road is at risk. All villages are supplied by their usual road.",
            f"{rain} मिमी बारिश पर कोई सड़क खतरे में नहीं है। सभी गाँवों में सामान्य आपूर्ति जारी है।")


# ---- "Tell us your problem": keyword checklist (fallback for the AI advice in ai_service.py) ----
TOPICS = [  # (words, English point, Hindi point). The first words that match decide which points are shown.
    (["medicine", "dawa", "dawai", "doctor", "hospital", "injur", "chot", "bimar", "sick", "pregnan", "दवा", "दवाई", "डॉक्टर", "अस्पताल", "चोट", "बीमार"],
     "Medicine or health need: send a help request for Medicine on the Report tab. If someone's life is in danger, dial 112 first.",
     "दवा या स्वास्थ्य की ज़रूरत: रिपोर्ट टैब पर दवा के लिए मदद का अनुरोध भेजें। किसी की जान खतरे में हो तो पहले 112 डायल करें।"),
    (["fuel", "petrol", "diesel", "ईंधन", "पेट्रोल", "डीजल"],
     "Fuel is short: send a help request for Fuel on the Report tab and keep your fuel for emergencies.",
     "ईंधन कम है: रिपोर्ट टैब पर ईंधन के लिए मदद का अनुरोध भेजें और ईंधन आपात काम के लिए बचाकर रखें।"),
    (["food", "ration", "khana", "bhookh", "hungry", "अनाज", "खाना", "राशन", "भूख"],
     "Food is short: send a help request for Food on the Report tab and share what you have with neighbours.",
     "खाना कम है: रिपोर्ट टैब पर खाने के लिए मदद का अनुरोध भेजें और जो है उसे पड़ोसियों के साथ बाँटें।"),
    (["rescue", "stuck", "trapped", "phans", "फंस", "फँस", "बचाव"],
     "Stuck or in danger: dial 112 now and stay where rescuers can find you. Also send a Rescue help request.",
     "फंसे हैं या खतरे में हैं: अभी 112 डायल करें और ऐसी जगह रहें जहाँ बचावकर्मी आपको ढूँढ सकें। बचाव का अनुरोध भी भेजें।"),
    (["landslide", "pathar", "patthar", "malba", "slope", "crack", "pahad", "पत्थर", "मलबा", "दरार", "पहाड़", "ढलान"],
     "Landslide danger: move away from the slope quickly and do not drive under steep slopes in heavy rain.",
     "भूस्खलन का खतरा: ढलान से जल्दी दूर हट जाएँ और भारी बारिश में खड़ी ढलान के नीचे गाड़ी न चलाएँ।"),
    (["flood", "baadh", "bahav", "बाढ़", "बहाव"],
     "Flood danger: move to higher ground early and never walk or drive through flood water.",
     "बाढ़ का खतरा: जल्दी ऊँची जगह पर चले जाएँ और बाढ़ के पानी में पैदल या गाड़ी से न जाएँ।"),
    (["water", "paani", "pani", "पानी"],
     "Drink only boiled or treated water.", "सिर्फ़ उबला या साफ़ किया हुआ पानी पिएँ।"),
    (["road", "sadak", "raasta", "route", "jam", "सड़क", "रास्ता"],
     "Road problem: check the Routes tab for the safest road.", "सड़क की समस्या: सबसे सुरक्षित रास्ते के लिए रूट्स टैब देखें।"),
    (["phone", "network", "signal", "bijli", "electricity", "बिजली", "नेटवर्क"],
     "No phone or power: keep your phone for emergencies, use a torch, and tell a neighbour where you are.",
     "फ़ोन या बिजली नहीं है: फ़ोन आपात काम के लिए बचाकर रखें, टॉर्च इस्तेमाल करें और पड़ोसी को बताएँ कि आप कहाँ हैं।"),
]


def advice_template(v, problem):
    """Plain checklist for one village (v from build_state) and the problem text. Returns (english_points, hindi_points)."""
    t, pts = problem.lower(), []
    if v["status"] == "Isolated":
        pts.append((f"No safe road reaches {v['name']} right now: stay where you are unless officials say otherwise.",
                    f"अभी {v['name']} तक कोई सुरक्षित सड़क नहीं पहुँचती: जब तक अधिकारी न कहें, जहाँ हैं वहीं रहें।"))
    elif v["status"] == "Detour":
        pts.append(("The main road may be cut, so deliveries come by a longer road and can be late. Keep a few extra days of supplies.",
                    "मुख्य सड़क कट सकती है, इसलिए सामान लंबे रास्ते से आएगा और देर हो सकती है। कुछ दिन का अतिरिक्त सामान रखें।"))
    hits = [(i, en, hi) for i, (ws, en, hi) in enumerate(TOPICS) if _has(t, ws)][:3]
    pts += [(en, hi) for _, en, hi in hits]
    if v["depots"] and any(i <= 3 for i, _, _ in hits):  # a supply or rescue need: say where the nearest depot is
        d = v["depots"][0]
        pts.append((f"Nearest depot by safe road: {d['name']}, {d['km']} km.", f"सुरक्षित सड़क से सबसे नज़दीकी डिपो: {d['name']}, {d['km']} किमी।"))
    if not hits:
        pts.append(("Send a help request on the Report tab so the control room knows what you need.",
                    "रिपोर्ट टैब पर मदद का अनुरोध भेजें ताकि कंट्रोल रूम को पता चले कि आपको क्या चाहिए।"))
    pts.append((f"In danger? Dial {EMERGENCY}.", f"खतरे में हैं? {EMERGENCY} डायल करें।"))
    return [e for e, _ in pts[:6]], [h for _, h in pts[:6]]


def impact_template(v):
    """What a flood or landslide is likely to do to one village (v from build_state). Plain fallback for the AI impact points. Returns (english, hindi)."""
    n, en, hi = v["name"], [], []
    if v["status"] == "Isolated":
        en.append(f"No safe road reaches {n} now, so food, medicine and fuel trucks cannot arrive until a road reopens.")
        hi.append(f"अभी {n} तक कोई सुरक्षित सड़क नहीं पहुँचती, इसलिए सड़क खुलने तक खाना, दवा और ईंधन के ट्रक नहीं आ पाएँगे।")
    elif v["status"] == "Detour":
        en.append(f"Deliveries to {n} must take a longer road and may be late. Stock left: {v['stock_days']} days.")
        hi.append(f"{n} तक सामान लंबे रास्ते से आएगा और देर हो सकती है। बचा हुआ सामान: {v['stock_days']} दिन।")
    else:
        en.append(f"The road to {n} is open now, but heavier rain can still cut it, so keep a few extra days of supplies.")
        hi.append(f"{n} की सड़क अभी खुली है, लेकिन ज़्यादा बारिश में यह कट सकती है, इसलिए कुछ दिन का अतिरिक्त सामान रखें।")
    if v["fruit_t"] > 0:
        en.append(f"About {v['fruit_t']} tonnes of fruit and vegetables from here could spoil if trucks cannot leave.")
        hi.append(f"यहाँ का लगभग {v['fruit_t']} टन फल और सब्ज़ी खराब हो सकती है अगर ट्रक न निकल पाएँ।")
    en.append("Floods also bring dirty water, power cuts and sickness, so boil water and stay away from fallen wires.")
    hi.append("बाढ़ के साथ गंदा पानी, बिजली कटना और बीमारियाँ भी आती हैं, इसलिए पानी उबालकर पिएँ और गिरे हुए तारों से दूर रहें।")
    return en, hi
