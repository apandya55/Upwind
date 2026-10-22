"""Deterministic property and independent planning-oracle batteries."""

from itertools import combinations
import math, time
import numpy as np
from pyproj import Geod
from ..engine import analyze
from ..models import Investigation, Site, Settings
from ..numerics import plume, stable_information
from .cases import scalar_plume, point


class Checks:
    def __init__(self):
        self.count = 0
        self.failures = []

    def check(self, name, ok, details=None, count=1):
        self.count += count
        if not bool(ok):
            self.failures.append({"name": name, "details": details})

    def result(self):
        return {
            "checks": self.count,
            "failed_groups": len(self.failures),
            "failures": self.failures,
        }


def numerical_battery(n=10000):
    c = Checks()
    rng = np.random.default_rng(110007)
    source = rng.uniform(-1000, 1000, (n, 2))
    angles = rng.uniform(0, 360, n)
    radians = np.deg2rad(angles)
    flow = np.stack((-np.sin(radians), -np.cos(radians)), axis=1)
    cross = np.stack((-flow[:, 1], flow[:, 0]), axis=1)
    down = rng.uniform(21, 2000, n)
    lateral = rng.uniform(-150, 150, n)
    receptor = source + down[:, None] * flow + lateral[:, None] * cross
    q = np.exp(rng.uniform(0, np.log(12000), n))
    speed = rng.uniform(0.8, 8, n)
    output = plume(receptor, source, q, speed, angles)
    oracle = np.array(
        [
            scalar_plume(p, s, float(a), float(b), float(d))
            for p, s, a, b, d in zip(receptor, source, q, speed, angles)
        ]
    )
    close = np.isclose(output, oracle, rtol=1e-10, atol=1e-12)
    c.check(
        "independent scalar Gaussian oracle",
        close.all(),
        {
            "mismatches": int((~close).sum()),
            "max_absolute_error": float(abs(output - oracle).max()),
        },
        n,
    )
    for name, other, expect in [
        ("emission scaling", plume(receptor, source, q * 2, speed, angles), output * 2),
        (
            "inverse wind-speed scaling",
            plume(receptor, source, q, speed * 2, angles),
            output / 2,
        ),
        (
            "translation",
            plume(receptor + 12345, source + 12345, q, speed, angles),
            output,
        ),
        (
            "crosswind symmetry",
            plume(
                source + down[:, None] * flow - lateral[:, None] * cross,
                source,
                q,
                speed,
                angles,
            ),
            output,
        ),
    ]:
        c.check(name, np.allclose(other, expect, rtol=1e-9, atol=1e-11), count=n)
    phi = 0.73
    rotation = np.array([[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]])
    rotated = plume(
        receptor @ rotation.T, source @ rotation.T, q, speed, angles - np.rad2deg(phi)
    )
    c.check(
        "rotation and meteorological convention",
        np.allclose(rotated, output, rtol=1e-9, atol=1e-11),
        count=n,
    )
    c.check(
        "finite nonnegative predictions",
        np.isfinite(output).all() and (output >= 0).all(),
        count=n,
    )
    for x, expected_positive in [
        (19.99, False),
        (20, True),
        (20.01, True),
        (2999.99, True),
        (3000, True),
        (3000.01, False),
    ]:
        value = float(plume([[x, 0]], [0, 0], 5000, 2, 270)[0])
        c.check(
            "explicit kernel support boundary",
            bool(value > 0) == expected_positive,
            {"downwind_m": x, "prediction": value},
        )
    for receptor_bad, speed_bad, q_bad in [
        ([[1, 2]], 0, 1),
        ([[1, 2]], -1, 1),
        ([[np.nan, 2]], 1, 1),
        ([[1, 2]], 1, -1),
        ([[1, 2, 3]], 1, 1),
        ([[1, 2]], 1, np.inf),
    ]:
        try:
            plume(receptor_bad, [0, 0], q_bad, speed_bad, 270)
            ok = False
        except ValueError:
            ok = True
        c.check("invalid kernel argument refusal", ok)
    from scipy.integrate import quad

    for x in [50, 100, 500, 1000, 2000]:
        sy = 0.08 * x / math.sqrt(1 + 0.0001 * x)
        sz = 0.06 * x / math.sqrt(1 + 0.0015 * x)
        integral = quad(
            lambda y: float(plume([[x, y]], [0, 0], 5000, 2, 270)[0]),
            -10 * sy,
            10 * sy,
            epsabs=1e-10,
        )[0]
        expected = (
            5000
            / (math.sqrt(2 * math.pi) * 2 * sz)
            * (math.exp(-0.5 * (3 / sz) ** 2) + math.exp(-0.5 * (7 / sz) ** 2))
        )
        c.check(
            "crosswind integrated mass convention",
            math.isclose(integral, expected, rel_tol=1e-9),
        )
    for i in range(1000):
        k = int(rng.integers(1, 9))
        a = rng.normal(size=(k, k))
        z = rng.normal(size=(k, k))
        r = a @ a.T + np.eye(k) * 10 ** rng.uniform(-1, 5)
        factor = z * 10 ** rng.uniform(-6, 2)
        b = factor @ factor.T
        score = stable_information(r, b, list(range(k)))
        chol = np.linalg.cholesky(r)
        sv = np.linalg.svd(np.linalg.solve(chol, factor), compute_uv=False)
        expected = float(0.5 * np.log1p(sv * sv).sum())
        c.check(
            "information independent singular-value oracle",
            math.isclose(score, expected, rel_tol=1e-8, abs_tol=1e-10),
            {"seed_index": i, "score": score, "oracle": expected},
        )
    return c.result()


def make_placement(seed, large=False):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(30, 70) if large else rng.integers(2, 9))
    sites = []
    for i in range(int(rng.integers(0, 3))):
        sites.append(
            Site(
                id=f"M{i}",
                name=f"Monitor {i}",
                kind="sensor",
                **point(tuple(rng.uniform(-1000, 1000, 2))),
            )
        )
    for i in range(n):
        permission = rng.random() > 0.1
        sites.append(
            Site(
                id=f"C{i:02}",
                name=f"Candidate {i}",
                allowed=permission,
                power=rng.random() > 0.05,
                access=rng.random() > 0.05,
                cost=float(rng.choice([0, 10, 30, 60, 100, 150])),
                windows=["steady-window"] if rng.random() > 0.05 else [],
                **point(tuple(rng.uniform(-1500, 1500, 2))),
            )
        )
    return Investigation(
        name=f"SYNTHETIC placement {seed}",
        synthetic=True,
        sites=sites,
        settings=Settings(
            objective="spatial_coverage",
            budget=float(rng.integers(0, 501)),
            equipment_limit=int(rng.integers(1, 9) if large else rng.integers(1, 4)),
            seed=seed,
        ),
    )


def placement_oracle(inv):
    permitted = [
        i
        for i, s in enumerate(inv.sites)
        if s.kind == "candidate"
        and s.allowed
        and s.power
        and s.access
        and "steady-window" in s.windows
    ]
    eligible = [i for i in permitted if inv.sites[i].cost <= inv.settings.budget]
    anchors = [i for i, s in enumerate(inv.sites) if s.kind == "sensor"]
    geod = Geod(ellps="WGS84")
    distance = np.array(
        [
            [
                geod.inv(
                    inv.sites[i].longitude,
                    inv.sites[i].latitude,
                    s.longitude,
                    s.latitude,
                )[2]
                for s in inv.sites
            ]
            for i in permitted
        ]
    ).reshape(len(permitted), len(inv.sites))

    def covered(indices):
        return (
            float(np.exp(-distance[:, indices + anchors].min(axis=1) / 400).mean())
            if permitted and indices + anchors
            else 0.0
        )

    base = covered([])

    def utility(indices):
        return covered(indices) - base

    best = 0.0
    for k in range(min(inv.settings.equipment_limit, len(eligible)) + 1):
        for subset in combinations(eligible, k):
            if sum(inv.sites[i].cost for i in subset) <= inv.settings.budget + 1e-9:
                best = max(best, utility(list(subset)))
    return best, utility, eligible


def planning_battery(count=100):
    checks = Checks()
    records = []
    for large in [False, True]:
        for i in range(count):
            seed = 111000 + i + int(large) * 1000
            inv = make_placement(seed, large)
            started = time.perf_counter()
            result = analyze(inv)
            plans = result["plans"]
            bad = []
            for plan in plans:
                selected = [s for s in inv.sites if s.id in plan["site_ids"]]
                ok = (
                    len(selected) == len(set(plan["site_ids"]))
                    and len(selected) <= inv.settings.equipment_limit
                    and sum(s.cost for s in selected) <= inv.settings.budget + 1e-8
                    and all(
                        s.kind == "candidate"
                        and s.allowed
                        and s.power
                        and s.access
                        and "steady-window" in s.windows
                        for s in selected
                    )
                )
                if not ok:
                    bad.append(plan)
                checks.check("all-method feasibility", ok, {"seed": seed, "plan": plan})
            if not large:
                expected, utility, eligible = placement_oracle(inv)
                actual = result["plans"][0]["score"]
                checks.check(
                    "independent exhaustive geographic optimum",
                    abs(expected - actual) < 2e-6,
                    {"seed": seed, "actual": actual, "oracle": expected},
                )
                original_score = actual
                inv.settings.budget += 100
                expanded = analyze(inv)["plans"][0]["score"]
                checks.check(
                    "budget monotonicity with fixed targets",
                    expanded >= original_score - 1e-10,
                    {"seed": seed},
                )
            elif plans:
                checks.check(
                    "heuristic no worse than supplied baseline envelope",
                    plans[0]["score"] >= max(p["score"] for p in plans[1:]) - 1e-10,
                    {"seed": seed, "scores": [p["score"] for p in plans]},
                )
            # Permuting sites must not change utility or chosen set, apart from
            # mathematically tied exact optima; all choices use canonical IDs.
            inv.sites = list(reversed(inv.sites))
            shuffled = analyze(inv)
            compare = expanded if not large else result["plans"][0]["score"]
            checks.check(
                "site permutation invariance",
                abs(shuffled["plans"][0]["score"] - compare) < 1e-9,
                {"seed": seed},
            )
            records.append(
                {
                    "seed": seed,
                    "large": large,
                    "sites": len(inv.sites),
                    "status": result["status"],
                    "exact_search": result.get("exact_search"),
                    "best_score": plans[0]["score"],
                    "baseline_scores": [p["score"] for p in plans[1:]],
                    "wall_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )
    return checks.result() | {"instances": records}


def capability_battery():
    from ..fixtures import synthetic_case
    from .cases import point

    checks = Checks()
    records = []
    names = [
        "empty_sites",
        "no_sources",
        "duplicate_sources",
        "hidden_calm",
        "hidden_variable",
        "missing_weather",
        "remote_weather",
        "conflicting_weather",
        "near_source",
        "far_observation",
        "far_candidates",
        "no_permission",
        "zero_budget",
        "free_site",
        "zero_information",
        "wind_lower_boundary",
        "wind_upper_boundary",
        "wind_below",
        "wind_above",
        "uncertainty_lower",
        "uncertainty_upper",
        "full_window_duration",
        "too_many_sensors",
    ]
    for name in names:
        inv, _ = synthetic_case()
        expected = "insufficient_data"
        if name == "empty_sites":
            inv.sites = []
            expected = "infeasible"
        elif name == "no_sources":
            inv.source_locations = []
        elif name == "duplicate_sources":
            inv.source_locations = [inv.source_locations[0]] * 2
        elif name in ["hidden_calm", "hidden_variable"]:
            inv.weather.append(
                inv.weather[0].model_copy(
                    update={
                        "timestamp": "2025-06-12T10:02:00+00:00",
                        **(
                            {"wind_speed_m_s": 0.1}
                            if name == "hidden_calm"
                            else {"wind_from_deg": 180}
                        ),
                    }
                )
            )
        elif name == "missing_weather":
            inv.weather = []
        elif name == "remote_weather":
            for w in inv.weather:
                w.latitude = 40
        elif name == "conflicting_weather":
            inv.weather.append(inv.weather[0].model_copy(update={"wind_from_deg": 90}))
        elif name == "near_source":
            inv.measurements[0].latitude = inv.source_locations[0].latitude
            inv.measurements[0].longitude = inv.source_locations[0].longitude
        elif name == "far_observation":
            inv.measurements[0].latitude = 0.1
        elif name == "far_candidates":
            for site in inv.sites:
                if site.kind == "candidate":
                    site.latitude = 0.1
            expected = "infeasible"
        elif name == "no_permission":
            for site in inv.sites:
                site.allowed = False
            expected = "infeasible"
        elif name == "zero_budget":
            inv.settings.budget = 0
            expected = "infeasible"
        elif name == "free_site":
            inv.settings.budget = 0
            inv.sites[3].cost = 0
            expected = "ok"
        elif name == "zero_information":
            for m in inv.measurements:
                m.latitude = point((-1500, 0))["latitude"]
                m.longitude = point((-1500, 0))["longitude"]
            for site in inv.sites:
                p = point((-1500, -300))
                site.latitude = p["latitude"]
                site.longitude = p["longitude"]
            expected = "uninformative"
        elif name.startswith("wind_"):
            speed = {
                "wind_lower_boundary": 0.8,
                "wind_upper_boundary": 8.0,
                "wind_below": 0.79999,
                "wind_above": 8.00001,
            }[name]
            for w in inv.weather:
                w.wind_speed_m_s = speed
            if name in ["wind_lower_boundary", "wind_upper_boundary"]:
                expected = "ok"
        elif name.startswith("uncertainty_"):
            for m in inv.measurements:
                m.uncertainty_ug_m3 = 0.01 if name == "uncertainty_lower" else 1000
            expected = "ok"
        elif name == "full_window_duration":
            inv.measurements.append(
                inv.measurements[0].model_copy(
                    update={"timestamp": "2025-06-13T10:00:00+00:00"}
                )
            )
        elif name == "too_many_sensors":
            inv.measurements = [
                inv.measurements[0].model_copy(update={"sensor_id": f"Alias{i}"})
                for i in range(41)
            ]
        try:
            result = analyze(inv)
            accepted = (
                result["status"] == expected
                or expected == "ok"
                and result["status"] == "uninformative"
            )
            checks.check(
                "capability " + name,
                accepted,
                {
                    "expected": expected,
                    "actual": result["status"],
                    "reason": result.get("reason"),
                },
            )
            finite = all(
                np.isfinite(s["weight"]) for s in result.get("sources", [])
            ) and all(np.isfinite(p["score"]) for p in result.get("plans", []))
            checks.check("finite capability " + name, finite)
            records.append(
                {
                    "case": name,
                    "expected": expected,
                    "status": result["status"],
                    "reason": result.get("reason"),
                    "passed": accepted and finite,
                }
            )
        except Exception as e:
            checks.check(
                "capability " + name,
                False,
                {"exception": type(e).__name__, "message": str(e)},
            )
    # Schema maxima are checked without constructing unbounded allocations.
    for field, max_count in [
        ("sites", 100),
        ("source_locations", 25),
        ("measurements", 10000),
        ("weather", 10000),
    ]:
        inv, _ = synthetic_case()
        data = inv.model_dump()
        sample = data[field][0]
        data[field] = [sample] * (max_count + 1)
        try:
            Investigation.model_validate(data)
            refused = False
        except ValueError as exc:
            refused = hasattr(exc, "errors") and any(
                error["type"] == "too_long" and error["loc"] == (field,)
                for error in exc.errors()
            )
        checks.check("schema count limit " + field, refused)
    return checks.result() | {"cases": records}
