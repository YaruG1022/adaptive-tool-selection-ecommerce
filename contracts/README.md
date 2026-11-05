# Shared contracts

This directory is reserved for reviewed, versioned specifications and machine-readable schemas shared by the JavaScript reference, Python environment, and replay importer. No validated contract or schema is supplied by this scaffold.

Phase 1 should define:

- State and episode configuration, including initial conditions and environment version.
- Controller observations, legal actions, tool budget/time, stopping, and termination.
- Accounting, valuation, reward timing, rounding, and terminal settlement.
- Reproducible exogenous market/tool inputs independent of action order.
- Immutable episode/receipt formats, run identity, configuration snapshots, and analysis-only fields.

Describe prototype compatibility separately from deliberate research changes. Store representative serialized examples in `tests/fixtures/`, and test those examples against the eventual schemas. English/Chinese presentation strings are not identifiers and do not belong in controller observations.
