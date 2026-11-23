"""Fixed tool-selection baselines for the first controlled experiment."""

from collections.abc import Callable

from ..environment import Action, EnvironmentConfig, Observation
from ..policies.replenishment import replenishment_units


BASELINE_IDS = ("no_tools", "fixed_order", "uncertainty_threshold")


def _no_tools(_observation: Observation) -> Action:
    return Action.STOP


def _fixed_order(observation: Observation) -> Action:
    for action in (Action.MARKET_REPORT, Action.FORECAST):
        if action in observation.legal_actions:
            return action
    return Action.STOP


def make_baselines(config: EnvironmentConfig) -> dict[str, Callable[[Observation], Action]]:
    """Return deterministic controllers that use the public observation only."""
    margin_per_unit = config.selling_price_cents - config.unit_cost_cents

    def uncertainty_threshold(observation: Observation) -> Action:
        today = observation.public_today
        if observation.market_report is not None:
            today = observation.market_report
        tomorrow = observation.public_tomorrow
        if observation.forecast is not None:
            tomorrow = observation.forecast

        def order_size(expected_today: int, target_tomorrow: int, *, cash_cents: int) -> int:
            return replenishment_units(
                stock=observation.stock,
                expected_today=expected_today,
                target_tomorrow=target_tomorrow,
                cash_cents=cash_cents,
                unit_cost_cents=config.unit_cost_cents,
            )

        # Consider the market report first so a positive score tie favors it.
        candidates = (
            (
                Action.MARKET_REPORT,
                config.market_report_fee_cents,
                (max(0, observation.public_today - 4), tomorrow),
                (observation.public_today + 4, tomorrow),
            ),
            (
                Action.FORECAST,
                config.forecast_fee_cents,
                (today, max(0, observation.public_tomorrow - 6)),
                (today, observation.public_tomorrow + 6),
            ),
        )

        best_action = Action.STOP
        best_score = 0
        for action, fee, lower_estimates, upper_estimates in candidates:
            if action not in observation.legal_actions:
                continue
            post_fee_cash = observation.cash_cents - fee
            lower_order = order_size(*lower_estimates, cash_cents=post_fee_cash)
            upper_order = order_size(*upper_estimates, cash_cents=post_fee_cash)
            score = (upper_order - lower_order) * margin_per_unit - fee
            if score > best_score:
                best_action = action
                best_score = score
        return best_action

    return {
        "no_tools": _no_tools,
        "fixed_order": _fixed_order,
        "uncertainty_threshold": uncertainty_threshold,
    }
