import { useEffect, useState } from "react";
import { mapSvg, chartSvg } from "./draw.js";
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const call = async (p, o) => { const r = await fetch(API + p, o); const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d.detail || "Request failed"); return d; };
const post = (p, b) => call(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });
const Chip = ({ s, children }) => <span className={"chip " + s}>{children || s}</span>;
const Legs = ({ legs }) => legs.map((l, i) => <div className="row" key={i}><div className="n">{i + 1}</div><div className="grow"><b>{l.from} to {l.to}</b><div className="mut">{l.km} km · {l.risk}% risk{l.status === "Watch" ? ", drive with care" : ""}</div></div><Chip s={l.status} /></div>);
const Sel = ({ value, set, items, ph }) => <select value={value} onChange={e => set(e.target.value)}>{ph && <option value="">{ph}</option>}{items.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}</select>;
const ago = m => m === 0 ? "Just now" : m < 60 ? m + " min ago" : Math.floor(m / 60) + " hour" + (m >= 120 ? "s" : "") + " ago";
const Bi = ({ d }) => <div className="bi"><div><span className="mut">English</span><p>{d.en}</p></div><div><span className="mut">हिंदी</span><p lang="hi">{d.hi}</p></div><p className="mut">{d.source === "gemini" ? "Written by AI from the computed facts. Every number was checked against the data." : "Standard text (AI is off or unavailable)."}</p></div>;
const Steps = ({ d }) => <div className="bi">
  {d.impact_en && d.impact_en.length > 0 && <><b>What the flood could do here</b><div className="cols"><div><span className="mut">English</span><ul>{d.impact_en.map((x, i) => <li key={i}>{x}</li>)}</ul></div><div><span className="mut">हिंदी</span><ul lang="hi">{(d.impact_hi || []).map((x, i) => <li key={i}>{x}</li>)}</ul></div></div></>}
  <b>What to do now</b><div className="cols"><div><span className="mut">English</span><ol>{d.en.map((x, i) => <li key={i}>{x}</li>)}</ol></div><div><span className="mut">हिंदी</span><ol lang="hi">{d.hi.map((x, i) => <li key={i}>{x}</li>)}</ol></div></div>
  <p className="mut">{d.source === "gemini" ? "Written by AI from this village's facts plus general flood safety knowledge. Village numbers come from the app. Follow local officials. In danger, dial 112 first." : "Standard checklist (AI is off or unavailable). In danger, dial 112 first."}</p></div>;
const View = ({ id, tab, children }) => tab === id ? <section className="view on">{children}</section> : null;
const TABS = [["home", "🗺️", "Home"], ["check", "📍", "Check area"], ["routes", "🧭", "Routes"], ["report", "📢", "Report"], ["advice", "🛡️", "Advice"]];

export default function App() {
  const [tab, setTab] = useState("home"), [whatIf, setWhatIf] = useState(false), [wi, setWi] = useState(70), [st, setSt] = useState(null), [err, setErr] = useState("");
  const [vid, setVid] = useState("nadi"), [rf, setRf] = useState("kheri"), [rt, setRt] = useState("nadi"), [rte, setRte] = useState(null), [rteErr, setRteErr] = useState("");
  const [rd, setRd] = useState(""), [txt, setTxt] = useState(""), [ht, setHt] = useState(""), [hv, setHv] = useState(""), [hp, setHp] = useState(""), [msg, setMsg] = useState({}), [br, setBr] = useState(null), [al, setAl] = useState(null), [busy, setBusy] = useState(""), [pb, setPb] = useState(""), [ad, setAd] = useState(null);
  const rp = whatIf ? "rain=" + wi : ""; // no rain = the forecast
  const load = () => call("/api/state?" + rp).then(s => { setSt(s); setErr(""); }).catch(() => setErr("Could not reach the backend. Is it running on port 8000?"));
  useEffect(() => { let on = true; call("/api/state?" + rp).then(s => { if (on) { setSt(s); setErr(""); } }).catch(() => on && setErr("Could not reach the backend. Is it running on port 8000?")); setRte(null); return () => { on = false; }; }, [whatIf, wi]); // ignore slow replies from older slider positions
  const note = (k, cls, t) => setMsg(m => ({ ...m, [k]: [cls, t] }));
  if (!st) return <main><h1>ReliefLink</h1><p className={err ? "msg err" : "mut"}>{err || "Loading…"}</p></main>;
  const rain = st.rain, sig = String(rain); // rain actually used (forecast or what-if); AI texts are shown only while this is unchanged
  const v = st.villages.find(x => x.id === vid), vs = st.villages.map(x => ({ id: x.id, name: x.name })), roads = st.roads.map(r => ({ id: r.k, name: r.name }));
  const find = async () => { setRteErr(""); setRte(null); try { setRte(await call(`/api/route?src=${rf}&dst=${rt}&${rp}`)); } catch (e) { setRteErr(e.message); } };
  const sendReport = async () => { try { const r = await post("/api/reports", { road: rd, text: txt }); note("r", "good", `Report added as ${r.status} on ${r.road_name}.` + (r.verified ? " Two blocked reports verified this road as cut." : "") + (r.note ? " " + r.note : "") + (r.source === "gemini" ? " (read by AI)" : "")); setTxt(""); setBr(null); setAl(null); load(); } catch (e) { note("r", "err", e.message); } };
  const writeBrief = async () => { setBusy("b"); try { setBr({ sig, ...(await call("/api/brief?" + rp)) }); note("b", "", ""); } catch (e) { note("b", "err", e.message); } setBusy(""); };
  const writeAlert = async () => { setBusy("a"); try { setAl({ key: vid + ":" + sig, ...(await call(`/api/alert?village=${vid}&${rp}`)) }); note("a", "", ""); } catch (e) { note("a", "err", e.message); } setBusy(""); };
  const getAdvice = async () => { setBusy("d"); setAd(null); try { setAd({ key: vid + ":" + sig, ...(await post("/api/advice", { village: vid, problem: pb, rain: whatIf ? wi : undefined })) }); note("d", "", ""); } catch (e) { note("d", "err", e.message); } setBusy(""); };
  const sendHelp = async () => { try { const r = await post("/api/help", { type: ht, village: hv, people: Number(hp) || 0 }); note("h", "good", `${ht} for ${hp} people in ${vs.find(x => x.id === hv).name}. ${r.message}`); } catch (e) { note("h", "err", e.message); } };
  return <div className="app">
    <aside><div className="brand">Relief<b>Link</b></div>
      {TABS.map(([id, ic, label]) => <button key={id} className={"nav" + (tab === id ? " on" : "")} onClick={() => setTab(id)}><span aria-hidden="true">{ic}</span>{label}</button>)}
      <div className="side-note">Stock and village numbers are synthetic. In danger? Dial 112.</div></aside>
    <main>
      {err && <p className="msg err">{err}</p>}
      <View tab={tab} id="home"><h1>Keep relief moving when <span className="hl">roads break</span></h1><p className="mut sub">See which roads fail in the rain, which villages run short first, and the safest way to reach them.</p>
        <div className={"banner " + st.banner.level}><h3>{st.banner.level === "ok" ? "All roads open" : st.banner.level}</h3><p>{st.banner.text}</p></div>
        <div className="g2 home"><div>
          <div className="card"><h2>Risk map</h2><p className="mut">Rain comes from the 72-hour forecast, so nobody has to guess it. Use What-if only to test a heavier storm.</p>
            <div className="modes" role="group" aria-label="Rain source"><button className={whatIf ? "" : "on"} onClick={() => setWhatIf(false)}>Forecast (automatic)</button><button className={whatIf ? "on" : ""} onClick={() => setWhatIf(true)}>What-if</button></div>
            {whatIf ? <><div className="slider"><input type="range" min="0" max="160" value={wi} onChange={e => setWi(+e.target.value)} aria-label="What-if rain in millimetres" /><div className="mm">{wi} mm</div></div><p className="mut">What-if test, not a forecast. The forecast expects {st.forecast_mm} mm. <button className="link" onClick={() => setWhatIf(false)}>Back to forecast</button></p></>
              : <div className="slider"><div className="mm">{rain} mm</div><p className="mut">Expected over the next 72 hours (live forecast).</p></div>}
<div className="map" dangerouslySetInnerHTML={{ __html: mapSvg(st) }} />
            <div className="legend"><span><i style={{ background: "var(--ok)" }} />Open road / supplied village</span><span><i style={{ background: "var(--warn)" }} />Watch / detour</span><span><i style={{ background: "var(--cut)" }} />Cut / cut off</span><span><i style={{ background: "var(--depot)" }} />Depot</span></div></div>
          <div className="card"><h2>Rain forecast</h2><p className="mut">Next 72 hours (mm) against the rain where the weakest road is cut.</p><div dangerouslySetInnerHTML={{ __html: chartSvg(st) }} /></div></div>
          <div className="col">
            <div className="card"><div className="kpi">{st.kpi.affected}</div><p>Villages affected</p><p className="mut">of {st.kpi.villages} villages are on a detour or cut off · {st.roads.filter(r => r.status === "Cut").length} of {st.roads.length} roads cut</p></div>
            <div className="card"><div className="kpi">{st.kpi.depots}</div><p>Relief depots</p><p className="mut">{st.places.filter(p => p.kind === "depot").map(p => `${p.label} (${p.name})`).join(", ")}</p></div>
            <div className="card"><div className="kpi">{st.kpi.fruit_t.toFixed(1)} t</div><p>Fruit and vegetables at risk</p></div>
            <div className="card"><h2>Who needs help first</h2><p className="mut">Ranked by road access, stock left and fruit at risk.</p>
              <ol className="rank">{st.villages.map((x, i) => <li key={x.id}><div className="n">{i + 1}</div><div className="grow"><b>{x.name}</b><div className="mut">{x.stock_days} days of stock left</div></div><Chip s={x.status} /><Chip s={x.priority} /></li>)}</ol></div></div></div></View>
      <View tab={tab} id="check"><h1>Check your area</h1><div className="card"><label>Your village</label><Sel value={vid} set={setVid} items={vs} /></div>
        <div className="g3"><div className="card"><p className="mut">Status</p><Chip s={v.status} /></div><div className="card"><div className="kpi">{v.stock_days} days</div><p className="mut">Stock left</p></div><div className="card"><div className="kpi">{v.fruit_t.toFixed(1)} t</div><p className="mut">Fruit and vegetables at risk</p></div></div>
        <div className="card" style={{ marginTop: 16 }}><h2>Latest alert</h2><p>{v.alert}</p><button className="btn" onClick={writeAlert} disabled={busy === "a"}>{busy === "a" ? "Writing…" : "Show in Hindi + English"}</button>{al && al.key === vid + ":" + sig && <Bi d={al} />}{msg.a && msg.a[0] === "err" && <div className="msg err" role="status">{msg.a[1]}</div>}</div>
        <div className="g2"><div className="card"><h2>Roads on your route</h2><Legs legs={v.legs} /></div>
          <div className="card"><h2>Nearest depots by safe road</h2>{v.depots.length ? v.depots.map((d, i) => <div className="row" key={d.id}><div className="grow"><b>{d.name}</b><div className="mut">{d.stock} ration-days stocked</div></div><b>{d.km} km</b>{i === 0 && <Chip s="Open">Best choice</Chip>}</div>) : <p>No depot is reachable by a safe road right now.</p>}</div></div></View>
      <View tab={tab} id="routes"><h1>Safest route and relief plan</h1>
        <div className="card"><div className="g3"><div><label>From</label><Sel value={rf} set={setRf} items={st.places} /></div><div><label>To</label><Sel value={rt} set={setRt} items={st.places} /></div><div><button className="btn" onClick={find}>Find safest route</button></div></div>
          {rteErr && <p className="msg err">{rteErr}</p>}
          {rte && <><p className="msg">{rte.usual.cut.length ? `Your usual road is cut: ${rte.usual.cut.join(", ")} is closed.` : "Your usual road is open."}</p>
            <div className="g2" style={{ marginTop: 8 }}><div className="card"><h3>Usual route</h3><div className="kpi">{rte.usual.km} km</div><Chip s={rte.usual.cut.length ? "Cut" : "Open"} /></div>
              <div className="card"><h3>Safest route now</h3>{rte.safe ? <><div className="kpi">{rte.safe.km} km</div><Chip s={rte.safe.legs.some(l => l.status === "Watch") ? "Watch" : "Open"} /></> : <p><b>No safe route right now.</b> Call the district helpline.</p>}</div></div>
            {rte.safe && <div className="card"><h2>Step by step</h2><Legs legs={rte.safe.legs} /></div>}
            <div className="map" dangerouslySetInnerHTML={{ __html: mapSvg(st, rte.safe ? rte.safe.legs.map(l => l.k) : []) }} /></>}</div>
        <div className="card"><h2>Relief plan</h2><p className="mut">The worst-hit villages are served first, each from the nearest depot reachable by a safe road. Each village gets 3 days of rations.</p>
          <button className="btn" onClick={writeBrief} disabled={busy === "b"}>{busy === "b" ? "Writing…" : "Write briefing (English + Hindi)"}</button>{br && br.sig === sig && <Bi d={br} />}{msg.b && msg.b[0] === "err" && <div className="msg err" role="status">{msg.b[1]}</div>}
          <div className="scroll">{st.plan.length ? <table><thead><tr><th>#</th><th>Village</th><th>Needs</th><th>From</th><th>Route</th></tr></thead><tbody>{st.plan.map((p, i) => <tr key={p.village}><td>{i + 1}</td><td><b>{p.name}</b> <Chip s={p.status} /><div className="mut">{p.days} days left</div></td><td>3 days of rations</td><td>{p.depot || "No depot stock reachable"}</td><td>{p.km ? p.km + " km" : "–"}</td></tr>)}</tbody></table> : <p>No village needs relief at {rain} mm. All villages are reached by their usual road.</p>}</div></div></View>
      <View tab={tab} id="report"><h1>Report a problem</h1><div className="g2"><div>
        <div className="card"><h2>What did you see?</h2><p className="mut">Write in Hindi, Hinglish or English. We never ask for your name.{st.ai_configured ? " AI reads your report and finds the road. To help it, name both villages." : " Name both villages if you skip the road."}</p>
          <label>Road (optional)</label><Sel value={rd} set={setRd} items={roads} ph="Not sure? We will find it from your text" /><label>Your report</label><textarea maxLength={300} value={txt} onChange={e => setTxt(e.target.value)} placeholder="पत्थर गिर रहे हैं, गाड़ी नहीं निकल सकती" />
          <div className="chips">{["पत्थर गिर रहे हैं", "road band hai", "slush and fog", "road clear"].map(t => <button key={t} onClick={() => setTxt(t)}>{t}</button>)}</div>
          <button className="btn" onClick={sendReport}>Send report</button>{msg.r && <div className={"msg " + msg.r[0]} role="status">{msg.r[1]}</div>}</div>
        <div className="card"><h2>Request help</h2><p className="mut">Recorded in this demo only. Nothing is sent to anyone.</p>
          <div className="chips">{["Medicine", "Fuel", "Rescue", "Food"].map(t => <button key={t} className={ht === t ? "on" : ""} onClick={() => setHt(t)}>{t}</button>)}</div>
          <label>Village</label><Sel value={hv} set={setHv} items={vs} ph="Choose a village" /><label>How many people?</label><input type="number" min="1" max="500" value={hp} onChange={e => setHp(e.target.value)} />
          <button className="btn" onClick={sendHelp}>Save request</button>{msg.h && <div className={"msg " + msg.h[0]} role="status">{msg.h[1]}</div>}</div></div>
        <div className="card"><h2>Recent reports</h2><p className="mut">Two blocked reports on one road mark it as cut.</p>
          {st.reports.map((r, i) => <div className="row" key={i}><div className="grow"><b>{r.name}</b><div>{r.text}</div><div className="mut">{ago(r.age)}{r.note ? " · " + r.note : ""}</div></div><Chip s={r.status} /></div>)}</div></div></View>
      <View tab={tab} id="advice"><h1>Advice and safety</h1><div className="card"><label>Your village</label><Sel value={vid} set={setVid} items={vs} />
        <h2 style={{ marginTop: 14 }}>{v.name}: {v.status === "Supplied" ? "supplies are normal" : v.status === "Detour" ? "use the link road" : "no safe road right now"} <Chip s={v.status} /></h2>
        <p>{v.status === "Supplied" ? "Keep a few extra days of rations, medicine and fuel at home as a habit." : v.status === "Detour" ? "The main road may be cut. Trucks will come by the longer link road, so deliveries can be late." : "Stay where you are unless officials say otherwise, and send a help request if you run short of medicine, fuel or food."}</p>
        <p><b>Shopkeepers:</b> order stock today, before the road closes.</p><p><b>Farmers:</b> send apples and vegetables early, or use cold storage.</p></div>
        <div className="card"><h2>Tell us your problem</h2><p className="mut">Ask anything about floods, landslides or supplies, in Hindi, Hinglish or English. You get quick, specific advice for {v.name}. In danger? Dial 112 first.</p>
          <textarea maxLength={300} value={pb} onChange={e => setPb(e.target.value)} placeholder="दवा खत्म हो गई है और सड़क बंद है" />
          <div className="chips">{["दवा खत्म हो गई", "fuel is almost over", "ghar ke paas pathar gir rahe hain", "we are stuck, no food", "paani ghar mein aa raha hai", "is flood water safe to drink?"].map(t => <button key={t} onClick={() => setPb(t)}>{t}</button>)}</div>
          <button className="btn" onClick={getAdvice} disabled={busy === "d"}>{busy === "d" ? "Thinking…" : "Get steps"}</button>{msg.d && msg.d[0] === "err" && <div className="msg err" role="status">{msg.d[1]}</div>}
          {ad && ad.key === vid + ":" + sig && <Steps d={ad} />}</div>
        <div className="g2"><div className="card"><h2>If there is a flood</h2><p><b>Before:</b> keep a bag ready with documents, torch, medicines and dry food. Know the nearest high ground.</p><p><b>During:</b> move to higher ground early. Never walk or drive through flood water.</p><p><b>After:</b> do not go back until officials say it is safe. Drink only boiled or treated water.</p></div>
          <div className="card"><h2>If there is a landslide</h2><p><b>Warning signs:</b> new cracks in ground or walls, tilting trees, muddy water in streams.</p><p><b>During:</b> move away from the slope quickly. Do not drive under steep slopes in heavy rain.</p><p><b>After:</b> stay away from the slide area. More can follow.</p></div></div>
        <div className="card"><h2>Emergency</h2><p><b>Dial 112</b> for any emergency. For the district helpline, ask your panchayat office for the number.</p></div></View>
    </main></div>;
}
