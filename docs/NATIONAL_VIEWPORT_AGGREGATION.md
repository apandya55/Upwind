# National Explorer viewport aggregation

The Explorer requests only the active evidence layer through `GET /api/national/viewport`. The API applies the active year and pollutant filters before building map dots. Place estimates, measured monitor records, and emissions inventory records are queried separately; the endpoint never combines their values.

Records are assigned to global Web Mercator cells, so their identities remain stable during small pans. The server starts from a zoom-dependent grid and coarsens deterministically if occupied cells exceed the 3,000-dot rendering ceiling. It never samples rows or fills a visual quota. Each aggregate dot is anchored to a real coordinate from one of its represented records; it is never placed at an invented cell centroid. Coincident locations stay together and can be inspected through the paged member endpoint. `member_count` sums to `represented_records`, and `symbol_count` is the number of returned map dots. A viewport may therefore contain fewer than 2,900 dots when the source geometry does not support that many stable representatives.

Viewport inclusion uses inclusive longitude and latitude bounds against source row WGS84 coordinates. Cell IDs include the release filename, grid level, and integer cell coordinates. The response reports the requested zoom, selected aggregation level, exact viewport and filters, dataset identity, aggregation version, symbol count, and represented-record count. Counts describe represented source records, not people reached or geographic population coverage.

The active layer alone is requested. Map movement is queried after `moveend` and a 100 ms debounce. New requests abort the previous request, and late responses cannot replace newer data. Existing dots stay visible while the next result loads. The map instance and native GeoJSON layers remain mounted across filter changes.

Use separate `/api/national/places`, `/monitors`, or `/sources` requests for search, detail, or export workflows. Those endpoints retain their own pagination behavior and do not define map completeness.

The map includes a simplified Natural Earth country boundary layer for coverage context. Only the United States has a published release in this build; other countries are shaded gray and contain no inferred values. Extending coverage requires a separately audited national monitoring and geography pipeline with compatible units, years, provenance, and evaluation; the boundary layer does not imply that those countries are supported.
