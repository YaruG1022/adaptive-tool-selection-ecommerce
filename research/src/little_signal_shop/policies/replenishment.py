"""Fixed order-up-to policy shared by all research controllers."""


def replenishment_units(
    *, stock: int, expected_today: int, target_tomorrow: int, cash_cents: int, unit_cost_cents: int
) -> int:
    """Return a whole-unit order within the cash available at decision time."""
    projected_stock = stock - min(stock, expected_today)
    needed_units = max(0, target_tomorrow - projected_stock)
    return min(needed_units, cash_cents // unit_cost_cents)
