# UPWIND engine code review

This review follows one investigation through the current public path:
`POST /api/analyze` → `engine.analyze()` → quality screening
and UTC-normalized weather matching → `inference.fit()` → finite weather/source
quadrature and positive-strength posterior integration → `region()` and
predictive checks → `identifiability.diagnose_fit()` → evidence status and
planning/report/API serialization. Raw CSV, row origin, instrument text and
weather provenance remain stored separately from inferred results. The old
0.6 source is retained under `evaluations/engine-v06/baseline-source`.

## Findings

| Area and code | Mechanism | Consequence | Evidence | Priority | Disposition |
|---|---|---|---|---|---|
| `models.migrate_analysis()`; `/api/health` | Persisted results were identified by model only, so a protocol change could leave an apparently current result attached. | A changed calculation contract could be displayed without a rerun. | Regression tests create a same-model/old-protocol result and verify archival; health now exposes both identifiers. | High | Fixed. The current result is cleared and archived when either identifier changes. |
| `identifiability._two_source_profile()` | Bounded NNLS can return non-finite coefficients even when the main posterior is finite. | Serializing `NaN` could crash analysis, and treating the failed adequacy check as a pass could create false support. | Locked final row `8310020/sensor_drift` reproduced the crash; post-repair rerun is 256/256 finite. | High | Fixed. Invalid pair fits are counted, diagnostics become unavailable, and `source_supported` is withheld. |
| `importers.utc_timestamp()`; `models.TimedPoint` | Local times require a declared IANA zone and reject ambiguous/nonexistent DST instants; all retained timestamps are normalized to UTC. | Silent timezone shifts can move concentration/weather matches. | Focused importer tests and the model validator cover explicit offsets, DST rejection and UTC output. | High | Fixed and tested. |
| `quality.measurement_quality()`; `weather.matched_weather()` | Sensor-time conflicts and weather duplicate metadata are compared field-by-field; importer row-position markers are ignored only for measurement deduplication. | Import order cannot silently choose humidity, uncertainty, lineage or weather provenance. | Post-release integrity tests cover metadata conflicts and order-independent identical duplicates. | High | Fixed and tested. |
| `numerics.plume()`; `weather.matched_weather()` | Uses a local WGS84 azimuthal-equidistant projection, wind-from converted to a downwind vector, finite positive speed, 20 m near-field and 3 km support. | The calculation is bounded to a neutral short-range Gaussian plume; unsupported calm/variable/strong wind is refused. | Unit/geometry and unsupported-weather tests; explicit warnings remain in results. | High | Implemented operating limit. Physical mismatch outside this scope remains unresolved. |
| `inference.fit()` | Integrates nonnegative release strength, background/trend nuisance terms, persistent weather alternatives, and finite source cells; adaptive subdivision retains area prior for unselected cells. | Posterior weights are conditional on a one-source steady neutral model and finite quadrature, not measured source probabilities. | Implementation record and v0.6/v0.7 source freezes; source-region text states the limitation. | High | Documented limitation; no claim of field accuracy. |
| `predictive_checks.screen()` | Withheld sensors/periods are refit with a joint QMC predictive tail screen and familywise threshold; only a bounded subset is checked. | A passed screen is not an adequacy certificate; unavailable blocks and false negatives remain possible. | Result diagnostics expose checked counts, QMC resolution and unavailable reasons. | Medium | Kept visible and documented. |
| `identifiability._externality_checks()` and bounded pair profile | Tests humidity contrast, temporal structure, nearby residual products, outliers, release variation and a shared-weather two-source alternative. | Structured residuals block resolution but do not identify an emitter, chemistry, instrument fault or source count. | v0.7 final: 86 model-mismatch, 167 ambiguous, 3 conditional support; all two-source worlds remained ambiguous. | High | Implemented as guarded diagnostics; interpretation remains explicitly non-diagnostic. |
| `engine.planning_score()` / `prediction_design.py` | Candidate scoring uses observed-window weather and posterior predictive uncertainty; future weather and instrument learning are not credited. | Plans are conditional design scores, not demonstrated field benefit or future forecasts. | API/report wording and planner metadata state the timestamp and research-only status. | Medium | Documented limitation. Equal-budget planner superiority is not established. |
| `source_grid.region()` / `location_summary()` | A 90% finite mass region is selected by cell density, while posterior mean and density mode are separate summaries. | A mean can lie between modes; a broad region can contain truth while point error is large. | Three accepted v0.7 spatial-background cases cover truth but have roughly 172–197 m posterior-mean error. | High | Documented and surfaced in UI; precision target remains failed. |
| `quality.select_rows()` | When a limit is exceeded, every sensor/group is retained, then endpoints/extrema and seeded temporal strata are selected. | Large campaigns fit a declared bounded subset, not every loaded row; selection can affect inference. | Result includes `rows_loaded`, `rows_input`, exclusions and selection metadata; refusal occurs when groups exceed the limit. | Medium | Operating limit documented; raw rows remain retained. |
| Weather representativeness and model physics | The engine can marginalize declared persistent station bias and use paired reference comparisons, but it cannot infer spatial representativeness, urban flow, chemistry, deposition or responsibility from PM readings alone. | Correct numerical execution can still yield a wrong location under missing information or model mismatch. | Weather evidence is labelled unverified unless qualifying comparisons are supplied; measured-data access remains blocked. | High | Unresolved information/model limit; requires suitable measured or controlled-release validation. |

## Defect classes

Demonstrated implementation defects were the protocol-only migration check and
non-finite competing-source serialization path; both are fixed with focused
regressions. Approximation defects remain: finite weather/source quadrature,
bounded adequacy candidates, selected rows, and a limited predictive screen.
Model mismatch is represented by explicit v0.7 residual and predictive flags;
the engine withholds a resolved label rather than converting those flags into a
source explanation. Information limits remain when several source/weather/
background explanations fit the same readings. Those limits cannot be removed
by a larger optimizer without new independent observations or a defensible
physical model.

## Operating limits and unresolved issues

The supported reconstruction requires at least two usable sensors, at least
two source-domain anchors, steady open terrain, local representative weather,
wind speed from 0.8–8 m/s, direction variation within 25°, speed ratio at most
2, receptors within 3 km and source cells within 1.5 km. A study window is at
most one hour; campaigns contain two to six non-overlapping steady windows and
assume one fixed source and constant release. Unsupported weather or numerical
workload is refused while raw inputs remain available.

The v0.7 candidate has no measured validation. NOAA/DATEM/Sagebrush access was
blocked by the environment proxy, and the inspected Prairie Grass workbook
lacks verified provenance/units/meteorology compatibility. No output supports
field accuracy, calibration, source responsibility, regulatory attribution,
partner adoption or organizational reliability.

The monitoring planner can expose candidate scores, costs, feasibility,
observed-window timestamp and uncertainty diagnostics as experimental planning
evidence. It must keep measurements, predictions, resident accounts and inferred
explanations distinct; it must not present a plan as a guaranteed source or
health intervention.
