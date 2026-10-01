# Bounded OSM road context

These raw extracts were retrieved from the OpenStreetMap API on 2026-10-26 UTC
for the Census Gazetteer internal points used by the national place release:

- Durham city, GEOID `3719000`: center `35.977928, -78.898109`; bounding box in
  `raw/durham.metadata.json`.
- Charlotte city, GEOID `3712000`: center `35.209045, -80.830990`; bounding box
  in `raw/charlotte.metadata.json`.

The extracts contain OSM ways and nodes inside roughly a 1.3 km by 1.4 km
rectangle around each point. The analysis uses mapped highway classes
`motorway`, `trunk`, `primary`, and `secondary`, and reports distance and
estimated road length inside a 0.65 km circle. OSM feature timestamps remain
available per way in the raw XML. The API returns an explicit coverage state
outside these two anchors; this is not nationwide road coverage.

Source: [OpenStreetMap contributors](https://www.openstreetmap.org/), via the
[OpenStreetMap API](https://api.openstreetmap.org/api/0.6/map). Data are made
available under the [Open Database License 1.0](https://www.openstreetmap.org/copyright).
Attribution: © OpenStreetMap contributors.

Road proximity and mapped length are geographic context. They do not represent
traffic volume, emissions, ambient concentration, or causal contribution.

EPA ECHO/FRS facilities were not added. The queried EPA ECHO `get_facilities`
call returned only a query summary, its query-results endpoint returned HTTP
500, and the FRS facility lookup tested returned records outside the requested
North Carolina filter. Those paths did not yield a reliable, correctly scoped
geocoded dataset to deduplicate against EPA NEI. Existing NEI evidence remains
available separately through the national release.
