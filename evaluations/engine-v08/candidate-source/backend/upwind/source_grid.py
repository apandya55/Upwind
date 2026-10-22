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
        "meaning": "Conditional single-source decisions, not measured locations. Mean minimizes squared position loss under the model; density mode is distinct. A mean can lie between modes or in excluded geography; inspect the region. Spatial RMS is model spread, not field accuracy. Edge mass is in the outer 10% strip of the declared rectangle; it cannot verify domain completeness.",
    }


def posterior_region_structure(cells, mass, *, level=0.9):
    """Describe connected components of a highest-density posterior region.

    Components are geometric summaries of finite cell mass, not physical source
    modes or calibrated confidence sets. Edge-sharing cells are connected;
    point contact alone is not.
    """
    cells, mass = np.asarray(cells, float), np.asarray(mass, float)
    if cells.ndim != 2 or cells.shape[1] != 4 or mass.shape != (len(cells),):
        raise ValueError("Compatible source cells and posterior mass required")
    if not 0 < level < 1 or not np.isfinite(cells).all() or not np.isfinite(mass).all() or np.any(mass < 0):
        raise ValueError("Finite cells, nonnegative posterior mass and a valid level required")
    area = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    if np.any(area <= 0):
        return {"level": float(level), "component_count": 0, "components": [], "meaning": "No area-supported continuous region."}
    density = mass / area
    order = np.argsort(-density, kind="stable")
    count = min(len(mass), int(np.searchsorted(np.cumsum(mass[order]), level)) + 1)
    chosen = order[:count]
    parent = {int(i): int(i) for i in chosen}

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    scale = max(float(np.ptp(cells[:, [0, 2]])), float(np.ptp(cells[:, [1, 3]])), 1.0)
    tol = scale * 1e-10

    def join_edge(first, second):
        # `first` and `second` are opposing sides of the same oriented edge.
        # Sorted interval sweeps handle coarse-to-fine T junctions in O(n log n).
        for key in first.keys() & second.keys():
            left = sorted(first[key], key=lambda row: row[0])
            right = sorted(second[key], key=lambda row: row[0])
            i = j = 0
            while i < len(left) and j < len(right):
                lo = max(left[i][0], right[j][0])
                hi = min(left[i][1], right[j][1])
                if hi - lo > tol:
                    ra, rb = root(left[i][2]), root(right[j][2])
                    if ra != rb:
                        parent[rb] = ra
                left_end, right_end = left[i][1], right[j][1]
                if left_end <= right_end + tol:
                    i += 1
                if right_end <= left_end + tol:
                    j += 1

    def bucket(value):
        return float(value)

    left_x, right_x, bottom_y, top_y = {}, {}, {}, {}
    for i0 in chosen:
        i = int(i0)
        x0, y0, x1, y1 = cells[i]
        left_x.setdefault(bucket(x0), []).append((y0, y1, i))
        right_x.setdefault(bucket(x1), []).append((y0, y1, i))
        bottom_y.setdefault(bucket(y0), []).append((x0, x1, i))
        top_y.setdefault(bucket(y1), []).append((x0, x1, i))
    join_edge(right_x, left_x)
    join_edge(top_y, bottom_y)
    groups = {}
    for i0 in chosen:
        i = int(i0)
        groups.setdefault(root(i), []).append(i)
    summaries = []
    for ids in groups.values():
        ids = np.asarray(ids, int)
        weights = mass[ids]
        centers = (cells[ids, :2] + cells[ids, 2:]) / 2
        center = weights @ centers / weights.sum() if weights.sum() else centers.mean(axis=0)
        summaries.append({
            "posterior_mass": float(weights.sum()),
            "area_m2": float(area[ids].sum()),
            "cell_count": int(len(ids)),
            "centroid_xy_m": [float(center[0]), float(center[1])],
        })
    summaries.sort(key=lambda x: (-x["posterior_mass"], x["centroid_xy_m"]))
    separations = []
    for i, a in enumerate(summaries):
        for b in summaries[i + 1 :]:
            separations.append(float(np.linalg.norm(np.asarray(a["centroid_xy_m"]) - b["centroid_xy_m"])))
    return {
        "level": float(level),
        "selected_region_mass": float(mass[chosen].sum()),
        "component_count": len(summaries),
        "components": summaries,
        "minimum_component_centroid_separation_m": min(separations) if separations else None,
        "meaning": "Connected components of the finite highest-density region; geometric structure is not a calibrated confidence set or proof of distinct physical sources.",
    }
