# Reading the revised engine outputs

The investigation workflow remains unchanged: import measurements and weather,
record assumptions, mark accessible candidate sites, compare plans, and save or
export the investigation. The engine changes the meaning of source markers and
adds evidence checks; this document describes those meanings, not a performance
claim.

## Source explanations and domain anchors

The current engine compares a background-only explanation with a single-source
explanation. Their model weights are conditional on the implemented priors,
transport model, noise model, and input data. They are not probabilities of
responsibility. A background-only result does not establish the absence of
pollution, multiple sources, or an unmodelled source.

Marked source locations now act as **domain anchors**. The search domain is the
rectangle spanned by them. The calculation assumes that a single source lies
inside that rectangle; it does not establish that the selected domain contains
every plausible source. Boundary weight requires reviewing domain completeness.
The displayed anchor weights summarize nearest-anchor partitions of the domain,
conditional on a single source. They are not probabilities at exact marker
coordinates. Earlier archived models used discrete-location weights; reports
retain that distinction.

Map shading shows cells containing at least 90% of the approximate conditional
single-source model mass. The UI and report give both region area and domain
area. The nominal 90% mass is a model calculation, not an empirically calibrated
geographic confidence level. Numerical cell size targets 20 m, capped at 24
cells per side, and the actual resolution is displayed. Degenerate rectangles
retain discrete hypotheses and have no geographic region area.

## Four different evidence questions

- Implementation checks establish whether calculations implement the stated
  model; they do not establish physical realism.
- Model adequacy is screened by withholding whole sensors. Unavailable checks
  are explicitly labelled. A check that raises no warning can still miss a
  different physical explanation.
- Identifiability asks whether the available data distinguish the implemented
  explanations. The UI prominently says when a source remains unresolved or a
  predictive mismatch is flagged. Evidence-label thresholds are interpretive
  rules, not calibrated accuracy guarantees.
- Empirical reliability requires independent performance evidence. Synthetic
  results do not establish field PM2.5 attribution, geographic coverage, or
  community benefit.

## Observation counts and plans

Loaded, excluded, usable, and fitted rows are displayed separately. A user can
change the fitting limit and observation-selection seed in Scenarios; this
invalidates the current result and does not delete raw observations. The result
records the selection method, limit, and seed. Full retained readings remain in
the private JSON and CSV exports.

Experimental information planning estimates learning about background-only
versus broad source areas using a finite mixture and numerical integration.
Plans use the assumed observed weather window, rather than a future forecast.
Model scores are not expected percentage improvements or guaranteed reductions
in localization error. Spread, random, and applicable wind baselines remain
visible for review. Spatial coverage remains a geometric design objective.
The information-plan label now says "Experimental information" rather than
"Optimized". Browser assertions for this visible wording were updated; their
constraint, save/reopen, baseline, offline, import, and export checks remain.

The evidence HTML gives the model interpretation, counts, checks, and region
areas, but excludes exact source-domain coordinates and region polygons. The
private investigation JSON retains them. Resident free-text notes still require
the operator's privacy review before sharing.
