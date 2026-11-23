# Project commands

Run the baseline comparison and saved-input replay through the [Python module command](../research/README.md#run-the-baseline-comparison). The `scripts/` directory is reserved for future standalone entry points.

Add commands when their implementation exists, together with documented inputs, configuration paths, output location, and a small reproducible example. Keep simulation and learning logic in the implementation modules. Commands should write generated output under `artifacts/` and record code revision, environment/schema versions, configuration, and seeds.

The current game still runs by opening root `index.html`; it needs no setup command.
