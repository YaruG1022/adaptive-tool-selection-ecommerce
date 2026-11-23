# Shared contracts

The [environment v1 specification](environment-v1.md) defines the Python experiment and its episode record. The [worked fixture](../tests/fixtures/worked-example-v1.json) gives machine-readable inputs and expected results.

The [evaluation protocol v1](evaluation-v1.md) fixes the baseline rules, seed splits, model selection, metrics, and held-out analysis.

The [browser bundle v1](browser-bundle-v1.md) defines the versioned local file exchanged by the Python exporter and Research Lab.

The specification covers the following behavior.

- State and episode configuration, including initial conditions and environment version.
- Controller observations, legal actions, tool budget/time, stopping, and termination.
- Accounting, valuation, reward timing, rounding, and terminal settlement.
- Reproducible exogenous market/tool inputs independent of action order.
- Immutable episode/receipt formats, run identity, configuration snapshots, and analysis-only fields.

Keep representative serialized examples in `tests/fixtures/`. Use stable record identifiers independently of English and Chinese presentation strings.
