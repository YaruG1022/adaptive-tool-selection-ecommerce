# DQN training and selection v1

The training program compared two multilayer perceptrons under the [frozen evaluation protocol](../contracts/evaluation-v1.md#phase-4-dqn-selection). It ran each candidate on learning seeds 401–405 for 500 episodes per seed using the 128 training markets. Each run evaluated checkpoints at episodes 100, 250, and 500 on all 24 archived validation markets. The 10 runs yielded 30 checkpoints and 720 validation episodes.

| Candidate | Hidden layers | Learning rate | Mean validation final net worth at episodes 100, 250, and 500 |
| --- | --- | ---: | ---: |
| `mlp32` | 32, 32 | 0.0003 | $2,456.17 at each checkpoint |
| `mlp64` | 64, 64 | 0.001 | $2,456.17 at each checkpoint |

Both candidates use Adam, experience replay, an undiscounted 90-day objective, and a periodically updated target network. The controller encodes public observations and restricts exploration, greedy inference, and target maximization to legal actions. Terminal transitions have zero bootstrap value. The [training configuration](../research/configs/dqn-v1.json) records the full settings.

**Frozen selection: `mlp32` at episode 100 for all five learning seeds.** The six candidate-checkpoint combinations tied on the complete validation grid. The predeclared tie rules selected the earliest checkpoint and then `mlp32`. The selected policies used only `STOP` on the validation markets and matched the no-tool baseline. The frozen uncertainty-threshold reference averaged $2,469.42 on these markets.

All 10 logs contain 500 training episodes with finite recorded optimization losses. Reloading the five selected checkpoints reproduced all 120 corresponding validation scores exactly. These results use Python 3.12.4 and CPU-only PyTorch 2.8.0. The local archive is `artifacts/phase4-dqn`. It contains the training and validation inputs, the source fingerprint, the per-seed learning histories, the validation rankings, and the checksummed checkpoints. See the [training command](../research/README.md#train-and-evaluate-the-dqn) to regenerate the archive.
