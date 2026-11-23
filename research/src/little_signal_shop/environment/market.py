"""Create or supply market inputs before any controller acts."""

from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import json
from random import Random

from .model import EnvironmentConfig, require_nonnegative_int


@dataclass(frozen=True, slots=True)
class DayInput:
    demand: int
    public_today: int = 0
    public_tomorrow: int = 0
    market_report: int = 0
    forecast: int = 0

    def __post_init__(self) -> None:
        for field in fields(self):
            require_nonnegative_int(field.name, getattr(self, field.name))


@dataclass(frozen=True, slots=True)
class MarketInputs:
    days: tuple[DayInput, ...]
    seed: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.days, tuple) or any(
            not isinstance(day, DayInput) for day in self.days
        ):
            raise ValueError("days must be a tuple of DayInput values")
        if self.seed is not None:
            require_nonnegative_int("seed", self.seed)

    @property
    def input_id(self) -> str:
        rows = [asdict(day) for day in self.days]
        encoded = json.dumps(rows, separators=(",", ":"), ensure_ascii=True)
        return sha256(encoded.encode("ascii")).hexdigest()


def generate_market(config: EnvironmentConfig, seed: int) -> MarketInputs:
    """Generate coupled daily demand and noisy observations for one market seed."""
    require_nonnegative_int("seed", seed)
    channels = {
        name: Random(f"lss-market-v1:{seed}:{name}")
        for name in ("regime", "demand", "public_today", "public_tomorrow", "market_report", "forecast")
    }
    regime = channels["regime"]
    level = 5 if regime.random() < 0.5 else 11
    demand = []
    for day in range(config.days):
        if day > 0 and regime.random() < 0.20:
            level = 11 if level == 5 else 5
        demand.append(max(0, level + channels["demand"].randint(-3, 3)))

    def estimate(target: int, channel: str, noise: int) -> int:
        return max(0, target + channels[channel].randint(-noise, noise))

    rows = [
        DayInput(
            demand=today,
            public_today=estimate(today, "public_today", 4),
            public_tomorrow=estimate(tomorrow, "public_tomorrow", 6),
            market_report=estimate(today, "market_report", 1),
            forecast=estimate(tomorrow, "forecast", 2),
        )
        for today, tomorrow in zip(demand, demand[1:])
    ]
    rows.append(DayInput(demand=demand[-1]))
    return MarketInputs(tuple(rows), seed=seed)
