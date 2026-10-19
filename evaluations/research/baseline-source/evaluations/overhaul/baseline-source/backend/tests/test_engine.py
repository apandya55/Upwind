from itertools import combinations
import numpy as np
import pytest
from upwind.engine import (
    analyze,
    plume,
    flow_vector,
    projector,
    ensemble,
    information_matrices,
    eligible_indices,
)
from upwind.fixtures import synthetic_case
from upwind.models import Investigation


def test_wind_convention_projection_and_units():
    assert np.allclose(flow_vector(270), [1, 0], atol=1e-10)
    assert np.allclose(flow_vector(0), [0, -1], atol=1e-10)
    tr = projector(40, -75)
    x, y = tr.transform(-74.999, 40)
    assert 80 < x < 90 and abs(y) < 0.01
    east = plume([[200, 0], [-200, 0], [200, 100]], [0, 0], 5000, 2, 270)
    assert east[0] > 0 and east[1] == 0 and east[2] < east[0]
    assert np.allclose(plume([[200, 0]], [0, 0], 10000, 2, 270), 2 * east[:1])
    assert np.allclose(plume([[200, 0]], [0, 0], 5000, 4, 270), east[:1] / 2)
    # Independent direct equation at x=200, ground reflection, z=2m, H=5m.
    sy = 0.08 * 200 / np.sqrt(1 + 0.0001 * 200)
    sz = 0.06 * 200 / np.sqrt(1 + 0.0015 * 200)
    expected = (
        5000
        / (2 * np.pi * 2 * sy * sz)
        * (np.exp(-0.5 * (3 / sz) ** 2) + np.exp(-0.5 * (7 / sz) ** 2))
    )
    assert east[0] == pytest.approx(expected)


def test_exact_optimum_and_baseline_feasibility():
    inv, _ = synthetic_case()
    inv.settings.budget = 260
    out = analyze(inv)
    assert out["status"] == "ok"
    for plan in out["plans"]:
        assert plan["cost"] <= 260 and len(plan["site_ids"]) <= 2
        for id in plan["site_ids"]:
            site = next(s for s in inv.sites if s.id == id)
            assert (
                site.allowed
                and site.power
                and site.access
                and "steady-window" in site.windows
            )
    e = ensemble(inv)
    r, b = information_matrices(e, inv.settings.noise_ug_m3)
    indices = eligible_indices(inv)
    scores = [0.0]
    for k in [1, 2]:
        for subset in combinations(indices, k):
            if sum(inv.sites[i].cost for i in subset) <= 260:
                ix = np.ix_(subset, subset)
                scores.append(
                    0.5
                    * (np.linalg.slogdet((r + b)[ix])[1] - np.linalg.slogdet(r[ix])[1])
                )
    assert out["plans"][0]["score"] == pytest.approx(max(scores))
    assert out["plans"][0]["score"] >= max(p["score"] for p in out["plans"]) - 1e-10


def test_budget_and_permission_actually_change_plan():
    inv, _ = synthetic_case()
    a = analyze(inv)
    ids = a["plans"][0]["site_ids"]
    inv.sites = [
        s.model_copy(update={"allowed": False}) if s.id in ids else s for s in inv.sites
    ]
    b = analyze(inv)
    assert not set(ids).intersection(b["plans"][0]["site_ids"])
    inv.settings.budget = 0
    c = analyze(inv)
    assert c["status"] == "infeasible"
    assert all(not p["site_ids"] for p in c["plans"])


@pytest.mark.parametrize("case", ["calm", "variable_wind", "missing_sensors"])
def test_unsupported_inference_is_refused_but_coverage_available(case):
    inv, _ = synthetic_case(case)
    assert analyze(inv)["status"] == "insufficient_data"
    inv.settings.objective = "spatial_coverage"
    assert analyze(inv)["status"] == "ok"


def test_weather_missing_and_remote_never_fabricated():
    inv, _ = synthetic_case()
    inv.weather = []
    assert "missing" in analyze(inv)["reason"]
    inv.weather = synthetic_case()[0].weather
    for w in inv.weather:
        w.latitude = 30
    assert "30 minutes and 3 km" in analyze(inv)["reason"]


def test_reproducibility_and_redundancy():
    inv, _ = synthetic_case()
    a = analyze(inv)
    assert a == analyze(inv)
    assert a == analyze(Investigation.model_validate_json(inv.model_dump_json()))
    inv.sites.append(inv.sites[3].model_copy(update={"id": "copy"}))
    e = ensemble(inv)
    r, b = information_matrices(e, 2)

    def score(ids):
        ix = np.ix_(ids, ids)
        return 0.5 * (np.linalg.slogdet((r + b)[ix])[1] - np.linalg.slogdet(r[ix])[1])

    single = score([3])
    joint = score([3, len(inv.sites) - 1])
    assert single < joint < 2 * single


def test_duplicate_followups_do_not_amplify_evidence():
    inv, _ = synthetic_case()
    baseline = analyze(inv)
    inv.measurements += inv.measurements
    assert analyze(inv)["sources"] == baseline["sources"]
