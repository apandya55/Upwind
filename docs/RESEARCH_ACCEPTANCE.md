# Accepted/rejected final results

Forty paired seed blocks per condition; generated/refused counts are in the main report. Conditional coverage refers to a primary source where one exists. Interpret both groups and area/error jointly; an accepted label is not validated accuracy. All rates/intervals/distributions and per-condition source-presence reliability bins are retained in [the raw JSON](../evaluations/research/acceptance-reliability.json).

| Condition | Group | n / fitted | Present/covered | MAP p10 / median / p90 m | Mean area % | Brier mean |
|---|---|---|---|---|---|---|
| background_campaign | accepted | 0/40 | 0 / 0 | — / — / — | — | — |
| background_campaign | rejected | 40/40 | 0 / 0 | — / — / — | 72.0 | 0.083 |
| biased_met_campaign | accepted | 18/40 | 18 / 0 | 113.0 / 151.5 / 219.0 | 5.7 | 0.001 |
| biased_met_campaign | rejected | 22/40 | 22 / 6 | 133.5 / 233.4 / 285.2 | 50.6 | 0.332 |
| boundary_campaign | accepted | 6/40 | 6 / 6 | 7.1 / 17.7 / 33.9 | 3.7 | 0.000 |
| boundary_campaign | rejected | 34/40 | 34 / 34 | 12.5 / 44.2 / 362.1 | 54.5 | 0.361 |
| changing_release_campaign | accepted | 20/40 | 20 / 13 | 31.3 / 70.0 / 148.3 | 11.9 | 0.001 |
| changing_release_campaign | rejected | 20/40 | 20 / 19 | 20.6 / 74.7 / 225.2 | 50.3 | 0.257 |
| correlated_campaign | accepted | 9/40 | 9 / 6 | 21.1 / 57.4 / 114.0 | 9.1 | 0.000 |
| correlated_campaign | rejected | 31/40 | 31 / 20 | 9.0 / 116.7 / 302.1 | 19.6 | 0.067 |
| independent_transport | accepted | 27/40 | 27 / 24 | 14.5 / 37.4 / 155.6 | 8.6 | 0.000 |
| independent_transport | rejected | 13/40 | 13 / 13 | 30.3 / 148.7 / 277.4 | 54.7 | 0.328 |
| informative_campaign | accepted | 25/40 | 25 / 23 | 10.5 / 22.3 / 108.1 | 11.6 | 0.001 |
| informative_campaign | rejected | 15/40 | 15 / 15 | 11.0 / 28.1 / 233.4 | 52.4 | 0.286 |
| same_wind_repetition | accepted | 7/40 | 7 / 7 | 17.0 / 67.5 / 115.4 | 20.5 | 0.001 |
| same_wind_repetition | rejected | 33/40 | 33 / 32 | 69.9 / 164.1 / 373.9 | 69.7 | 0.285 |
| single_window_original | accepted | 0/40 | 0 / 0 | — / — / — | — | — |
| single_window_original | rejected | 40/40 | 40 / 39 | 74.5 / 188.8 / 281.2 | 84.9 | 0.274 |
| two_sources_campaign | accepted | 30/40 | 30 / 15 | 10.5 / 91.7 / 360.8 | 11.2 | 0.000 |
| two_sources_campaign | rejected | 10/40 | 10 / 8 | 58.4 / 162.1 / 336.7 | 46.1 | 0.200 |
| unsupported_campaign | accepted | 0/0 | 0 / 0 | — / — / — | — | — |
| unsupported_campaign | rejected | 0/0 | 0 / 0 | — / — / — | — | — |
| weak_campaign | accepted | 0/40 | 0 / 0 | — / — / — | — | — |
| weak_campaign | rejected | 40/40 | 40 / 27 | 94.1 / 215.9 / 426.8 | 73.7 | 0.547 |


Presence reliability bins do not demonstrate population calibration: the benchmark intentionally constructs conditions with different prevalence and reused seed blocks. Within-condition bins have small denominators and often all or no sources. They cannot identify a facility or justify source-location precision.
