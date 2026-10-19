"""Independent integration and conditioning checks, without localization truth.

The observation values here are arbitrary contract inputs. No simulated source
location is used as a success criterion. The oracle integrates positive release
strength numerically instead of using the production truncation identities.
"""

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import multivariate_normal, truncnorm

from upwind.inference import (
    CONFIG,
    fit,
    positive_normal_moments,
    region,
    source_cells,
)
from upwind.models import Assumptions, Investigation, Measurement, Point, Settings, Weather
from upwind.numerics import projector


START = datetime(2026, 2, 1, tzinfo=timezone.utc)


def point_at(x, y):
    longitude, latitude = projector(0, 0).transform(x, y, direction="INVERSE")
    return {"latitude": latitude, "longitude": longitude}


def small_study():
    readings = [
        ("A", 0, 60, 0, 13.2, 0.7),
        ("A", 120, 60, 0, 15.7, 1.1),
        ("B", 240, 160, 45, 9.4, 0.9),
    ]
    return Investigation(
        source_locations=[Point(**point_at(-300, 0)), Point(**point_at(-180, 0))],
        assumptions=Assumptions(steady=True, open_terrain=True, local_weather=True),
        settings=Settings(noise_ug_m3=0.8),
        measurements=[
            Measurement(
                sensor_id=sensor,
                timestamp=(START + timedelta(seconds=seconds)).isoformat(),
                pm25_ug_m3=value,
                uncertainty_ug_m3=uncertainty,
                **point_at(x, y),
            )
            for sensor, seconds, x, y, value, uncertainty in readings
        ],
        weather=[
            Weather(
                timestamp=(START + timedelta(seconds=120)).isoformat(),
                wind_speed_m_s=2,
                wind_from_deg=270,
                **point_at(0, 0),
            )
        ],
    )


def projected_points(projection, points):
    return np.asarray(
        [projection.transform(point.longitude, point.latitude) for point in points]
    )


def covariance_oracle(x, times, ids, z, other_times, other_ids, noise):
    """Declared covariance evaluated independently with scalar pair loops."""
    answer = np.empty((len(x), len(z)))
    for i, (location, time, sensor) in enumerate(zip(x, times, ids)):
        for j, (other, other_time, other_sensor) in enumerate(
            zip(z, other_times, other_ids)
        ):
            answer[i, j] = (
                noise**2
                * np.exp(
                    -np.linalg.norm(location - other) / CONFIG["spatial_scale_m"]
                    - abs(time - other_time) / CONFIG["temporal_scale_s"]
                )
                + CONFIG["instrument_bias_sd_ug_m3"] ** 2 * (sensor == other_sensor)
                + CONFIG["background_sd_ug_m3"] ** 2
                + CONFIG["background_trend_sd_ug_m3_hour"] ** 2
                * time
                * other_time
                / 3600**2
            )
    return answer


def unit_plume_oracle(receptors, source, speed, direction=270):
    """Direct scalar equation, independent of the vectorized kernel."""
    answer = []
    for receptor in receptors:
        dx, dy = receptor - source
        radians = np.deg2rad(direction)
        downwind = -dx * np.sin(radians) - dy * np.cos(radians)
        crosswind = dx * np.cos(radians) - dy * np.sin(radians)
        if downwind < 20 or np.linalg.norm(receptor - source) > 3000:
            answer.append(0.0)
            continue
        horizontal = 0.08 * downwind / np.sqrt(1 + 0.0001 * downwind)
        vertical = 0.06 * downwind / np.sqrt(1 + 0.0015 * downwind)
        answer.append(
            np.exp(-0.5 * (crosswind / horizontal) ** 2)
            * (
                np.exp(-0.5 * (3 / vertical) ** 2)
                + np.exp(-0.5 * (7 / vertical) ** 2)
            )
            / (2 * np.pi * speed * horizontal * vertical)
        )
    return np.array(answer)


def integrated_strength(y, background, covariance, unit_concentration):
    """Integrate q/tau on [0,infinity), including the normalized half-normal."""
    tau = CONFIG["strength_halfnormal_scale_ug_s"]
    log_reference = multivariate_normal.logpdf(
        y, mean=np.full(len(y), background), cov=covariance
    )

    def density(scaled_strength):
        return float(
            np.exp(
                multivariate_normal.logpdf(
                    y,
                    mean=background + tau * scaled_strength * unit_concentration,
                    cov=covariance,
                )
                - log_reference
                + 0.5 * np.log(2 / np.pi)
                - 0.5 * scaled_strength**2
            )
        )

    integrals = [
        quad(
            lambda value: value**power * density(value),
            0,
            np.inf,
            epsabs=1e-16,
            epsrel=2e-11,
            limit=200,
        )[0]
        for power in range(3)
    ]
    # Scale away small absolute likelihoods so quadrature controls relative
    # accuracy even when every hypothesis explains the observations poorly.
    evidence = np.exp(log_reference) * integrals[0]
    mean = tau * integrals[1] / integrals[0]
    variance = tau**2 * (
        integrals[2] / integrals[0] - (integrals[1] / integrals[0]) ** 2
    )
    return evidence, mean, variance


@pytest.mark.parametrize(
    "observed_values",
    [[13.2, 15.7, 9.4], [4.0, 4.0, 4.0], [0.1, 0.2, 35.0]],
)
def test_halfnormal_integrated_evidence_and_predictive_moments_against_quad(
    observed_values,
):
    investigation = small_study()
    for row, value in zip(investigation.measurements, observed_values):
        row.pm25_ug_m3 = value
    fitted = fit(investigation, diagnostics=False, wind_uncertainty=False)
    assert not fitted["continuous"]
    rows = fitted["rows"]
    coordinates = projected_points(fitted["projection"], rows)
    times = np.array([-120.0, 0, 120])
    ids = [row.sensor_id for row in rows]
    values = np.array([row.pm25_ug_m3 for row in rows])
    covariance = covariance_oracle(
        coordinates,
        times,
        ids,
        coordinates,
        times,
        ids,
        investigation.settings.noise_ug_m3,
    ) + np.diag([row.uncertainty_ug_m3**2 for row in rows])
    background = CONFIG["background_mean_ug_m3"]
    background_evidence = multivariate_normal.pdf(
        values, mean=np.full(len(values), background), cov=covariance
    )

    targets = [Point(**point_at(125, -15)), Point(**point_at(250, 60))]
    target_coordinates = projected_points(fitted["projection"], targets)
    target_times = np.array([-60.0, 60])
    target_ids = ["A", "new-C"]
    target_uncertainties = [0.6, 1.2]
    cross = covariance_oracle(
        target_coordinates,
        target_times,
        target_ids,
        coordinates,
        times,
        ids,
        investigation.settings.noise_ug_m3,
    )
    future_covariance = covariance_oracle(
        target_coordinates,
        target_times,
        target_ids,
        target_coordinates,
        target_times,
        target_ids,
        investigation.settings.noise_ug_m3,
    ) + np.diag(np.square(target_uncertainties))
    conditional_covariance = future_covariance - cross @ np.linalg.solve(
        covariance, cross.T
    )
    conditional_background = background + cross @ np.linalg.solve(
        covariance, values - background
    )
    target_stamps = [
        (START + timedelta(seconds=seconds)).isoformat() for seconds in [60, 180]
    ]
    means, covariances = fitted["predictive"](
        targets,
        target_stamps,
        target_ids,
        uncertainties=target_uncertainties,
    )
    np.testing.assert_allclose(means[0], conditional_background, rtol=2e-11)
    np.testing.assert_allclose(covariances[0], conditional_covariance, atol=3e-11)

    evidence = [background_evidence * (1 - CONFIG["source_prior"])]
    component = 1
    for source in fitted["source_xy"]:
        for scale, weather_prior in zip(CONFIG["speed_scales"], CONFIG["speed_prior"]):
            response = unit_plume_oracle(coordinates, source, 2 * scale)
            integrated, q_mean, q_variance = integrated_strength(
                values, background, covariance, response
            )
            evidence.append(
                integrated
                * CONFIG["source_prior"]
                / len(fitted["source_xy"])
                * weather_prior
            )
            residual_response = unit_plume_oracle(
                target_coordinates, source, 2 * scale
            ) - cross @ np.linalg.solve(covariance, response)
            np.testing.assert_allclose(
                means[component],
                conditional_background + q_mean * residual_response,
                rtol=3e-10,
                atol=2e-10,
            )
            np.testing.assert_allclose(
                covariances[component],
                conditional_covariance
                + q_variance * np.outer(residual_response, residual_response),
                rtol=3e-9,
                atol=2e-9,
            )
            assert np.linalg.eigvalsh(covariances[component]).min() > 0
            component += 1
    normalized = np.asarray(evidence) / sum(evidence)
    np.testing.assert_allclose(fitted["weights"], normalized, rtol=3e-10)
    assert fitted["source_probability"] == pytest.approx(
        normalized[1:].sum(), rel=3e-10
    )


def test_weather_marginal_evidence_preserves_normalized_direction_and_speed_priors():
    inv = small_study()
    fitted = fit(inv, diagnostics=False)
    rows = fitted["rows"]
    coordinates = projected_points(fitted["projection"], rows)
    times = np.array([-120.0, 0, 120])
    ids = [row.sensor_id for row in rows]
    covariance = covariance_oracle(
        coordinates, times, ids, coordinates, times, ids, inv.settings.noise_ug_m3
    ) + np.diag([row.uncertainty_ug_m3**2 for row in rows])
    values = np.array([row.pm25_ug_m3 for row in rows])
    background = CONFIG["background_mean_ug_m3"]
    mass = [
        (1 - CONFIG["source_prior"])
        * multivariate_normal.pdf(
            values, mean=np.full(len(values), background), cov=covariance
        )
    ]
    offsets = np.asarray(CONFIG["wind_offsets_deg"])
    offset_prior = np.exp(-0.5 * (offsets / CONFIG["wind_offset_sd_deg"]) ** 2)
    offset_prior /= offset_prior.sum()
    for source in fitted["source_xy"]:
        for offset, angle_prior in zip(offsets, offset_prior):
            for scale, speed_prior in zip(CONFIG["speed_scales"], CONFIG["speed_prior"]):
                response = unit_plume_oracle(coordinates, source, 2 * scale, 270 + offset)
                evidence, _, _ = integrated_strength(values, background, covariance, response)
                mass.append(
                    evidence
                    * CONFIG["source_prior"]
                    / len(fitted["source_xy"])
                    * angle_prior
                    * speed_prior
                )
    weights = np.asarray(mass) / sum(mass)
    np.testing.assert_allclose(fitted["weights"], weights, rtol=4e-10, atol=1e-13)
    assert fitted["source_probability"] == pytest.approx(weights[1:].sum(), rel=4e-10)


@pytest.mark.parametrize("z", [-20, -10, -3, 0, 3, 20])
def test_positive_strength_moments_against_scipy_truncnorm(z):
    sd = 7.3
    actual_mean, actual_variance = positive_normal_moments(
        np.array([z * sd]), np.array([sd])
    )
    mean, variance = truncnorm.stats(-z, np.inf, loc=z * sd, scale=sd, moments="mv")
    assert actual_mean[0] == pytest.approx(mean, rel=1e-9)
    assert actual_variance[0] == pytest.approx(variance, rel=1e-8)


@pytest.mark.parametrize("negative_z", [20.01, 21, 40, 100, 1000])
def test_positive_strength_far_tail_moments_against_rescaled_integral(negative_z):
    # Integrating u=(-z)*q/sd avoids exponentially tiny tail probabilities and
    # cancellation in the reference truncnorm variance at z=-1000.
    scale = 11.2
    integrals = [
        quad(
            lambda u: u**power * np.exp(-u - u**2 / (2 * negative_z**2)),
            0,
            np.inf,
            epsabs=1e-13,
            epsrel=1e-12,
        )[0]
        for power in range(3)
    ]
    expected_mean = scale / negative_z * integrals[1] / integrals[0]
    expected_variance = (scale / negative_z) ** 2 * (
        integrals[2] / integrals[0] - (integrals[1] / integrals[0]) ** 2
    )
    mean, variance = positive_normal_moments(
        np.array([-negative_z * scale]), np.array([scale])
    )
    assert mean[0] == pytest.approx(expected_mean, rel=1e-6)
    assert variance[0] == pytest.approx(expected_variance, rel=1e-6)
    assert mean[0] > 0 and variance[0] > 0


def test_positive_strength_moments_accept_scalar_and_broadcast_scale():
    mean, variance = positive_normal_moments(-3.0, 2.0)
    oracle_mean, oracle_variance = truncnorm.stats(1.5, np.inf, loc=-3, scale=2, moments="mv")
    assert mean == pytest.approx(oracle_mean)
    assert variance == pytest.approx(oracle_variance)
    means, variances = positive_normal_moments(np.array([-100.0, 3.0]), 2.0)
    assert means.shape == variances.shape == (2,)
    assert np.all(means > 0) and np.all(variances > 0)


def test_continuous_cells_partition_domain_area_and_region_has_actual_geometry():
    anchors = np.array([[-57.0, -23], [48, 62], [-30, 30]])
    centers, cells, prior, continuous = source_cells(anchors)
    assert continuous
    areas = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    expected_area = (48 + 57) * (62 + 23)
    assert areas.sum() == pytest.approx(expected_area)
    np.testing.assert_allclose(prior, areas / expected_area)
    np.testing.assert_allclose(centers, (cells[:, :2] + cells[:, 2:]) / 2)
    # Every interior quadrature point belongs to precisely one rectangular cell.
    membership = (
        (centers[:, None] > cells[None, :, :2])
        & (centers[:, None] < cells[None, :, 2:])
    ).all(axis=2)
    assert np.all(membership.sum(axis=1) == 1)
    weights = np.full(len(cells), 0.05 / (len(cells) - 1))
    index = len(cells) // 2
    weights[index] = 0.95
    projection = projector(0, 0)
    actual = region(
        {
            "cell_weights": weights,
            "cells_xy": cells,
            "continuous": True,
            "projection": projection,
            "excluded_domain_area_m2": 0,
        }
    )
    assert actual["area_m2"] == pytest.approx(areas[index])
    assert actual["domain_area_m2"] == pytest.approx(expected_area)
    assert len(actual["cells"]) == 1
    polygon = actual["cells"][0]["polygon"]
    projected_polygon = np.asarray(
        [projection.transform(p["longitude"], p["latitude"]) for p in polygon]
    )
    x0, y0, x1, y1 = cells[index]
    np.testing.assert_allclose(
        projected_polygon, [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], atol=1e-7
    )
    # A geographic point midway through the chosen cell is inside the region;
    # an adjacent cell's center is outside, irrespective of nearest anchor.
    center = centers[index]
    assert np.all(center > projected_polygon.min(axis=0))
    assert np.all(center < projected_polygon.max(axis=0))
    other = centers[(index + 1) % len(cells)]
    assert np.any(other < projected_polygon.min(axis=0)) or np.any(
        other > projected_polygon.max(axis=0)
    )


def test_degenerate_domain_retains_discrete_points_without_inventing_area():
    anchors = np.array([[-300.0, 0], [-180, 0]])
    points, cells, prior, continuous = source_cells(anchors)
    assert not continuous
    np.testing.assert_array_equal(points, anchors)
    np.testing.assert_array_equal(cells[:, :2], cells[:, 2:])
    np.testing.assert_allclose(prior, [0.5, 0.5])


def repeated_sensor_study(count, *, independent_instruments=False):
    inv = small_study()
    inv.settings.noise_ug_m3 = 0.5
    inv.measurements = [
        Measurement(
            sensor_id=f"S{location}-{index}" if independent_instruments else f"S{location}",
            timestamp=(START + timedelta(microseconds=index)).isoformat(),
            pm25_ug_m3=13,
            uncertainty_ug_m3=0.01,
            **point_at(100, 50 * location),
        )
        for location in range(2)
        for index in range(count)
    ]
    inv.weather = [inv.weather[0].model_copy(update={"timestamp": START.isoformat()})]
    return inv


def test_repeated_same_instrument_rows_do_not_erase_shared_bias_uncertainty():
    target = [Point(**point_at(1400, 600))]
    variances = []
    for count, independent in [(1, False), (24, False), (24, True)]:
        fitted = fit(
            repeated_sensor_study(count, independent_instruments=independent),
            diagnostics=False,
            background_only=True,
            wind_uncertainty=False,
        )
        _, predictive_covariance = fitted["predictive"](
            target, [START.isoformat()], ["future-instrument"], uncertainties=[0.5]
        )
        assert fitted["source_probability"] == 0
        variances.append(predictive_covariance[0, 0, 0])
    # A 24-fold increase in the same instruments' rows leaves the common bias
    # uncertainty intact. Forty-eight genuinely independent biases reduce it.
    assert variances[1] >= 0.99 * variances[0]
    assert variances[1] - variances[2] > 0.3
    assert min(variances) > 1 + 0.5**2  # Future bias and measurement error remain.
