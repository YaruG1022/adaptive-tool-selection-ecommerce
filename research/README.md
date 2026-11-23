# Research implementation

The first research environment simulates one product over 90 days using two paid tools and a fixed replenishment policy. It runs on Python 3.10 or newer with the standard library. See [environment v1](../contracts/environment-v1.md) for the exact clock, market generator, ledger, and record format.

## Run the checks

From the repository root in PowerShell, expose the source directory and run the tests with a Python 3.10+ interpreter.

```powershell
$env:PYTHONPATH = (Resolve-Path 'research/src').Path
python -B -m unittest discover -s tests -v
```

Use the full path to `python.exe` if the interpreter is outside `PATH`. In a POSIX shell, run `PYTHONPATH=research/src python3 -B -m unittest discover -s tests -v`.

Install the training dependency below to include the DQN and held-out evaluation tests in discovery.

## Use the environment

With `research/src` on the Python import path, this example exercises a complete episode on one market seed.

```python
from little_signal_shop.environment import Action, EnvironmentConfig, ShopEnvironment, generate_market

config = EnvironmentConfig()
shop = ShopEnvironment(config)
observation = shop.reset(generate_market(config, seed=101))
total_reward_cents = 0
while observation is not None:
    result = shop.step(Action.STOP)
    total_reward_cents += result.reward_cents
    observation = result.observation
print(total_reward_cents)
```

Choose actions from `observation.legal_actions`. For matched comparisons, save and reuse the same `MarketInputs` rows. After termination, `episode_record(code_revision, controller_id, model_id=None)` returns a JSON-ready record for analysis. Use the actual source revision and controller identifier when collecting results.

## Run the baseline comparison

From the repository root with `research/src` on the import path, run the three baseline controllers on the 24 versioned validation markets. Use a new output directory for each run.

```powershell
$env:PYTHONPATH = (Resolve-Path 'research/src').Path
python -B -m little_signal_shop.experiments.baseline_comparison --output artifacts/phase3-baselines
```

Replay the same experiment using the saved configuration and market rows.

```powershell
python -B -m little_signal_shop.experiments.baseline_comparison --config artifacts/phase3-baselines/config.json --inputs artifacts/phase3-baselines/market_inputs.json --output artifacts/phase3-baselines-replay
```

See the [baseline development results](../docs/baseline-v1-results.md) and [evaluation protocol](../contracts/evaluation-v1.md) for metrics, output files, seed splits, and selection rules.

## Train and evaluate the DQN

Use a Python environment with the PyTorch dependency in [`requirements-dqn.txt`](requirements-dqn.txt). The study used CPU-only PyTorch 2.8.0 on Python 3.12.4. From the repository root, keep `research/src` on the import path and provide the saved Phase 3 validation inputs and summary to training.

```powershell
$env:PYTHONPATH = (Resolve-Path 'research/src').Path
python -B -m little_signal_shop.experiments.train_dqn --validation-inputs artifacts/phase3-baselines/market_inputs.json --baseline-summary artifacts/phase3-baselines/summary.json --output artifacts/phase4-dqn --workers 4
```

The training program evaluates checkpoints on the complete validation grid and records the joint selection across all five learning seeds. Keep the resulting training directory, including `selection.json` and its checkpoint files. The evaluation command verifies the selected files before running the held-out markets. Use a new directory for each output.

```powershell
python -B -m little_signal_shop.experiments.evaluate_dqn --training artifacts/phase4-dqn --output artifacts/phase5-held-out --sensitivity
```

Use `--inputs artifacts/phase5-held-out/market_inputs.json` to replay the saved main evaluation inputs in a new directory. The six sensitivity scenarios run with the same frozen checkpoints and baseline rules.

See the [training and selection report](../docs/dqn-v1-training.md) and [held-out evaluation report](../docs/held-out-v1-results.md).

## Package layout

```text
research/
  configs/                          Versioned environment and experiment settings
  src/little_signal_shop/
    environment/                    World transitions, accounting, information tools, observations, rewards
    policies/                       The fixed operational business policy
    controllers/                    Three fixed baselines and the DQN controller
    experiments/                    Baseline comparison, DQN training, and held-out evaluation
```

The environment owns hidden market state. The controller receives only decision-time observations, and every controller uses the same replenishment rule.

Keep generated runs, checkpoints, and exports under root `artifacts/`. The Phase 5 episode archives provide source records for the next phase's browser integration.
