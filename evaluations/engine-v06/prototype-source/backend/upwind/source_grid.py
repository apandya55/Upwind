"""Area-preserving refinement and decision summaries; no evaluator inputs."""

import numpy as np


def subdivide(cells, mass, *, target=0.9, limit=96):
    """Split selected parents in four, retaining every other parent exactly.

    Selection is by density, important for unequal-area subsequent refinements.
    The prior remains uniform in area, never uniform in the resulting cells.
    """
    cells, mass = np.asarray(cells, float), np.asarray(mass, float)
    area = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    if np.any(area <= 0) or not np.isfinite(mass).all() or np.any(mass < 0):
        raise ValueError("Positive-area cells and finite nonnegative mass required")
    density = mass / area
    order = np.argsort(-density, kind="stable")
    count = min(limit, int(np.searchsorted(np.cumsum(mass[order]), target)) + 1)
    chosen = set(order[:count])
    result = []
    for i, (x0, y0, x1, y1) in enumerate(cells):
        if i not in chosen:
            result.append((x0, y0, x1, y1))
            continue
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        result.extend(((x0, y0, xm, ym), (x0, ym, xm, y1),
                       (xm, y0, x1, ym), (xm, ym, x1, y1)))
    return np.asarray(result), count


def location_summary(points, weights, cells, cell_mass, bounds, projection, *, edge_fraction=0.1, edge_limit=0.5):
    """Conditional point decisions and spread, using all integration nodes.

    The posterior mean minimizes squared distance loss under this finite model;
    a density mode is separately reported. Neither is a measured source.
    """
    weights = np.asarray(weights, float)
    mean = weights @ points
    dev = points - mean
    covariance = (dev.T * weights) @ dev
    area = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    density = np.divide(cell_mass, area, out=cell_mass.copy(), where=area > 0)
    mode = (cells[density.argmax(), :2] + cells[density.argmax(), 2:]) / 2
    low, high = bounds
    span = high - low
    # Node integration estimates mass in a fixed geographic strip; cell splitting
    # cannot manufacture an additional boundary or shrink the strip itself.
    edge = np.any((points - low <= edge_fraction * span) | (high - points <= edge_fraction * span), axis=1)
    edge_mass = float(weights @ edge)

    def geographic(p):
        lon, lat = projection.transform(*p, direction="INVERSE")
        return {"latitude": float(lat), "longitude": float(lon)}

    return {
        "posterior_mean": geographic(mean),
        "density_mode": geographic(mode),
        "spatial_rms_m": float(np.sqrt(np.trace(covariance))),
        "covariance_east_north_m2": covariance.tolist(),
        "edge_mass": edge_mass,
        "domain_limited": bool(np.all(span >= 1) and edge_mass >= edge_limit),
        "meaning": "Conditional single-source decisions, not measured locations. Mean minimizes squared position loss under the model; density mode is distinct. Spatial RMS is model spread, not field accuracy. Edge mass is in the outer 10% strip of the declared rectangle; it cannot verify domain completeness.",
    }
