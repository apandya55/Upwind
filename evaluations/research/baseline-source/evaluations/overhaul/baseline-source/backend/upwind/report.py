import csv
import html
import io
from datetime import datetime, timezone


def safe_cell(value):
    s = str(value)
    return (
        "'" + s
        if s.lstrip().startswith(("=", "+", "-", "@")) or s.startswith(("\t", "\r"))
        else s
    )


def measurements_csv(inv):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "sensor_id",
            "timestamp",
            "latitude",
            "longitude",
            "pm25_ug_m3",
            "flags",
            "origin",
        ]
    )
    for m in inv.measurements:
        writer.writerow(
            [
                safe_cell(m.sensor_id),
                m.timestamp,
                m.latitude,
                m.longitude,
                m.pm25_ug_m3,
                safe_cell(";".join(m.flags)),
                m.origin,
            ]
        )
    return out.getvalue()


def evidence_report(inv):
    esc = lambda x: html.escape(str(x))
    result = inv.result or {}
    label = (
        "SYNTHETIC DEMONSTRATION — contains simulated inputs; inspect row origins"
        if inv.synthetic
        else "USER-IMPORTED DATA — instrument accuracy and representativeness unverified"
    )
    sources = "".join(
        f"<li>{esc(i.filename)} · SHA256 {esc(i.sha256)} · {esc(i.summary)}<br>Transformations: {esc('; '.join(i.transformations))}</li>"
        for i in inv.imports
    )
    if not sources:
        sources = (
            "<li>Bundled fixed-seed synthetic fixture; seed 42 for the supplied example.</li>"
            if inv.synthetic
            else "<li>No recorded CSV imports.</li>"
        )
    plans = "".join(
        f"<tr><td>{esc(p['method'])}</td><td>{esc(', '.join(p['site_ids']) or 'None')}</td><td>{p['cost']:.2f}</td><td>{p['score']:.5f}</td><td>{esc(p['window'])}</td></tr>"
        for p in result.get("plans", [])
    )
    readings = "".join(
        f"<tr><td>{esc(m.sensor_id)}</td><td>{esc(m.timestamp)}</td><td>{m.pm25_ug_m3:.2f}</td><td>{esc(', '.join(m.flags) or 'No automatic flags')}</td><td>{esc(m.origin)}</td></tr>"
        for m in inv.measurements[:500]
    )
    usable = [
        m
        for m in inv.measurements
        if m.pm25_ug_m3 >= 0
        and not {"negative", "duplicate", "extreme_review"}.intersection(m.flags)
    ]
    episodes = ""
    for sensor in sorted({m.sensor_id for m in usable}):
        rows = [m for m in usable if m.sensor_id == sensor]
        peak = max(rows, key=lambda m: m.pm25_ug_m3)
        episodes += f"<li>{esc(sensor)}: observed maximum {peak.pm25_ug_m3:.2f} µg/m³ at {esc(peak.timestamp)} ({esc(peak.origin)}); {len(rows)} usable rows. Descriptive maximum, not an exposure standard or source finding.</li>"
    constraints = "".join(
        f"<tr><td>{esc(s.id)} · {esc(s.name)}</td><td>{esc(s.kind)}</td><td>{s.cost:.2f}</td><td>{esc(s.allowed)}</td><td>{esc(s.power)}</td><td>{esc(s.access)}</td><td>{esc(', '.join(s.windows))}</td></tr>"
        for s in inv.sites
    )
    obs = (
        "".join(
            f"<li>{esc(o.timestamp)} · approximate location ({o.latitude:.2f}, {o.longitude:.2f}) · {esc(o.note)}</li>"
            for o in inv.observations
        )
        or "<li>None recorded.</li>"
    )
    warnings = "".join(f"<li>{esc(w)}</li>" for w in result.get("warnings", []))
    weights = "".join(
        f"<li>{esc(s['id'])}: {s['weight']:.4f} conditional model weight</li>"
        for s in result.get("sources", [])
    )
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>UPWIND evidence summary</title>
<style>body{{font:15px/1.6 system-ui;max-width:980px;margin:40px auto;padding:0 24px;color:#162333}}h1{{font-size:36px}}h2{{margin-top:32px}}.banner{{padding:16px;background:#fff0c6;border-left:4px solid #b07800}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:8px;text-align:left;border-bottom:1px solid #c8d1d8}}code{{overflow-wrap:anywhere}}@media print{{body{{margin:0;font-size:11px}}h2{{break-after:avoid}}tr{{break-inside:avoid}}.banner{{border:2px solid}}}}</style>
<header><p>UPWIND / USER-REVIEWED EVIDENCE SUMMARY</p><h1>{esc(inv.name)}</h1><p>{esc(datetime.now(timezone.utc).isoformat())}</p></header>
<p class="banner">{esc(label)}. Review privacy, assumptions, and content before sharing. This is not a regulatory complaint, certification, or proof of source responsibility.</p>
<h2>Question and objective</h2><p>{esc(inv.concern)}</p><p>{esc(inv.objective)}</p>
<h2>Observed measurements and episodes</h2><p>{len(inv.measurements)} retained readings; {len(inv.weather)} meteorology rows. This table shows up to 500 original normalized readings, not street-level interpolation. PM2.5 cannot identify composition or explain an odor by itself.</p><ul>{episodes}</ul><table><thead><tr><th>Sensor</th><th>UTC time</th><th>PM2.5 µg/m³</th><th>Flags</th><th>Origin</th></tr></thead><tbody>{readings}</tbody></table>
<h2>Provenance and quality</h2><ul>{sources}</ul><p>Instrument metadata: {esc(inv.instruments)}</p>
<h2>Practical constraints and selected plan</h2><p>Budget {inv.settings.budget:.2f} cost units; equipment limit {inv.settings.equipment_limit}. Only permitted sites with power, access, and the specified supported window are eligible.</p><table><thead><tr><th>Method</th><th>Sites</th><th>Cost units</th><th>Score</th><th>Window</th></tr></thead><tbody>{plans}</tbody></table><p>{esc(result.get("interpretation", "No plan generated"))}</p><p>Status: {esc(result.get("status", "unrun"))}. {esc(result.get("reason") or "")}</p>
<details><summary>Full practical-constraint snapshot</summary><table><thead><tr><th>Site</th><th>Kind</th><th>Cost</th><th>Permission</th><th>Power</th><th>Access</th><th>Windows</th></tr></thead><tbody>{constraints}</tbody></table></details>
<h2>Experimental scenario comparison</h2><ul>{weights}</ul><p>These are modelled quantities conditional on a single steady source, neutral open terrain, discrete candidate locations, nuisance grid, local wind approximation, and stated measurement noise. They are not calibrated real-world probabilities. Multiple sources, street canyons, chemistry, and changing backgrounds may invalidate this model.</p>
<p>Assumptions: {esc(inv.assumptions.model_dump())}. Settings: {esc(inv.settings.model_dump())}.</p>
<h2>Resident observations</h2><p>User-entered accounts, separate from measurements and inference; locations rounded to about 1 km here.</p><ul>{obs}</ul>
<h2>Limits and unresolved questions</h2><ul>{warnings}<li>Independent PM2.5 source validation and external-user evaluation have not been performed.</li><li>Future scheduling unsupported: observed weather windows are retrospective only.</li><li>Could unmodelled sources, instrument bias, or background changes explain these readings?</li></ul>
<h2>Reproduction and evaluation status</h2><p>Model: {esc(result.get("model_version", "unrun"))}. Input hash: <code>{esc(result.get("input_hash", "unrun"))}</code>. Engine time: {esc(result.get("runtime_ms", "unrun"))} ms.</p><p>Evaluation evidence is synthetic only. External NOAA/Sagebrush and EPA dataset acquisition was blocked by the setup environment's network policy; no tracer or field validation claimed. Full raw CSVs and full-precision coordinates are retained in the separate private investigation JSON export. This report excludes raw CSV and source coordinates. Nothing was submitted to an outside party.</p>
<footer>UPWIND 0.1.0 · Built with AI assistance; see docs/AI_ASSISTANCE.md · Gaussian dispersion and experimental-design methods predate this project.</footer></html>"""
