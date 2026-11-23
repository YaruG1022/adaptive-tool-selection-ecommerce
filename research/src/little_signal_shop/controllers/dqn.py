"""CPU Deep Q-Network training and deterministic checkpoint inference."""

from collections.abc import Callable
from dataclasses import asdict, dataclass
from math import isfinite, log1p
from pathlib import Path
from random import Random

import torch
from torch import Tensor, nn
from torch.nn import functional

from ..environment import Action, EnvironmentConfig, Observation


ACTION_ORDER = (Action.STOP, Action.MARKET_REPORT, Action.FORECAST)
FEATURE_COUNT = 12
CHECKPOINT_VERSION = "1"


def observation_features(observation: Observation, config: EnvironmentConfig) -> tuple[float, ...]:
    """Encode only the public observation, using -1 for an unobserved quantity."""
    def units(value: int | None) -> float:
        return -1.0 if value is None else value / 16

    window_minutes = max(1, config.cutoff_minute - config.opening_minute)
    return (
        log1p(observation.cash_cents / config.unit_cost_cents) / 8,
        units(observation.stock),
        units(observation.public_today),
        units(observation.public_tomorrow),
        units(observation.market_report),
        units(observation.forecast),
        units(observation.sales_yesterday),
        observation.remaining_days / config.days,
        observation.remaining_calls / 2,
        (config.cutoff_minute - observation.clock_minute) / window_minutes,
        float(Action.MARKET_REPORT in observation.legal_actions),
        float(Action.FORECAST in observation.legal_actions),
    )


def legal_mask(observation: Observation) -> tuple[bool, ...]:
    return tuple(action in observation.legal_actions for action in ACTION_ORDER)


def q_network(hidden_sizes: list[int]) -> nn.Sequential:
    layers: list[nn.Module] = []
    previous_size = FEATURE_COUNT
    for width in hidden_sizes:
        layers.extend((nn.Linear(previous_size, width), nn.ReLU()))
        previous_size = width
    layers.append(nn.Linear(previous_size, len(ACTION_ORDER)))
    return nn.Sequential(*layers)


def masked_bootstrap(q_values: Tensor, legal_masks: Tensor, terminated: Tensor) -> Tensor:
    """Return the greatest legal next Q-value, with zero on terminal transitions."""
    masked_max = q_values.masked_fill(~legal_masks, -torch.inf).max(dim=1).values
    return torch.where(terminated, 0.0, masked_max)


def greedy_actions(
    model: nn.Module, observations: list[Observation], config: EnvironmentConfig,
) -> list[Action]:
    """Choose legal actions by descending Q-value, with ties in ACTION_ORDER."""
    features = torch.tensor([observation_features(obs, config) for obs in observations], dtype=torch.float32)
    masks = torch.tensor([legal_mask(obs) for obs in observations], dtype=torch.bool)
    with torch.inference_mode():
        values = model(features)
    if not torch.isfinite(values).all():
        raise RuntimeError("DQN emitted a nonfinite Q-value")
    actions = values.masked_fill(~masks, -torch.inf).argmax(dim=1).tolist()
    return [ACTION_ORDER[index] for index in actions]


def load_controller(
    checkpoint: Path, config: EnvironmentConfig, *, expected_identity: tuple[str, int, int] | None = None,
) -> Callable[[Observation], Action]:
    """Restore an inference-only model from a weights-only CPU checkpoint."""
    data = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if not isinstance(data, dict) or data.get("format_version") != CHECKPOINT_VERSION:
        raise ValueError("unsupported DQN checkpoint format")
    if data.get("environment_config") != asdict(config):
        raise ValueError("DQN checkpoint was trained in a different environment configuration")
    if data.get("action_order") != [action.value for action in ACTION_ORDER]:
        raise ValueError("DQN checkpoint action order differs from this controller")
    identity = data.get("candidate_id"), data.get("learning_seed"), data.get("checkpoint_episode")
    if expected_identity is not None and identity != expected_identity:
        raise ValueError("DQN checkpoint identity differs from the frozen selection")
    sizes = data.get("hidden_sizes")
    if not isinstance(sizes, list) or not sizes or any(type(width) is not int or width < 1 for width in sizes):
        raise ValueError("DQN checkpoint has invalid hidden layer sizes")
    model = q_network(sizes)
    model.load_state_dict(data["state_dict"])
    model.eval()

    def choose(observation: Observation) -> Action:
        if len(observation.legal_actions) == 1:
            return observation.legal_actions[0]
        return greedy_actions(model, [observation], config)[0]

    return choose


@dataclass(frozen=True, slots=True)
class _Transition:
    features: tuple[float, ...]
    action_index: int
    reward: float
    next_features: tuple[float, ...]
    next_mask: tuple[bool, ...]
    terminated: bool


class DQNTrainer:
    """Train one learning seed with replay and a periodically refreshed target network."""

    def __init__(self, config: EnvironmentConfig, settings: dict, candidate: dict, seed: int) -> None:
        self.config = config
        self.settings = settings
        torch.manual_seed(seed)
        self.model = q_network(candidate["hidden_sizes"])
        self._target = q_network(candidate["hidden_sizes"])
        self._target.load_state_dict(self.model.state_dict())
        self._target.eval()
        self._optimizer = torch.optim.Adam(self.model.parameters(), lr=candidate["learning_rate"])
        self._exploration = Random(f"lss-dqn-v1:{seed}:exploration")
        self._sampling = Random(f"lss-dqn-v1:{seed}:replay")
        self._replay: list[_Transition] = []
        self.decision_steps = 0
        self.optimizer_steps = 0

    def choose(self, observation: Observation, features: tuple[float, ...], epsilon: float) -> Action:
        legal = [index for index, allowed in enumerate(legal_mask(observation)) if allowed]
        if len(legal) == 1:
            return ACTION_ORDER[legal[0]]
        if self._exploration.random() < epsilon:
            return ACTION_ORDER[self._exploration.choice(legal)]
        with torch.inference_mode():
            q_values = self.model(torch.tensor(features, dtype=torch.float32)).tolist()
        if not all(isfinite(value) for value in q_values):
            raise RuntimeError("DQN emitted a nonfinite Q-value")
        return ACTION_ORDER[max(legal, key=q_values.__getitem__)]

    def learn(
        self, features: tuple[float, ...], action: Action, reward_cents: int,
        next_features: tuple[float, ...] | None, next_observation: Observation | None,
    ) -> float | None:
        terminated = next_observation is None
        transition = _Transition(
            features,
            ACTION_ORDER.index(action),
            reward_cents / self.settings["reward_scale_cents"],
            (0.0,) * FEATURE_COUNT if next_features is None else next_features,
            (False,) * len(ACTION_ORDER) if terminated else legal_mask(next_observation),
            terminated,
        )
        capacity = self.settings["replay_capacity"]
        if len(self._replay) == capacity:
            self._replay[self.decision_steps % capacity] = transition
        else:
            self._replay.append(transition)
        self.decision_steps += 1
        if (len(self._replay) < self.settings["learning_starts"]
                or self.decision_steps % self.settings["train_every_steps"] != 0):
            return None

        batch = self._sampling.sample(self._replay, self.settings["batch_size"])
        features_batch = torch.tensor([row.features for row in batch], dtype=torch.float32)
        actions = torch.tensor([row.action_index for row in batch], dtype=torch.long)
        rewards = torch.tensor([row.reward for row in batch], dtype=torch.float32)
        next_features_batch = torch.tensor([row.next_features for row in batch], dtype=torch.float32)
        next_masks = torch.tensor([row.next_mask for row in batch], dtype=torch.bool)
        terminal_batch = torch.tensor([row.terminated for row in batch], dtype=torch.bool)

        with torch.no_grad():
            targets = rewards + self.settings["gamma"] * masked_bootstrap(
                self._target(next_features_batch), next_masks, terminal_batch,
            )
        predicted = self.model(features_batch).gather(1, actions[:, None]).squeeze(1)
        loss = functional.smooth_l1_loss(predicted, targets)
        loss_value = loss.item()
        if not isfinite(loss_value):
            raise RuntimeError("DQN loss became nonfinite")
        self._optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(), self.settings["gradient_clip_norm"], error_if_nonfinite=True)
        self._optimizer.step()
        self.optimizer_steps += 1
        if self.optimizer_steps % self.settings["target_update_steps"] == 0:
            self._target.load_state_dict(self.model.state_dict())
        return loss_value
