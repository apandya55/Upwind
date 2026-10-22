"""Public analysis orchestration; explicit evidence and bounded mixture design.

The previous engine remains in legacy.py solely for reproducible comparisons.
"""

from functools import lru_cache
from itertools import combinations
import hashlib
import json
import math
import time
from types import SimpleNamespace
import numpy as np
from .models import Investigation
from .numerics import projector as projector, flow_vector, plume as plume
from .quality import measurement_quality
from .inference import fit, region, MODEL_VERSION, PROTOCOL_VERSION, CONFIG
from .design import design_score
from .prediction_design import prediction_score
from .identifiability import diagnose_fit
from .weather import matched_weather
from .legacy import spatial_projector, eligible_indices, select_plan


def clean_measurements(inv):
    return measurement_quality(inv)[0]


def ensemble(inv):
    """Numerical fit without repeated diagnostic refits (analysis includes them)."""
    return fit(inv, diagnostics=False)


def planning_score(inv, fitted, **budgets):
    # Canonical site dimensions keep QMC integration and approximation invariant
    # under UI/import list permutations. Predictions use the update timestamp.
    order = sorted(range(len(inv.sites)), key=lambda i: inv.sites[i].id)
    rank = {index: i for i, index in enumerate(order)}
    timestamp = max(r.timestamp for r in clean_measurements(inv))
    future_ids = [f"followup-{s.id}" for s in inv.sites]

    def predictive(indices):
        original = [order[i] for i in indices]
        points = [inv.sites[i] for i in original]
        observed_scenarios = [
            SimpleNamespace(
                timestamp=timestamp, latitude=p.latitude, longitude=p.longitude
            )
            for p in points
        ]
        met, _, _ = matched_weather(inv, observed_scenarios, fitted["projection"])
        return fitted["predictive"](
            points, [timestamp] * len(points), [future_ids[i] for i in original], met
        )

    inner, metadata = design_score(
        fitted["weights"],
        fitted["groups"],
        predictive,
        inv.settings.seed,
        component_keys=fitted["component_keys"],
        **budgets,
    )

    def score(indices):
        return inner([rank[i] for i in indices])

    metadata["target"] = (
        "background-only versus nearest-anchor geographic partitions; conditional observed-window model, not source responsibility"
    )
    metadata["measurement_timestamp"] = timestamp
    metadata["future_instrument_ids"] = (
        "followup-{candidate ID}; independent new instruments unless this ID exists in history"
    )
    return score, metadata


def information_matrices(e, noise):
    """Legacy Gaussian-moment diagnostic, retained for comparisons only.

    Not the production acquisition objective. Use planning_score for new plans.
    """
    points = []
    for x, y in e["site_xy"]:
        lon, lat = e["projection"].transform(x, y, direction="INVERSE")
        points.append({"latitude": lat, "longitude": lon})
    p, cov = e["predictive"](points)
    w, groups = e["weights"], e["groups"]
    mu = w @ p
    within = np.einsum("k,kij->ij", w, cov)
    between = np.zeros_like(within)
    for group in np.unique(groups):
        mask = groups == group
        mass = w[mask].sum()
        if mass < 1e-15:
            continue
        conditional = w[mask] / mass
        local = conditional @ p[mask]
        dev = p[mask] - local
        within += mass * (dev.T * conditional) @ dev
        between += mass * np.outer(local - mu, local - mu)
    return within, between


def analyze(inv: Investigation):
    canonical = Investigation.model_validate_json(inv.model_dump_json())
    payload = canonical.model_dump(
        exclude={
            "result",
            "plan_history",
            "id",
            "archived_results",
            "compatibility_notes",
        }
    )
    configuration = hashlib.sha256(
        json.dumps(CONFIG, sort_keys=True).encode()
    ).hexdigest()
    return json.loads(
        _cached_analysis(json.dumps(payload, sort_keys=True), configuration)
    )


@lru_cache(maxsize=32)
def _cached_analysis(payload, configuration=""):
    inv = Investigation.model_validate_json(payload)
    started = time.perf_counter()
    key = hashlib.sha256((MODEL_VERSION + configuration + payload).encode()).hexdigest()
    warnings = [
        "Experimental conditional scenario weights; no field-validated attribution or geographic coverage calibration.",
        "Future scheduling is unsupported. Plans compare hypothetical simultaneous observations in the observed steady window, using its historical wind; no future observed weather is used.",
        "A background-only explanation competes with one steady release. Humidity response and sparse two-source alternatives are explicitly screened, while chemistry, urban transport and responsibility remain unidentified.",
    ]
    if inv.synthetic:
        warnings.insert(
            0,
            "SYNTHETIC investigation: simulated inputs, not field validation; row origins are preserved.",
        )
    e, reason = None, None
    try:
        e = fit(inv, diagnostics=True)
    except (ValueError, OverflowError, FloatingPointError, np.linalg.LinAlgError) as exc:
        reason = str(exc)
    _, quality = measurement_quality(inv)
    base = {
        "model_version": MODEL_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "input_hash": key,
        "quality": quality,
        "rows_loaded": len(inv.measurements),
        "rows_excluded": quality["excluded_rows"] + quality["identical_duplicates"],
        "rows_input": quality["usable_unique_rows"],
        "selection": {
            "method": "balanced sensor×period strata, rare-departure/endpoints/extrema then seeded temporal strata"
            if inv.study_windows
            else "balanced sensors, rare-departure/endpoints/extrema then seeded temporal strata",
            "limit": inv.settings.inference_limit,
            "seed": inv.settings.selection_seed,
        },
    }
    if inv.settings.objective != "spatial_coverage" and e is None:
        return json.dumps(
            base
            | {
                "status": "insufficient_data",
                "reason": reason,
                "warnings": warnings,
                "plans": [],
                "sources": [],
                "rows_used": 0,
            },
            allow_nan=False,
        )
    eligible = eligible_indices(inv)
    design = None
    if inv.settings.objective != "spatial_coverage":
        unsupported = [
            inv.sites[i].id for i in eligible if not e["candidate_supported"][i]
        ]
        eligible = [i for i in eligible if e["candidate_supported"][i]]
        if unsupported:
            warnings.append(
                "Excluded candidates whose distance is unsupported for some source-domain cells: "
                + ", ".join(unsupported)
            )
        if inv.settings.objective == "prediction_variance":
            score, design = prediction_score(inv, e)
            interpretation = "Mean Bayes-linear prediction-variance reduction at all permissible supported candidate receptors, in (µg/m³)². Separate target-instrument noise is not credited as learning. This targets concentration prediction, not source attribution, health benefit or guaranteed field improvement."
        else:
            score, design = planning_score(inv, e)
            interpretation = "Numerical expected information about background-only versus coarse source regions (nats), under a moment-matched predictive mixture conditioned on existing readings. This is an experimental model score, not demonstrated field benefit."
    else:
        if not inv.sites:
            return json.dumps(
                base
                | {
                    "status": "infeasible",
                    "reason": "Add candidate sites.",
                    "plans": [],
                    "sources": [],
                    "warnings": warnings,
                    "rows_used": 0,
                }
            )
        tr = spatial_projector(inv)
        xy = np.array([tr.transform(s.longitude, s.latitude) for s in inv.sites])
        if not np.isfinite(xy).all() or np.linalg.norm(xy, axis=1).max() > 100000:
            raise ValueError("Spatial coverage requires a local study within 100 km")
        anchors = [i for i, s in enumerate(inv.sites) if s.kind == "sensor"]
        targets = xy[
            [
                i
                for i, s in enumerate(inv.sites)
                if s.kind == "candidate"
                and s.allowed
                and s.power
                and s.access
                and inv.settings.window in s.windows
            ]
        ]

        def covered(indices):
            chosen = indices + anchors
            return (
                float(
                    np.exp(
                        -np.linalg.norm(
                            targets[:, None] - xy[chosen][None], axis=-1
                        ).min(axis=1)
                        / 400
                    ).mean()
                )
                if chosen and len(targets)
                else 0.0
            )

        initial = covered([])
        score = lambda indices: max(0.0, covered(indices) - initial)
        interpretation = "Increment in mean spatial coverage over all permissible targets; exp(-distance/400m). A transparent geometric baseline, not pollution or health benefit."
        if reason:
            warnings.append("Source reconstruction unavailable: " + reason)
    if quality["conflicting_keys"]:
        warnings.append(
            f"Excluded {len(quality['conflicting_keys'])} conflicting sensor/time groups; resolve originals."
        )
    if e and e["rows_input"] > e["rows_used"]:
        warnings.append(
            f"Bounded inference uses {e['rows_used']} of {e['rows_input']} usable rows; rare-departure/extrema and temporal strata selection is not full-data inference. Validate sensitivity before interpretation."
        )
    rng = np.random.default_rng(inv.settings.seed)

    def pack(method, chosen):
        val = score(chosen)
        return {
            "method": method,
            "site_ids": [inv.sites[i].id for i in chosen],
            "cost": sum(inv.sites[i].cost for i in chosen),
            "score": val,
            "equipment": len(chosen),
            "window": inv.settings.window,
        }

    optimized = select_plan(inv, "information", score, eligible, rng)
    # Bound exact scientific score evaluations, not just candidate count.
    subset_upper = sum(
        math.comb(len(eligible), k)
        for k in range(min(inv.settings.equipment_limit, len(eligible)) + 1)
    )
    exact = subset_upper <= 256
    feasible_count, ties = 0, 0
    if exact:
        best = 0.0
        optimized = []
        for k in range(min(inv.settings.equipment_limit, len(eligible)) + 1):
            for subset in combinations(eligible, k):
                if sum(inv.sites[i].cost for i in subset) > inv.settings.budget + 1e-9:
                    continue
                feasible_count += 1
                val = score(list(subset))
                if val > best + 1e-10:
                    best, optimized, ties = val, list(subset), 1
                elif abs(val - best) <= 1e-10:
                    ties += 1
    label = (
        "Prediction variance"
        if inv.settings.objective == "prediction_variance"
        else "Experimental information"
    )
    plans = [
        pack(
            label + " · exhaustive" if exact else label + " · greedy",
            optimized,
        ),
        pack("Spatial spread", select_plan(inv, "spread", score, eligible, rng)),
    ]
    randoms = [
        pack(
            "Random",
            select_plan(
                inv,
                "random",
                score,
                eligible,
                np.random.default_rng(inv.settings.seed + i),
            ),
        )
        for i in range(20)
    ]
    plans.append(
        randoms[0]
        | {
            "method": "Random · seed " + str(inv.settings.seed),
            "mean_score": float(np.mean([p["score"] for p in randoms])),
            "min_score": min(p["score"] for p in randoms),
            "max_score": max(p["score"] for p in randoms),
            "seeds": 20,
        }
    )
    if e is not None:
        flow = flow_vector(e["wind"])
        center = np.mean(e["source_xy"], axis=0)

        def priority(i):
            delta = e["site_xy"][i] - center
            return -(
                float(delta @ flow)
                - abs(float(flow[0] * delta[1] - flow[1] * delta[0]))
            )

        plans.append(
            pack(
                "Wind corridor",
                select_plan(
                    inv,
                    "wind",
                    score,
                    sorted(eligible, key=lambda i: (priority(i), inv.sites[i].id)),
                    rng,
                ),
            )
        )
    if not exact:
        best = max(plans, key=lambda p: (p["score"], -p["cost"], -p["equipment"]))
        optimized = (
            [i for i, s in enumerate(inv.sites) if s.id in best["site_ids"]]
            if best["score"] > 1e-10
            else []
        )
        plans[0] = pack(label + " · best heuristic", optimized) | {
            "origin_method": best["method"]
        }
    source_region = region(e) if e else None
    source_probability = e["source_probability"] if e else None
    predictive_warning = e["diagnostics"]["predictive_warning"] if e else False
    weather_warning = e["meteorology"]["weather_warning"] if e else False
    observability = None
    if e:
        try:
            observability = diagnose_fit(e, inv.settings.noise_ug_m3)
        except (ValueError, OverflowError, FloatingPointError, np.linalg.LinAlgError) as exc:
            # A fit can be numerically valid while a bounded secondary
            # diagnostic is unavailable for malformed or ill-conditioned input.
            # Preserve the posterior and raw data, but never silently turn an
            # unavailable adequacy check into source support.
            observability = {
                "method": "Source-adequacy diagnostics unavailable",
                "diagnostic_error": str(exc),
                "profile_compatible_domain_fraction": 1.0,
                "far_compatible_cells": None,
                "profile_background_improvement": None,
                "profile_best_strength_ug_s": None,
                "conditional_location_information_nats": None,
                "windows_observed": e.get("window_count", 0),
                "nuisance_rank": None,
                "source_count": {
                    "material_competing_pair": False,
                    "diagnostic_unavailable": True,
                    "meaning": "Source-count adequacy was not evaluated; the result cannot support a resolved source label.",
                },
                "externalities": {
                    "flags": ["adequacy_diagnostic_unavailable"],
                    "blocking": True,
                    "meaning": "A numerical or structural adequacy diagnostic failed; this is a refusal to resolve, not a diagnosis of a real externality.",
                },
                "meaning": "The posterior remains conditional, but source adequacy could not be checked.",
            }
            warnings.append(
                "SOURCE-ADEQUACY DIAGNOSTIC UNAVAILABLE: the conditional posterior is retained, but the engine withholds source support until the diagnostic can be evaluated."
            )
    externality = observability.get("externalities", {}) if observability else {}
    source_count = observability.get("source_count", {}) if observability else {}
    resolved = bool(
        e
        and source_probability >= 0.9
        and source_region["domain_area_m2"] > 0
        and source_region["area_m2"] < 0.5 * source_region["domain_area_m2"]
        and not predictive_warning
        and not weather_warning
        and not e["location_estimate"]["domain_limited"]
        and not externality.get("blocking", False)
        and not source_count.get("material_competing_pair", False)
        and not source_count.get("diagnostic_unavailable", False)
    )
    evidence_status = (
        "model_mismatch"
        if predictive_warning or weather_warning
        else "source_supported"
        if resolved
        else "ambiguous"
    )
    if e:
        if e["location_estimate"]["domain_limited"]:
            warnings.append(
                "SEARCH DOMAIN LIMIT: at least half of conditional source mass lies in the outer 10% strip of the declared rectangle. Reconsider the search area with independent evidence; this result does not support localization within the chosen area. Edge mass cannot detect every source outside it."
            )
        if e["quadrature_diagnostics"].get("limitation"):
            warnings.append(e["quadrature_diagnostics"]["limitation"])
        if weather_warning:
            warnings.append(
                "WEATHER COMPARISON MISMATCH: paired weather evidence is inconsistent with a shared station correction or requires a direction change outside its supported local circular approximation. Source localization is not supported."
            )
        if e["meteorology"]["status"] == "unverified":
            warnings.append(
                "Weather accuracy is UNKNOWN. Persistent station bias is marginalized in addition to declared short-period uncertainty. A low pollution residual does not verify wind. Additional independent weather evidence may be needed; pollution plans do not budget weather hardware."
            )
        if observability["profile_compatible_domain_fraction"] > 0.7:
            warnings.append(
                "INFORMATION LIMIT: nuisance-profile calculations find compatible explanations over more than 70% of the supported domain. Additional repeats in the same wind may not locate a source; compare feasible layouts or independently steady wind windows. This diagnostic is not a calibrated confidence region."
            )
        if source_count.get("material_competing_pair", False):
            warnings.append(
                "MULTI-SOURCE ALTERNATIVE: a bounded two-source GLS profile materially improves the fit. The one-source location is withheld until independent evidence separates source count and release timing."
            )
        if source_count.get("diagnostic_unavailable", False):
            warnings.append(
                "SOURCE-COUNT ADEQUACY UNAVAILABLE: at least one bounded competing-source fit was numerically non-finite. The posterior is retained, but source support is withheld until the adequacy diagnostic can be evaluated."
            )
        for flag in externality.get("flags", []):
            warnings.append(
                "EXTERNALITY SIGNAL: "
                + flag.replace("_", " ")
                + ". Residual structure can reflect instrument response, meteorology, chemistry or changing emissions; it is not a source identification."
            )
        if inv.study_windows:
            warnings.append(
                "Campaign analysis assumes one fixed source and constant release across independently steady windows; each window has its own background/trend. Changes in release, transport or sensor response can invalidate localization. Wind transitions are not simulated."
            )
        if e["excluded_domain_area_m2"] > 0:
            warnings.append(
                f"Source domain excludes {e['excluded_domain_area_m2']:.1f} m² of cells outside the 20 m–3 km kernel support at existing monitors; any truth there is outside this conditional result."
            )
        if source_region["resolution_m"] > 20.01:
            warnings.append(
                "Source-domain cells exceed the 20m target resolution because of the 24-per-axis cap. Quadrature can miss narrow plumes; assess resolution sensitivity."
            )
        if predictive_warning:
            warnings.append(
                "MODEL MISMATCH: a withheld-sensor or withheld-period contrast block failed the declared joint predictive screen. Review meteorology, instrument behavior, background and multiple-source explanations; the screen has false negatives and is not field calibrated."
            )
        if len({m.sensor_id for m in e["rows"]}) < 3:
            warnings.append(
                "Predictive adequacy could not be checked: fewer than three usable sensors. A sharp model weight is not an adequacy certificate."
            )
        if any(
            m.humidity_percent is not None and m.humidity_percent >= 80
            for m in inv.measurements
        ):
            warnings.append(
                "High humidity is recorded; no instrument-specific humidity correction or calibration is inferred. Verify instrument response independently."
            )
        if not resolved:
            warnings.append(
                "Source location is not resolved under the declared evidence rule. Spatial spread remains available as a geometric baseline; neither plan has demonstrated field benefit."
            )
    sources = (
        []
        if e is None
        else [
            {
                "id": f"S{i + 1}",
                **p.model_dump(),
                "weight": float(e["location_weights"][i]),
                "meaning": "nearest-anchor partition conditional on single source, not probability at this point",
            }
            for i, p in enumerate(inv.source_locations)
        ]
    )
    entropy = (
        None
        if e is None
        else float(
            -np.sum(
                e["location_weights"]
                * np.log(np.maximum(e["location_weights"], 1e-300))
            )
        )
    )
    # Negative integration estimates remain in metadata and in raw scores. Archived
    # score schema permits real-valued estimates; no clipping disguises them.
    result = base | {
        "status": "ok" if optimized else "uninformative" if eligible else "infeasible",
        "reason": None
        if optimized
        else "Feasible candidates have no positive estimated information above numerical tie tolerance."
        if eligible
        else "No feasible plan: check budget, permission, power, access, source-distance support and window.",
        "plans": plans,
        "sources": sources,
        "source_probability": source_probability,
        "evidence_status": evidence_status,
        "source_region90": source_region,
        "diagnostics": None if e is None else e["diagnostics"],
        "planning_diagnostics": design,
        "observability": observability,
        "study_window_count": 0 if e is None else e["window_count"],
        "meteorology_evidence": None if e is None else e["meteorology"],
        "location_estimate": None if e is None else e["location_estimate"],
        "quadrature_diagnostics": None if e is None else e["quadrature_diagnostics"],
        "spatial_quadrature_order": None
        if e is None
        else e["spatial_quadrature_order"],
        "meteorology_uncertainty": {
            "direction_sd_deg": inv.settings.met_direction_sd_deg,
            "speed_fraction": inv.settings.met_speed_fraction,
            "provenance": inv.settings.met_uncertainty_provenance,
        },
        "physical_heights_m": {
            "source": inv.settings.source_height_m,
            "receptor": inv.settings.receptor_height_m,
        },
        "recommendation_status": "research_only",
        "interpretation": interpretation,
        "warnings": warnings,
        "eligible_sites": len(eligible),
        "exact_search": exact,
        "feasible_subsets": feasible_count if exact else None,
        "ties": ties if exact else None,
        "entropy_nats": entropy,
        "fitted_rmse_ug_m3": None if e is None else e["rmse"],
        "standardized_residual_rms": None
        if e is None
        else e["standardized_residual_rms"],
        "rows_used": 0 if e is None else e["rows_used"],
        "scenario_count": 0 if e is None else e["scenario_count"],
        "runtime_ms": round((time.perf_counter() - started) * 1000, 2),
    }
    return json.dumps(result, allow_nan=False)
