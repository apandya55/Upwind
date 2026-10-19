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


def scientific_summary(result, esc):
    """Keep conditional model output distinct from field reliability in exports."""
    pieces = []
    status = result.get("evidence_status")
    if status:
        labels = {
            "source_supported": "Single-source explanation supported within the implemented model",
            "ambiguous": "Source not identified: available measurements remain ambiguous",
            "model_mismatch": "Source not established: weather or held-out predictive checks flag a mismatch",
        }
        pieces.append(f"<p class='banner'>{esc(labels.get(status, status))}.</p>")
        probability = result.get("source_probability")
        if probability is not None:
            pieces.append(
                f"<p>Conditional single-source model weight: {probability:.4f}; "
                f"background-only model weight: {1 - probability:.4f}. These compare the implemented explanations, "
                "not real-world responsibility. A background-only result does not prove an absence of pollution or other sources.</p>"
            )
        diagnostics = result.get("diagnostics") or {}
        adequacy = (
            "Predictive warning raised."
            if diagnostics.get("predictive_warning")
            else "No predictive warning raised; this cannot establish physical correctness."
            if any(
                "rmse_ug_m3" in check and not check.get("unavailable")
                for check in diagnostics.get("held_out_sensor", [])
            )
            else "No held-out sensor predictive check available."
        )
        pieces.append(
            f"<p><strong>Model adequacy:</strong> {esc(adequacy)} "
            "<strong>Identifiability:</strong> the evidence label is an interpretive rule about the implemented model families. "
            "<strong>Empirical reliability:</strong> synthetic evaluation only; weights, regions, and labels are not field calibrated. "
            "Reproducible computation does not establish any of these scientific properties.</p>"
        )
    region = result.get("source_region90")
    location = result.get("location_estimate")
    if location:
        pieces.append(
            f"<p><strong>Conditional source uncertainty:</strong> spatial RMS {location['spatial_rms_m']:.1f} m; "
            f"outer-domain-strip mass {100 * location['edge_mass']:.1f}%; domain limited: {esc(location['domain_limited'])}. "
            f"{esc(location['meaning'])} Coordinates remain in the private JSON export.</p>"
        )
    if region:
        pieces.append(
            f"<p>Conditional 90% model region: {region['area_m2'] / 1e6:.4f} km² "
            f"of a {region['domain_area_m2'] / 1e6:.4f} km² declared domain; "
            f"approximately {region['resolution_m']:.1f} m quadrature cells. "
            f"{esc(region['meaning'])}. Domain: {esc(region['support'])}. "
            "This region is conditional on a single source inside that domain and the assumed transport/noise model. "
            "Its nominal probability is not independently measured geographic coverage. "
            "The model assumes the source lies inside the declared rectangle; boundary weight cannot establish domain completeness. "
            "Cells target 20 m with at most 24 cells per side; larger domains have coarser numerical resolution. "
            "Location polygons and exact domain anchors remain in the private investigation JSON.</p>"
        )
    if "rows_loaded" in result:
        selection = result.get("selection", {})
        pieces.append(
            f"<p>Observations: {esc(result['rows_loaded'])} loaded; "
            f"{esc(result.get('rows_excluded', 0))} excluded; "
            f"{esc(result.get('rows_input', result.get('rows_used', 0)))} usable; "
            f"{esc(result.get('rows_used', 0))} fitted. "
            f"Selection: {esc(selection.get('method', 'not supplied'))}; "
            f"limit {esc(selection.get('limit', 'not supplied'))}; "
            f"seed {esc(selection.get('seed', 'not supplied'))}. "
            "All original readings remain retained; loaded rows are not all claimed to have been fitted.</p>"
        )
    elif "rows_used" in result:
        pieces.append(
            f"<p>Archived analysis: {esc(result['rows_used'])} fitted rows. "
            "Separate loaded/excluded counts and the revised predictive checks were not recorded by that model.</p>"
        )
    diagnostics = result.get("diagnostics")
    if diagnostics:
        checks = ""
        for check in diagnostics.get("held_out_sensor", []):
            checks += f"<tr><td>{esc(check['sensor_id'])}</td><td>{check['rows']}</td>"
            if check.get("unavailable") or "rmse_ug_m3" not in check:
                checks += f"<td colspan='4'>Check unavailable: {esc(check.get('unavailable', 'no prediction returned'))}</td></tr>"
            else:
                metrics = [
                    check.get(key) for key in ["rmse_ug_m3", "coverage90", "mean_nlpd"]
                ]
                checks += "".join(
                    f"<td>{value:.3f}</td>"
                    if value is not None
                    else "<td>unavailable</td>"
                    for value in metrics
                )
                checks += f"<td>{esc(check['flagged'])}</td></tr>"
        pieces.append(
            f"<details><summary>Held-out sensor predictive checks</summary><p>{esc(diagnostics['method'])}</p>"
            "<table><thead><tr><th>Sensor</th><th>Held-out rows</th><th>RMSE µg/m³</th>"
            "<th>Conditional 90% interval coverage</th><th>Mean negative log predictive density</th>"
            f"<th>Flagged</th></tr></thead><tbody>{checks}</tbody></table>"
            "<p>These checks withhold complete sensors rather than treating adjacent readings as independent validation. "
            "They can miss physically different explanations that the observed layout cannot distinguish.</p></details>"
        )
        window_checks = diagnostics.get("held_out_window", [])
        if window_checks:
            items = "".join(
                f"<li>{esc(c['window_id'])}: "
                + (
                    f"Unavailable: {esc(c['unavailable'])}"
                    if c.get("unavailable")
                    else f"Joint contrast tail {c['tail_probability']:.5f}; screen threshold {c['screen_alpha']:.5f}; flagged: {esc(c['flagged'])}"
                )
                + "</li>"
                for c in window_checks
            )
            pieces.append(
                "<details><summary>Cross-period predictive checks</summary>"
                "<p>Entire periods' concentrations withheld; recorded weather retained. "
                "Constant background and linear trend projected out to test spatial contrasts. "
                "These are retrospective checks, not future forecasts or calibrated adequacy probabilities.</p>"
                f"<ul>{items}</ul></details>"
            )
    observation = result.get("observability")
    weather = result.get("meteorology_evidence")
    if weather:
        if "common_mode_posterior_probability" in weather:
            pieces.append(
                f"<p>Shared weather-error alternative: prior {100 * weather.get('common_mode_prior_probability', 0):.1f}%; "
                f"conditional source posterior {100 * weather['common_mode_posterior_probability']:.1f}%. "
                f"{esc(weather.get('common_mode_meaning', ''))}</p>"
            )
        pieces.append(
            "<h3>Weather accuracy and source ambiguity</h3>"
            f"<p>{'Independent comparison readings supplied; user-declared provenance.' if weather['status'] == 'comparison_supplied' else 'Weather accuracy UNKNOWN; no qualifying independent comparison.'} "
            f"{weather['comparison_count']} paired readings, {weather['independent_upstream_groups']} upstream groups. "
            f"Weather-only direction correction {weather['direction_comparison_correction_deg']:.2f}°; "
            f"persistent direction SD {weather['persistent_direction_sd_deg']:.2f}°; "
            f"speed factor {weather['speed_comparison_factor']:.3f}.</p>"
            f"<p>Pollution-conditioned wind offset {weather['pollution_conditioned_offset_mean_deg']:.2f}°; "
            f"source alternatives across wind offsets span {weather['source_weather_location_span_m']:.1f} m. "
            "Model inferences, not measured calibration or a confidence bound.</p>"
            f"<p>Weather inconsistency flagged: {esc(weather['weather_warning'])}. {esc(weather['meaning'])}</p>"
            f"<p>{esc(weather['additional_evidence'])}</p>"
        )
        if weather["unusable_comparisons"]:
            pieces.append(
                "<ul>"
                + "".join(
                    f"<li>{esc(w['source_id'])}: {esc(w['reason'])}</li>"
                    for w in weather["unusable_comparisons"]
                )
                + "</ul>"
            )
        if weather.get("comparisons_used"):
            pieces.append(
                "<details><summary>Comparison readings used (user-declared provenance)</summary><ul>"
                + "".join(
                    f"<li>{esc(w['source_id'])}, upstream {esc(w['upstream_id'])}, {esc(w['timestamp'])}; lag {w['lag_s']:.1f}s, separation {w['distance_m']:.1f}m; {esc(w['origin'])}. {esc(w['provenance'])}</li>"
                    for w in weather["comparisons_used"]
                )
                + "</ul></details>"
            )
    if observation:
        pieces.append(
            f"<p><strong>Location distinguishability:</strong> {100 * observation['profile_compatible_domain_fraction']:.1f}% "
            "of supported area has similarly fitting explanations with adjustable release strength/background. "
            f"{esc(observation['meaning'])}</p>"
        )
    if result.get("study_window_count", 0) > 1:
        pieces.append(
            f"<p>Campaign: {result['study_window_count']} separately steady periods; "
            "one fixed source with constant release across periods is assumed. Background can differ. "
            f"Spatial quadrature order: {esc(result.get('spatial_quadrature_order'))}.</p>"
        )
    return "".join(pieces)


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
    weight_meaning = (
        "nearest-anchor partition weight, conditional on a single source; not probability at the marker"
        if result.get("source_region90")
        else "archived discrete-location conditional model weight; not a geographic confidence region"
    )
    weights = "".join(
        f"<li>{esc(s['id'])}: {s['weight']:.4f} {esc(weight_meaning)}</li>"
        for s in result.get("sources", [])
    )
    science = scientific_summary(result, esc)
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>UPWIND evidence summary</title>
<style>body{{font:15px/1.6 system-ui;max-width:980px;margin:40px auto;padding:0 24px;color:#162333}}h1{{font-size:36px}}h2{{margin-top:32px}}.banner{{padding:16px;background:#fff0c6;border-left:4px solid #b07800}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:8px;text-align:left;border-bottom:1px solid #c8d1d8}}code{{overflow-wrap:anywhere}}@media print{{body{{margin:0;font-size:11px}}h2{{break-after:avoid}}tr{{break-inside:avoid}}.banner{{border:2px solid}}}}</style>
<header><p>UPWIND / USER-REVIEWED EVIDENCE SUMMARY</p><h1>{esc(inv.name)}</h1><p>{esc(datetime.now(timezone.utc).isoformat())}</p></header>
<p class="banner">{esc(label)}. Review privacy, assumptions, and content before sharing. This is not a regulatory complaint, certification, or proof of source responsibility.</p>
<h2>Question and objective</h2><p>{esc(inv.concern)}</p><p>{esc(inv.objective)}</p>
<p>{esc(" ".join(inv.compatibility_notes))} Archived previous model results: {len(inv.archived_results)}; retained in private JSON, not recalibrated here.</p>
<h2>Observed measurements and episodes</h2><p>{len(inv.measurements)} retained readings; {len(inv.weather)} meteorology rows. This table shows up to 500 original normalized readings, not street-level interpolation. PM2.5 cannot identify composition or explain an odor by itself.</p><ul>{episodes}</ul><table><thead><tr><th>Sensor</th><th>UTC time</th><th>PM2.5 µg/m³</th><th>Flags</th><th>Origin</th></tr></thead><tbody>{readings}</tbody></table>
<h2>Provenance and quality</h2><ul>{sources}</ul><p>Instrument metadata: {esc(inv.instruments)}</p>
<h2>Practical constraints and selected plan</h2><p>Budget {inv.settings.budget:.2f} cost units; equipment limit {inv.settings.equipment_limit}. Only permitted sites with power, access, and the specified supported window are eligible.</p><table><thead><tr><th>Method</th><th>Sites</th><th>Cost units</th><th>Score</th><th>Window</th></tr></thead><tbody>{plans}</tbody></table><p>{esc(result.get("interpretation", "No plan generated"))}</p><p>Status: {esc(result.get("status", "unrun"))}. {esc(result.get("reason") or "")}</p>
<details><summary>Full practical-constraint snapshot</summary><table><thead><tr><th>Site</th><th>Kind</th><th>Cost</th><th>Permission</th><th>Power</th><th>Access</th><th>Windows</th></tr></thead><tbody>{constraints}</tbody></table></details>
<h2>Experimental conditional scenario weights</h2>{science}<ul>{weights}</ul><p>These are modelled quantities conditional on the declared source domain, model families, neutral open terrain, nuisance assumptions, local wind approximation, and stated measurement noise. They are not calibrated real-world probabilities. Multiple sources, street canyons, chemistry, and changing backgrounds may invalidate this model. A sharp weight or narrow region cannot establish responsibility.</p>
<p>Measurement recommendations compare experimental model scores or geometric coverage under the assumed observed window. They are not future forecasts or guaranteed improvements. The spread and random baselines remain available for review.</p>
<p>Assumptions: {esc(inv.assumptions.model_dump())}. Settings: {esc(inv.settings.model_dump())}.</p>
<h2>Resident observations</h2><p>User-entered accounts, separate from measurements and inference; locations rounded to about 1 km here.</p><ul>{obs}</ul>
<h2>Limits and unresolved questions</h2><ul>{warnings}<li>Independent PM2.5 source validation and external-user evaluation have not been performed.</li><li>Future scheduling unsupported: observed weather windows are retrospective only.</li><li>Could unmodelled sources, instrument bias, or background changes explain these readings?</li></ul>
<h2>Reproduction and evaluation status</h2><p>Model: {esc(result.get("model_version", "unrun"))}. Input hash: <code>{esc(result.get("input_hash", "unrun"))}</code>. Engine time: {esc(result.get("runtime_ms", "unrun"))} ms.</p><p>Evaluation evidence is synthetic only. External NOAA/Sagebrush and EPA dataset acquisition was blocked by the setup environment's network policy; no tracer or field validation claimed. Full raw CSVs and full-precision coordinates are retained in the separate private investigation JSON export. This report excludes raw CSV and source coordinates. Nothing was submitted to an outside party.</p>
<footer>UPWIND 0.1.0 · Built with AI assistance; see docs/AI_ASSISTANCE.md · Gaussian dispersion and experimental-design methods predate this project.</footer></html>"""
