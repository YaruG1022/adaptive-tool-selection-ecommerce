"""Decision clock, inventory ledger, and completed episode records."""

from copy import deepcopy
from dataclasses import asdict, dataclass, replace

from ..policies.replenishment import replenishment_units
from .market import DayInput, MarketInputs
from .model import Action, EnvironmentConfig, Observation, StepResult


@dataclass(frozen=True, slots=True)
class _Tool:
    observation_field: str
    fee_cents: int
    duration_minutes: int


@dataclass(frozen=True, slots=True)
class _Settlement:
    day: int
    received_units: int
    opening_stock: int
    ordered_units: int
    purchase_cents: int
    delivery_day: int | None
    sold_units: int
    unfilled_units: int
    revenue_cents: int
    closing_stock: int
    in_transit_units: int
    cash_cents: int
    inventory_value_cents: int
    terminal_write_down_cents: int
    net_worth_cents: int


def _record_observation(observation: Observation | None) -> dict | None:
    if observation is None:
        return None
    result = asdict(observation)
    result["legal_actions"] = [action.value for action in observation.legal_actions]
    return result


class ShopEnvironment:
    """A tool-selection environment that applies the same replenishment rule at every stop."""

    def __init__(self, config: EnvironmentConfig) -> None:
        self._config = config
        self._tools = {
            Action.MARKET_REPORT: _Tool(
                "market_report", config.market_report_fee_cents, config.market_report_minutes
            ),
            Action.FORECAST: _Tool("forecast", config.forecast_fee_cents, config.forecast_minutes),
        }
        self._inputs: MarketInputs | None = None
        self._observation: Observation | None = None
        self._received_units = 0
        self._transitions: list[dict] = []

    def reset(self, inputs: MarketInputs) -> Observation:
        """Start at day 1 with an explicit, precomputed market path."""
        if not isinstance(inputs, MarketInputs) or len(inputs.days) != self._config.days:
            raise ValueError("market inputs must contain one row per configured day")
        self._inputs = inputs
        self._received_units = 0
        self._transitions.clear()
        self._observation = self._open_day(
            day=1,
            market_day=inputs.days[0],
            cash_cents=self._config.opening_cash_cents,
            stock=self._config.opening_stock,
            sales_yesterday=None,
        )
        return self._observation

    def observe(self) -> Observation | None:
        """Return an immutable decision snapshot, or None after the final settlement."""
        if self._inputs is None:
            raise RuntimeError("reset the environment before observing")
        return self._observation

    def step(self, action: Action) -> StepResult:
        """Call an eligible tool or stop and settle, returning the net-worth change."""
        inputs = self._inputs
        before = self._observation
        if inputs is None or before is None:
            raise RuntimeError("reset the environment before taking another action")
        action = Action(action)
        if action not in before.legal_actions:
            raise ValueError(f"{action.value} is unavailable at this decision")

        current_day = inputs.days[before.day - 1]
        settlements = []
        fee_cents = 0
        worth_before = before.cash_cents + before.stock * self._config.unit_cost_cents
        if action is Action.STOP:
            settlements, after = self._stop(before, current_day, inputs.days[before.day])
            worth_after = settlements[-1].net_worth_cents
        else:
            tool = self._tools[action]
            fee_cents = tool.fee_cents
            after = self._with_legal_actions(replace(
                before,
                clock_minute=before.clock_minute + tool.duration_minutes,
                cash_cents=before.cash_cents - fee_cents,
                remaining_calls=before.remaining_calls - 1,
                **{tool.observation_field: getattr(current_day, tool.observation_field)},
            ))
            worth_after = worth_before - fee_cents

        reward_cents = worth_after - worth_before
        self._observation = after
        self._transitions.append({
            "action": action.value,
            "before": _record_observation(before),
            "after": _record_observation(after),
            "reward_cents": reward_cents,
            "net_worth_cents": worth_after,
            "fee_cents": fee_cents,
            "settlements": [asdict(settlement) for settlement in settlements],
        })
        return StepResult(after, reward_cents, terminated=after is None)

    def episode_record(
        self, code_revision: str, controller_id: str, model_id: str | None = None
    ) -> dict:
        """Export a detached, JSON-ready record once all decisions have ended."""
        if self._inputs is None or self._observation is not None:
            raise RuntimeError("episode records are available after final settlement")
        ids = {"code_revision": code_revision, "controller_id": controller_id}
        if model_id is not None:
            ids["model_id"] = model_id
        for name, value in ids.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        return {
            "environment_version": "1",
            "schema_version": "1",
            "config": asdict(self._config),
            "input_id": self._inputs.input_id,
            "seed": self._inputs.seed,
            "code_revision": code_revision,
            "controller_id": controller_id,
            "model_id": model_id,
            "initial_net_worth_cents": (
                self._config.opening_cash_cents
                + self._config.opening_stock * self._config.unit_cost_cents
            ),
            "final_net_worth_cents": self._transitions[-1]["net_worth_cents"],
            "transitions": deepcopy(self._transitions),
            "analysis_only": {"daily_demand": [day.demand for day in self._inputs.days]},
        }

    def _open_day(
        self, *, day: int, market_day: DayInput, cash_cents: int, stock: int,
        sales_yesterday: int | None,
    ) -> Observation:
        return self._with_legal_actions(Observation(
            day=day,
            clock_minute=self._config.opening_minute,
            cash_cents=cash_cents,
            stock=stock,
            public_today=market_day.public_today,
            public_tomorrow=market_day.public_tomorrow,
            market_report=None,
            forecast=None,
            sales_yesterday=sales_yesterday,
            remaining_days=self._config.days - day + 1,
            remaining_calls=len(self._tools),
            legal_actions=(),
        ))

    def _with_legal_actions(self, observation: Observation) -> Observation:
        legal_actions = [Action.STOP]
        for action, tool in self._tools.items():
            if (
                getattr(observation, tool.observation_field) is None
                and observation.cash_cents >= tool.fee_cents
                and observation.clock_minute + tool.duration_minutes <= self._config.cutoff_minute
            ):
                legal_actions.append(action)
        return replace(observation, legal_actions=tuple(legal_actions))

    def _stop(
        self, before: Observation, current_day: DayInput, next_day: DayInput
    ) -> tuple[list[_Settlement], Observation | None]:
        expected_today = (
            before.market_report if before.market_report is not None else before.public_today
        )
        target_tomorrow = before.forecast if before.forecast is not None else before.public_tomorrow
        order = replenishment_units(
            stock=before.stock,
            expected_today=expected_today,
            target_tomorrow=target_tomorrow,
            cash_cents=before.cash_cents,
            unit_cost_cents=self._config.unit_cost_cents,
        )
        settled = self._settle_day(
            day=before.day,
            opening_stock=before.stock,
            cash_cents=before.cash_cents,
            received_units=self._received_units,
            demand=current_day.demand,
            ordered_units=order,
        )
        day = before.day + 1
        stock = settled.closing_stock + order
        if day == self._config.days:
            terminal = self._settle_day(
                day=day,
                opening_stock=stock,
                cash_cents=settled.cash_cents,
                received_units=order,
                demand=next_day.demand,
                ordered_units=0,
            )
            return [settled, terminal], None

        self._received_units = order
        after = self._open_day(
            day=day,
            market_day=next_day,
            cash_cents=settled.cash_cents,
            stock=stock,
            sales_yesterday=settled.sold_units,
        )
        return [settled], after

    def _settle_day(
        self, *, day: int, opening_stock: int, cash_cents: int, received_units: int,
        demand: int, ordered_units: int,
    ) -> _Settlement:
        sold_units = min(opening_stock, demand)
        closing_stock = opening_stock - sold_units
        purchase_cents = ordered_units * self._config.unit_cost_cents
        revenue_cents = sold_units * self._config.selling_price_cents
        ending_cash = cash_cents - purchase_cents + revenue_cents
        inventory = (closing_stock + ordered_units) * self._config.unit_cost_cents
        write_down = 0
        if day == self._config.days:
            write_down = closing_stock * max(
                0, self._config.unit_cost_cents - self._config.terminal_unit_nrv_cents
            )
        inventory_value = inventory - write_down
        return _Settlement(
            day=day,
            received_units=received_units,
            opening_stock=opening_stock,
            ordered_units=ordered_units,
            purchase_cents=purchase_cents,
            delivery_day=day + 1 if ordered_units else None,
            sold_units=sold_units,
            unfilled_units=demand - sold_units,
            revenue_cents=revenue_cents,
            closing_stock=closing_stock,
            in_transit_units=ordered_units,
            cash_cents=ending_cash,
            inventory_value_cents=inventory_value,
            terminal_write_down_cents=write_down,
            net_worth_cents=ending_cash + inventory_value,
        )
