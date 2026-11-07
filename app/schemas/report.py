"""Reporting schemas."""
from decimal import Decimal
import uuid
from pydantic import BaseModel, Field


class MonthlySummaryResponse(BaseModel):
    """Aggregated financial summary for a single month."""

    month: str = Field(..., description="Month in YYYY-MM format")
    total_income: Decimal
    total_expense: Decimal
    net_savings: Decimal
    savings_rate: Decimal = Field(..., description="Percentage of income saved (0.00 - 100.00)")


class CategoryBreakdownItem(BaseModel):
    """Category level spending or income item."""

    category_id: uuid.UUID | None
    category_name: str
    total_amount: Decimal
    percentage: Decimal = Field(..., description="Percentage of directional total")


class CategoryBreakdownResponse(BaseModel):
    """Breakdown of expenses or income categorized for a given month."""

    month: str
    direction: str
    total_amount: Decimal
    items: list[CategoryBreakdownItem]


class BudgetVsActualItem(BaseModel):
    """Comparison between budgeted and actual spend per category."""

    category_id: uuid.UUID
    category_name: str
    budgeted_amount: Decimal
    actual_amount: Decimal
    difference: Decimal = Field(..., description="budgeted - actual (positive is under budget)")
    percentage_used: Decimal = Field(..., description="(actual / budgeted) * 100")


class BudgetVsActualResponse(BaseModel):
    """Comprehensive budget versus actual comparison for a given month."""

    month: str
    total_budgeted: Decimal
    total_actual: Decimal
    items: list[BudgetVsActualItem]
