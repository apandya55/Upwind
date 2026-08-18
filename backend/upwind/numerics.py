"""Coordinate projections, dispersion equations, and linear algebra utilities."""

from functools import lru_cache
import numpy as np
from pyproj import CRS, Transformer
from scipy.linalg import solve_triangular


@lru_cache(maxsize=128)
def projector(latitude, longitude):
    crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={latitude} +lon_0={longitude} +datum=WGS84 +units=m"
    )
    return Transformer.from_crs("EPSG:4326", crs, always_xy=True)


def flow_vector(wind_from_deg):
    radians = np.deg2rad(wind_from_deg)
    return np.array([-np.sin(radians), -np.cos(radians)])


def plume(
    receptors,
    source,
    strength,
    speed,
    direction,
    release_height=5.0,
    receptor_height=2.0,
):
    """Ground-reflected neutral plume, µg/s -> µg/m³. Broadcasts (...,2).

    Defaults H=5m, z=2m; explicit study heights may be supplied. The kernel returns zero outside its downwind/distance support;
    inference must separately reject unsupported observation/source pairs.
    """
    pts, src = np.asarray(receptors, dtype=float), np.asarray(source, dtype=float)
    if pts.size == 0 and pts.ndim == 1:
        pts = pts.reshape(0, 2)
    if pts.ndim < 2 or pts.shape[-1] != 2 or src.ndim < 1 or src.shape[-1] != 2:
        raise ValueError("Receptors and sources require final coordinate dimension 2")
    q, u, angle = (np.asarray(x, dtype=float) for x in (strength, speed, direction))
    if not all(np.isfinite(x).all() for x in (pts, src, q, u, angle)):
        raise ValueError("Plume inputs must be finite")
    if np.any(u <= 0) or np.any(q < 0):
        raise ValueError("Plume speed must be positive and strength nonnegative")
    height, z = (np.asarray(v, dtype=float) for v in (release_height, receptor_height))
    if (
        not np.isfinite(height).all()
        or not np.isfinite(z).all()
        or np.any(height < 0)
        or np.any(z < 0)
    ):
        raise ValueError("Release and receptor heights must be finite and nonnegative")
    try:
        with np.errstate(over="raise", divide="raise", invalid="raise", under="ignore"):
            delta = pts - src
            theta = np.deg2rad(np.remainder(angle, 360))
            fx, fy = -np.sin(theta), -np.cos(theta)
            down = delta[..., 0] * fx + delta[..., 1] * fy
            cross = delta[..., 0] * (-fy) + delta[..., 1] * fx
            x = np.maximum(down, 20)
            sy, sz = (
                0.08 * x / np.sqrt(1 + 0.0001 * x),
                0.06 * x / np.sqrt(1 + 0.0015 * x),
            )
            vertical = np.exp(-0.5 * ((z - height) / sz) ** 2) + np.exp(
                -0.5 * ((z + height) / sz) ** 2
            )
            transverse = np.exp(-0.5 * np.minimum(np.abs(cross) / sy, 40) ** 2)
            c = q / (2 * np.pi * u * sy * sz) * transverse * vertical
            out = np.where(
                (down >= 20) & (np.hypot(delta[..., 0], delta[..., 1]) <= 3000), c, 0.0
            )
    except (FloatingPointError, OverflowError) as e:
        raise ValueError("Plume inputs exceed supported floating-point range") from e
    if not np.isfinite(out).all():
        raise ValueError("Non-finite plume prediction")
    return out


def stable_information(r, b, indices):
    """0.5 log det(I+R^-1/2 B R^-T/2), avoiding subtractive logdet loss."""
    if not indices:
        return 0.0
    ix = np.ix_(indices, indices)
    chol = np.linalg.cholesky(r[ix])
    left = solve_triangular(chol, b[ix], lower=True, check_finite=False)
    whitened = solve_triangular(chol, left.T, lower=True, check_finite=False).T
    whitened = (whitened + whitened.T) * 0.5
    eigen = np.linalg.eigvalsh(whitened)
    tolerance = 1e-9 * max(1.0, float(np.max(np.abs(eigen))))
    if eigen.min() < -tolerance:
        raise ValueError("Information covariance is not positive semidefinite")
    return float(0.5 * np.log1p(np.maximum(eigen, 0)).sum())
