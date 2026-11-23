# Verification

The environment and baseline checks run with the Python standard library. DQN training and held-out evaluation checks use PyTorch. See the [test command](../research/README.md#run-the-checks).

| Directory | Intended checks |
| --- | --- |
| `test_environment.py` | Environment lifecycle, legal actions, observation boundaries, ledger, and complete 90-day episodes on saved inputs |
| `test_baselines.py` | Baseline decision rules, information boundaries, and legal tool choices |
| `test_baseline_comparison.py` | Validation-only runs, pairings, provenance, saved-input replay, and failed-run handling |
| `test_learned_evaluation.py` | DQN action masks, terminal targets, checkpoint integrity and identity, matched held-out evaluation, and sensitivity replay |
| `test_browser_export.py` | Research bundle export, source ledgers, matched episodes, and training checkpoint provenance |
| `test_research_records.cjs` | Browser bundle version, chronology, reconciliation, and immutability |
| `fixtures/` | Versioned market inputs and independent expected results, including the two-day worked example |
| `browser/` | Three screens, English default, state-preserving language changes, settlement, playback controls, and replay isolation |
| `contracts/` | Reserved for shared record and schema checks |

Run the parser checks with `node --test tests/test_research_records.cjs`. To verify the integration in Chromium, install or locate Playwright, [export the Phase 5 archive](../research/README.md#export-research-records-for-the-browser), and run `node tests/browser/research-import.cjs`. The script accepts a bundle path as its first argument. `PLAYWRIGHT_MODULE` selects an available Playwright module path and `PLAYWRIGHT_BROWSER_EXECUTABLE` can select an installed Chromium browser.

The initial browser setup was verified against the unchanged prototype. Reproducible reference values are recorded in [Phase 0](../docs/implementation-plan.md#phase-0--preserve-the-prototype); these rounded values are characterization anchors, not a substitute for full fixtures.

Add meaningful tests with each implementation phase. Keep generated reports, browser profiles, screenshots, and large episode dumps in `artifacts/`, not fixtures. Fixtures must be small, intentional, free of credentials, and identify their environment version.
