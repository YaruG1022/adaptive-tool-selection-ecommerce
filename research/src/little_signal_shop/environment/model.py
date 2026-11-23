"""Configuration and public decision data for the first experiment."""

from dataclasses import dataclass, fields
from enum import Enum


def require_nonnegative_int(name: str, value: int) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


class Action(str, Enum):
    STOP = "stop"
    MARKET_REPORT = "market_report"
    FORECAST = "forecast"


@dataclass(frozen=True, slots=True)
class EnvironmentConfig:
    days: int = 90
    opening_cash_cents: int = 10_000
    opening_stock: int = 5
    unit_cost_cents: int = 500
    selling_price_cents: int = 900
    terminal_unit_nrv_cents: int = 300
    opening_minute: int = 540
    cutoff_minute: int = 630
    market_report_fee_cents: int = 100
    market_report_minutes: int = 30
    forecast_fee_cents: int = 200
    forecast_minutes: int = 60

    def __post_init__(self) -> None:
        for field in fields(self):
            require_nonnegative_int(field.name, getattr(self, field.name))
        if self.days < 2:
            raise ValueError("days must include at least one decision day and one final day")
        if not 0 < self.unit_cost_cents < self.selling_price_cents:
            raise ValueError("selling price must exceed positive unit cost")
        if not self.opening_minute <= self.cutoff_minute < 1440:
            raise ValueError("decision window must be ordered and within one day")
        if self.market_report_minutes == 0 or self.forecast_minutes == 0:
            raise ValueError("tool durations must be positive")


@dataclass(frozen=True, slots=True)
class Observation:
    day: int
    clock_minute: int
    cash_cents: int
    stock: int
    public_today: int
    public_tomorrow: int
    market_report: int | None
    forecast: int | None
    sales_yesterday: int | None
    remaining_days: int
    remaining_calls: int
    legal_actions: tuple[Action, ...]


@dataclass(frozen=True, slots=True)
class StepResult:
    observation: Observation | None
    reward_cents: int
    terminated: bool
