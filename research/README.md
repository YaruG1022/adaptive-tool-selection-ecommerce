# Research implementation

The first research environment simulates one product over 90 days using two paid tools and a fixed replenishment policy. It runs on Python 3.10 or newer with the standard library. See [environment v1](../contracts/environment-v1.md) for the exact clock, market generator, ledger, and record format.

## Run the checks

From the repository root in PowerShell, expose the source directory and run the tests with a Python 3.10+ interpreter.

```powershell
$env:PYTHONPATH = (Resolve-Path 'research/src').Path
python -B -m unittest discover -s tests -v
```

Use the full path to `python.exe` if the interpreter is outside `PATH`. In a POSIX shell, run `PYTHONPATH=research/src python3 -B -m unittest discover -s tests -v`.

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

## Package layout

```text
research/
  configs/                          Versioned environment and experiment settings
  src/little_signal_shop/
    environment/                    World transitions, accounting, information tools, observations, rewards
    policies/                       The fixed operational business policy
    controllers/                    Three fixed baseline controllers
    experiments/                    Baseline comparison and protocol loader
```

The environment owns hidden market state. The controller receives only decision-time observations, and every controller uses the same replenishment rule.

The next phase adds the learned controller. Store generated runs, checkpoints, and exports under root `artifacts/`. Keep training, validation, and held-out evaluation seed sets separate.
