# Verification

The environment and baseline checks run with the Python standard library. See the [test command](../research/README.md#run-the-checks).

| Directory | Intended checks |
| --- | --- |
| `test_environment.py` | Environment lifecycle, legal actions, observation boundaries, ledger, and complete 90-day episodes on saved inputs |
| `test_baselines.py` | Baseline decision rules, information boundaries, and legal tool choices |
| `test_baseline_comparison.py` | Validation-only runs, pairings, provenance, saved-input replay, and failed-run handling |
| `fixtures/` | Versioned market inputs and independent expected results, including the two-day worked example |
| `browser/` | Three screens, English default, state-preserving language changes, settlement, playback controls, and replay isolation |
| `contracts/` | Reserved for shared record and schema checks |
| `research/` | Reserved for controller training and held-out evaluation checks |

The initial browser setup was verified against the unchanged prototype. Reproducible reference values are recorded in [Phase 0](../docs/implementation-plan.md#phase-0--preserve-the-prototype); these rounded values are characterization anchors, not a substitute for full fixtures.

Add meaningful tests with each implementation phase. Keep generated reports, browser profiles, screenshots, and large episode dumps in `artifacts/`, not fixtures. Fixtures must be small, intentional, free of credentials, and identify their environment version.
