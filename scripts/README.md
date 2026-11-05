# Project commands

Reserved for small entry points that call tested project modules: reference-fixture generation, baseline comparisons, training, held-out evaluation, and episode export. No runnable commands are implemented yet.

Add commands when their implementation exists, together with documented inputs, configuration paths, output location, and a small reproducible example. Keep simulation and learning logic in the implementation modules. Commands should write generated output under `artifacts/` and record code revision, environment/schema versions, configuration, and seeds.

The current game still runs by opening root `index.html`; it needs no setup command.
