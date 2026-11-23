# Project commands

Run the baseline comparison through its [Python module command](../research/README.md#run-the-baseline-comparison). The [training and evaluation commands](../research/README.md#train-and-evaluate-the-dqn) cover DQN selection, held-out evaluation, and replay.

The [browser export command](../research/README.md#export-research-records-for-the-browser) converts a saved comparison to a Research Lab import file.

Add commands when their implementation exists, together with documented inputs, configuration paths, output location, and a small reproducible example. Keep simulation and learning logic in the implementation modules. Commands should write generated output under `artifacts/` and record code revision, environment/schema versions, configuration, and seeds.

The current game still runs by opening root `index.html`; it needs no setup command.
