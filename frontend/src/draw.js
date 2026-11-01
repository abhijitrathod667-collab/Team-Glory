// SVG drawing helpers. They only draw what the backend sends; no risk or route maths happens here.
const col = { Open: "var(--ok)", Watch: "var(--warn)", Cut: "var(--cut)" };
const W = 720, H = 480;  // map canvas; the coordinates in backend/app/sample_data.py use this size
const ring = { Supplied: "var(--ok)", Detour: "var(--warn)", Isolated: "var(--cut)" };
// Where to write each place name. It tries 8 spots around the place and keeps the one that is inside the map and touches the fewest
// roads, percent tags, places and earlier names.
function placeNames(st, P, pillBoxes) {
  const road = st.roads.flatMap(r => { const a = P[r.a], b = P[r.b]; return Array.from({ length: 30 }, (_, i) => [a.x + (b.x - a.x) * i / 29, a.y + (b.y - a.y) * i / 29]); });
  const taken = st.places.map(p => ({ id: p.id, box: [p.x - 16, p.y - 16, p.x + 16, p.y + 16] })).concat(pillBoxes.map(box => ({ id: "", box }))), out = {};
  for (const p of st.places) {
    const w = p.name.length * 8, spots = [["middle", p.x, p.y - 22, .3], ["middle", p.x, p.y + 34, .3], ["start", p.x + 22, p.y + 5, .2], ["end", p.x - 22, p.y + 5, .2],
      ["start", p.x + 14, p.y - 18, 0], ["end", p.x - 14, p.y - 18, 0], ["start", p.x + 14, p.y + 32, 0], ["end", p.x - 14, p.y + 32, 0]];
    let best = null;
    for (const [anchor, x, y, bonus] of spots) {
      const x0 = anchor === "middle" ? x - w / 2 : anchor === "start" ? x : x - w, box = [x0 - 2, y - 14, x0 + w + 2, y + 5];
      let score = bonus;
      if (box[0] < 4 || box[2] > W - 4 || box[1] < 2 || box[3] > H - 2) score -= 100;
      score -= 3 * road.filter(([px, py]) => px > box[0] && px < box[2] && py > box[1] && py < box[3]).length;
      score -= 20 * taken.filter(t => t.id !== p.id && !(t.box[2] < box[0] || t.box[0] > box[2] || t.box[3] < box[1] || t.box[1] > box[3])).length;
      if (!best || score > best.score) best = { score, anchor, x, y, box };
    }
    out[p.id] = best; taken.push({ id: "", box: best.box });
  }
  return out;
}
export function mapSvg(st, hl = []) {
  const P = Object.fromEntries(st.places.map(p => [p.id, p])), L = new Set(hl), V = Object.fromEntries(st.villages.map(v => [v.id, v.status]));
  let lines = "", pills = "", dots = "", names = "";
  const pillBoxes = [];
  st.roads.forEach(r => {
    const a = P[r.a], b = P[r.b], on = L.has(r.k), dim = L.size && !on, ln = `x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"`, mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    if (on) lines += `<line ${ln} stroke="var(--acc)" stroke-width="16" opacity=".25" stroke-linecap="round"/>`;
    lines += `<line ${ln} stroke="${col[r.status]}" stroke-width="${r.status === "Open" ? 4 : 5}" stroke-linecap="round" ${r.status === "Cut" ? 'stroke-dasharray="2 10"' : ""} opacity="${dim ? .3 : 1}"/>`;
    if (r.status !== "Open" || on) {  // only roads at risk (or on the chosen route) carry a percent label, so the map stays clean
      pillBoxes.push([mx - 23, my - 10, mx + 23, my + 10]);
      pills += `<g transform="translate(${mx},${my})" opacity="${dim ? .4 : 1}"><rect x="-23" y="-10" width="46" height="20" rx="10" fill="var(--card)" stroke="${col[r.status]}"/><text text-anchor="middle" y="4" font-size="11.5" font-weight="700" fill="var(--ink)">${r.risk}%</text></g>`;
    }
  });
  const spot = placeNames(st, P, pillBoxes);
  st.places.forEach(p => {
    if (p.kind === "depot") dots += `<rect x="${p.x - 15}" y="${p.y - 15}" width="30" height="30" rx="6" fill="var(--depot)"/><text x="${p.x}" y="${p.y + 5}" text-anchor="middle" font-size="14" font-weight="700" fill="#fff">${p.label.slice(-1)}</text>`;
    else {  // a village: its ring shows whether it is supplied, on a detour, or cut off
      const c = ring[V[p.id]] || "var(--ink)", unsafe = V[p.id] && V[p.id] !== "Supplied";
      dots += `<circle cx="${p.x}" cy="${p.y}" r="12" fill="var(--card)" stroke="${c}" stroke-width="4"/>` + (unsafe ? `<circle cx="${p.x}" cy="${p.y}" r="5" fill="${c}"/>` : "");
    }
    const t = spot[p.id];
    names += `<text x="${t.x}" y="${t.y}" text-anchor="${t.anchor}" font-size="14" font-weight="700" fill="var(--ink)" stroke="var(--map)" stroke-width="4" paint-order="stroke">${p.name}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Road network map"><path d="M 365 -20 Q 425 150 360 260 T 400 500" fill="none" stroke="var(--riv)" stroke-width="26" stroke-linecap="round" opacity=".5"/>` + lines + pills + dots + names + "</svg>";
}
export function chartSvg(st) {
  const F = st.forecast, W = 560, H = 170, X = i => 40 + i * (W - 60) / 6, Y = v => H - 20 - v / 160 * (H - 40), pts = F.map((v, i) => X(i) + "," + Y(v)).join(" ");
  return `<svg viewBox="0 0 ${W} ${H + 14}" role="img" aria-label="72-hour rain forecast">` + [0, 50, 100, 150].map(v => `<line x1="40" x2="${W - 20}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text x="34" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="var(--mut)">${v}</text>`).join("")
    + `<polygon points="${X(0)},${Y(0)} ${pts} ${X(6)},${Y(0)}" fill="var(--acc)" opacity=".15"/><polyline points="${pts}" fill="none" stroke="var(--acc)" stroke-width="3"/>`
    + `<line x1="40" x2="${W - 20}" y1="${Y(st.weakest_cut_mm)}" y2="${Y(st.weakest_cut_mm)}" stroke="var(--cut)" stroke-dasharray="6 5"/><text x="${W - 20}" y="${Y(st.weakest_cut_mm) + 16}" text-anchor="end" font-size="12" fill="var(--cut)">Weakest road is cut at about ${st.weakest_cut_mm} mm</text>`
    + `<line x1="40" x2="${W - 20}" y1="${Y(st.rain)}" y2="${Y(st.rain)}" stroke="var(--acc)" stroke-dasharray="2 4"/><text x="44" y="${Y(st.rain) - 5}" font-size="12" fill="var(--acc)">${st.what_if ? "What-if" : "Forecast"}: ${st.rain} mm</text>`
    + ["Now", "+12h", "+24h", "+36h", "+48h", "+60h", "+72h"].map((t, i) => `<text x="${X(i)}" y="${H + 8}" text-anchor="middle" font-size="11" fill="var(--mut)">${t}</text>`).join("") + "</svg>";
}
