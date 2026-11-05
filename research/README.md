# Research implementation

Reserved for a Python research environment and reproducible experiments. No Python package, environment interface, training code, or DQN model is implemented by this scaffold. Dependency manifests and runnable commands should be added with the first tested implementation.

```text
research/
  configs/                          Versioned environment and experiment settings
  src/little_signal_shop/
    environment/                    World transitions, accounting, information tools, observations, rewards
    policies/                       The fixed operational business policy
    controllers/                    No-tools, full-budget, fixed-rule, and future DQN tool selection
    experiments/                    Episode runners, training/evaluation orchestration, metrics and export
```

The environment owns hidden market state; controllers receive only permitted observations. All compared controllers use the same business policy. Keep recording/serialization behind the environment and runner interfaces, with shared formats specified in [contracts](../contracts/README.md).

JavaScript/Python compatibility must be established before results are compared. After that gate, Python owns research execution and the browser can import episode records for demonstration. Store generated runs, checkpoints, and exports under root `artifacts/`, not in source or configuration directories. Keep training, validation/tuning, and evaluation seed sets explicit and separate.
