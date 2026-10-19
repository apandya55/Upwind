# Separate development sensitivity, declared before final evaluation

The candidate49-file freeze is already fixed. The auxiliary diagnostic
`scripts/diagnose_v06.py` does not select or alter it. It uses only inspected
seed7100000, characterized nominal and shared-reference-bias development cases.
Before any diagnostic fits, its own source hash/snapshot and fixed variants are
saved: common-mode probabilities0.1/0.25/0.5 at extra20deg SD, and extra15/30deg
SD at probability0.25. Production CONFIG is restored after every fit; source files
must remain unchanged. These are10 sensitivity fits, not new independent worlds.
Acceptance is not assessed because predictive diagnostic refits are disabled.
Two separately labelled evaluator-only correct-weather fits diagnose information
limits; known weather never enters any actual inference/planner input. No source
or threshold changes may be made from this diagnostic or final outcomes.


A second post-freeze numerical diagnostic compares the coarse integral, the
released one-stage adaptive integral and a uniformly subdivided fine reference.
It uses inspected development nominal seed7100000 only, plus a constructed
noiseless control generated with independent scalar plume arithmetic and exact
weather. The latter is a mathematical oracle/control, never a deployed correction
or measured validation. Retain all six scheduled integrals, including any workload
refusal. Compare posterior mass on the same coarse parent partition and mean
position differences to the uniform reference; no production changes may follow.
The diagnostic saves its own source snapshot/hash before fitting.
