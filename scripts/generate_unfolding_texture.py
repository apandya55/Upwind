"""Generate high-fidelity illustrative map texture panels for UPWIND's unfolding atlas.
Creates continuous, cartographically refined panels with landmasses, states,
cities, graticules, bathymetry, and compass details.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend/public/landing/unfolding-map"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 2048, 1024

# Base parchment ocean with subtle warmth
img = Image.new("RGB", (W, H), "#c8dce2")
d = ImageDraw.Draw(img)

# Try system fonts with fallback
try:
    font_lg = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
    font_md = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 17)
    font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    font_serif = ImageFont.truetype("/System/Library/Fonts/Georgia.ttf", 22)
except OSError:
    try:
        font_lg = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 26)
        font_md = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 17)
        font_sm = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
        font_serif = font_lg
    except OSError:
        font_lg = font_md = font_sm = font_serif = None

def project(lon: float, lat: float) -> tuple[int, int]:
    x = int((lon + 170) / 120 * W)
    y = int((55 - lat) / 40 * H)
    return x, y

def draw_geom(geom, fill, outline, width=1):
    if not geom:
        return
    typ = geom.get("type")
    coords = geom.get("coordinates", [])
    if typ == "Polygon":
        for ring in coords:
            pts = [project(float(lon), float(lat)) for lon, lat in ring]
            if len(pts) >= 3:
                d.polygon(pts, fill=fill, outline=outline)
    elif typ == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                pts = [project(float(lon), float(lat)) for lon, lat in ring]
                if len(pts) >= 3:
                    d.polygon(pts, fill=fill, outline=outline)

# 1. Bathymetric shoreline halos (depth contours around coastlines)
geo_path = ROOT / "frontend/public/countries.geojson"
if geo_path.exists():
    geo = json.loads(geo_path.read_text())
    # Outer shallow water tint
    for feature in geo.get("features", []):
        draw_geom(feature.get("geometry"), fill="#b8d2d9", outline="#9cb9c2", width=2)
    # Inner land tint
    for feature in geo.get("features", []):
        props = feature.get("properties") or {}
        iso = str(props.get("iso_a2") or "")
        is_us = (iso == "US")
        land_fill = "#ece5d5" if is_us else "#d6deda"
        land_outline = "#56717a" if is_us else "#788f95"
        draw_geom(feature.get("geometry"), fill=land_fill, outline=land_outline)

# 2. Graticules / Coordinate Grid
for lon in range(-160, -45, 10):
    x1, _ = project(lon, 55)
    x2, _ = project(lon, 15)
    d.line((x1, 0, x2, H), fill="#9bbdc7", width=1)
    if font_sm:
        d.text((x1 + 4, H - 24), f"{abs(lon)}°W", fill="#5a7781", font=font_sm)

for lat in range(20, 56, 5):
    _, y = project(-170, lat)
    d.line((0, y, W, y), fill="#9bbdc7", width=1)
    if font_sm:
        d.text((12, y + 4), f"{lat}°N", fill="#5a7781", font=font_sm)

# 3. Atmospheric wind stream trajectories (prevailing westerlies)
wind_paths = [
    [(-124, 46), (-110, 44), (-95, 43), (-80, 42), (-70, 43)],
    [(-122, 38), (-108, 39), (-92, 38), (-78, 37), (-68, 38)],
    [(-118, 33), (-104, 34), (-88, 33), (-76, 34), (-66, 35)],
]
for path in wind_paths:
    pts = [project(lon, lat) for lon, lat in path]
    for k in range(len(pts) - 1):
        d.line((pts[k][0], pts[k][1], pts[k+1][0], pts[k+1][1]), fill="#6a9bb0", width=1)

# 4. Prominent Cities & Anchor Points
places = [
    (-122.3, 47.6, "Seattle"),
    (-122.4, 37.8, "San Francisco"),
    (-118.2, 34.0, "Los Angeles"),
    (-104.9, 39.7, "Denver"),
    (-95.3, 29.7, "Houston"),
    (-87.6, 41.8, "Chicago"),
    (-84.3, 33.7, "Atlanta"),
    (-78.8, 35.9, "Durham"),
    (-74.0, 40.7, "New York"),
    (-71.0, 42.3, "Boston"),
]
for lon, lat, name in places:
    px, py = project(lon, lat)
    # Target reticle dot
    is_durham = (name == "Durham")
    dot_color = "#b83a25" if is_durham else "#2d4b52"
    dot_radius = 5 if is_durham else 3
    d.ellipse((px - dot_radius, py - dot_radius, px + dot_radius, py + dot_radius), fill=dot_color, outline="#ffffff", width=1)
    if is_durham:
        d.ellipse((px - 9, py - 9, px + 9, py + 9), outline="#b83a25", width=1)
    if font_sm:
        offset_y = -18 if is_durham else 5
        d.text((px + 7, py + offset_y), name.upper(), fill="#1a353c" if is_durham else "#39525a", font=font_sm)

# 5. Geographic Labels
ocean_labels = [(-135, 36, "PACIFIC OCEAN"), (-64, 32, "ATLANTIC OCEAN"), (-90, 24, "GULF OF MEXICO")]
for lon, lat, lbl in ocean_labels:
    ox, oy = project(lon, lat)
    if font_md:
        d.text((ox, oy), lbl, fill="#4f717c", font=font_md)

# 6. Map Cartouche / Legend Box (Upper Left in Panel 0)
d.rectangle((36, 36, 476, 148), fill="#fdfbf5", outline="#7a979c", width=2)
d.rectangle((40, 40, 472, 144), outline="#a8c1c5", width=1)
if font_serif:
    d.text((58, 52), "UPWIND AIR ATLAS", fill="#133330", font=font_serif)
if font_md:
    d.text((58, 84), "CONTINENTAL PM2.5 EVIDENCE · 2024", fill="#3b5a57", font=font_md)
if font_sm:
    d.text((58, 114), "10-FOLD SPATIAL CALIBRATION · 31,523 PLACES", fill="#627b78", font=font_sm)

# 7. Compass Rose in Atlantic (Panel 3)
cx, cy = project(-60, 44)
d.ellipse((cx - 32, cy - 32, cx + 32, cy + 32), outline="#658892", width=1)
d.polygon([(cx, cy - 36), (cx + 7, cy), (cx, cy + 12), (cx - 7, cy)], fill="#1a3f47")
d.polygon([(cx, cy + 36), (cx + 7, cy), (cx, cy - 12), (cx - 7, cy)], fill="#85a4ad")
d.polygon([(cx - 36, cy), (cx, cy - 7), (cx + 12, cy), (cx, cy + 7)], fill="#4e727c")
d.polygon([(cx + 36, cy), (cx, cy - 7), (cx - 12, cy), (cx, cy + 7)], fill="#4e727c")
if font_sm:
    d.text((cx - 5, cy - 54), "N", fill="#1a3f47", font=font_sm)

# Save master map texture
img.save(OUT / "map-texture.png", optimize=True)

# Save the 4 split panels for the accordion
for i in range(4):
    panel = img.crop((i * W // 4, 0, (i + 1) * W // 4, H))
    panel.save(OUT / f"panel-{i}.png", optimize=True)

print("Generated refined cartographic textures in", OUT)
