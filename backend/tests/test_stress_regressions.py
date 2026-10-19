import numpy as np
import pytest
from upwind.engine import analyze, ensemble
from upwind.models import Investigation, ImportRequest, Weather
from upwind.fixtures import synthetic_case
from upwind.importers import parse_csv
from upwind.numerics import stable_information


def test_empty_sites_is_a_result_not_a_crash():
    inv, _ = synthetic_case()
    inv.sites = []
    r = analyze(inv)
    assert r["status"] == "infeasible" and len(r["sources"]) == 6


@pytest.mark.parametrize("uncertainty", [0, 1e-300, 1e300, float("nan"), float("inf")])
def test_unsupported_uncertainty_is_a_schema_refusal(uncertainty):
    inv, _ = synthetic_case()
    data = inv.model_dump()
    data["measurements"][0]["uncertainty_ug_m3"] = uncertainty
    with pytest.raises(ValueError):
        Investigation.model_validate(data)


def test_full_window_checks_unmatched_calm_weather():
    inv, _ = synthetic_case()
    inv.weather.append(
        inv.weather[0].model_copy(
            update={"timestamp": "2025-06-12T10:02:00+00:00", "wind_speed_m_s": 0.1}
        )
    )
    r = analyze(inv)
    assert r["status"] == "insufficient_data" and "Calm" in r["reason"]


def test_duplicate_source_hypotheses_refused():
    inv, _ = synthetic_case()
    inv.source_locations = [inv.source_locations[0]] * 2
    assert "1 m apart" in analyze(inv)["reason"]


def test_tiny_information_is_not_lost_to_logdet_subtraction():
    r = np.eye(2) * 1e8
    b = np.eye(2) * 1e-8
    score = stable_information(r, b, [0, 1])
    assert score == pytest.approx(np.log1p(1e-16), rel=1e-12, abs=0)


def test_permutation_invariance_and_conflicting_duplicates():
    inv, _ = synthetic_case()
    a = analyze(inv)
    inv.measurements = list(reversed(inv.measurements))
    inv.weather = list(reversed(inv.weather))
    inv.sites = list(reversed(inv.sites))
    b = analyze(inv)
    assert np.allclose(
        [s["weight"] for s in a["sources"]], [s["weight"] for s in b["sources"]]
    )
    assert set(a["plans"][0]["site_ids"]) == set(b["plans"][0]["site_ids"])
    inv.measurements.append(inv.measurements[0].model_copy(update={"pm25_ug_m3": 100}))
    assert analyze(inv)["quality"]["conflicting_keys"]


def test_north_equivalence_and_malformed_csv():
    w = Weather(
        timestamp="2025-01-01T00:00Z",
        latitude=0,
        longitude=0,
        wind_speed_m_s=2,
        wind_from_deg=360,
    )
    assert w.wind_from_deg == 0
    with pytest.raises(ValueError, match="Malformed"):
        parse_csv(
            ImportRequest(
                csv='sensor_id,timestamp,latitude,longitude,pm25_ug_m3\n"unclosed'
            )
        )
    with pytest.raises(ValueError, match="2 MB"):
        ImportRequest(csv="é" * 1_000_001)


def test_geometry_pair_out_of_domain_is_not_zero_evidence():
    inv, _ = synthetic_case()
    inv.measurements[0].latitude = inv.source_locations[0].latitude
    inv.measurements[0].longitude = inv.source_locations[0].longitude
    # Continuous-domain inference reports and excludes unsupported source area;
    # it must not call a near-field zero plume observation evidence against it.
    e = ensemble(inv)
    assert e["excluded_domain_area_m2"] > 0
    xy = np.array(
        e["projection"].transform(
            inv.measurements[0].longitude, inv.measurements[0].latitude
        )
    )
    closest = np.maximum(
        np.maximum(e["cells_xy"][:, :2] - xy, xy - e["cells_xy"][:, 2:]), 0
    )
    assert np.linalg.norm(closest, axis=1).min() >= 20
    assert any("domain excludes" in w for w in analyze(inv)["warnings"])


def test_balanced_selection_preserves_all_sensors_and_full_window():
    inv, _ = synthetic_case()
    inv.measurements = [m for m in inv.measurements if m.sensor_id == "M1"] * 20 + [
        m for m in inv.measurements if m.sensor_id == "M2"
    ]
    # Exact duplicates do not consume the fit-row budget.
    e = ensemble(inv)
    assert {m.sensor_id for m in e["rows"]} == {"M1", "M2"}
    inv.measurements.append(
        inv.measurements[0].model_copy(
            update={"timestamp": "2025-06-13T10:00:00+00:00"}
        )
    )
    assert "one hour" in analyze(inv)["reason"]


def test_reported_uncertainty_is_used_in_residual_diagnostic():
    from upwind.validation.cases import make_case

    inv, _ = make_case("high_noise", 110000)
    e = ensemble(inv)
    assert e["standardized_residual_rms"] < 3
    assert not any("MODEL MISMATCH" in w for w in analyze(inv)["warnings"])


def test_uniform_posterior_is_an_unresolved_map_set():
    from upwind.validation.cases import make_case
    from upwind.validation.science import location_metrics

    inv, truth = make_case("ambiguous", 110000)
    # Preserve the original discrete-model regression. Its scenario IDs are not
    # geographic regions in the replacement area-weighted model.
    from upwind.legacy import ensemble as legacy_ensemble

    e = legacy_ensemble(inv)
    m = location_metrics(
        e["location_weights"], inv.source_locations, truth, e["projection"]
    )
    assert not m["map_unique"] and m["map_tie_count"] == 9
    assert m["map_max_error_m"] > m["map_min_error_m"]


def test_unobserved_plume_retains_area_prior_and_background_ambiguity():
    from upwind.validation.cases import make_case

    inv, _ = make_case("ambiguous", 110000)
    e = ensemble(inv)
    area = np.prod(e["cells_xy"][:, 2:] - e["cells_xy"][:, :2], axis=1)
    assert np.allclose(e["cell_weights"], area / area.sum())
    assert e["source_probability"] == pytest.approx(0.5)
    assert analyze(inv)["evidence_status"] == "ambiguous"


def test_planner_is_invariant_to_domain_anchor_and_site_order():
    inv, _ = synthetic_case()
    a = analyze(inv)
    inv.sites.reverse()
    inv.source_locations.reverse()
    b = analyze(inv)
    assert set(a["plans"][0]["site_ids"]) == set(b["plans"][0]["site_ids"])
    assert a["plans"][0]["score"] == pytest.approx(b["plans"][0]["score"], abs=1e-12)


def test_json_boolean_and_numeric_strings_are_not_scientific_quantities():
    inv, _ = synthetic_case()
    for value in [True, "12.0"]:
        data = inv.model_dump()
        data["measurements"][0]["pm25_ug_m3"] = value
        with pytest.raises(ValueError):
            Investigation.model_validate(data)
