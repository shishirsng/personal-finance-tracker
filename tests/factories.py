"""Polyfactory model factories for test fixtures."""
from decimal import Decimal
import uuid
from polyfactory.factories.pydantic_factory import ModelFactory
from app.schemas.account import AccountCreate
from app.schemas.auth import UserRegisterRequest
from app.schemas.budget import BudgetUpsert
from app.schemas.category import CategoryCreate


class UserRegisterFactory(ModelFactory[UserRegisterRequest]):
    __model__ = UserRegisterRequest

    @classmethod
    def email(cls) -> str:
        return f"user_{uuid.uuid4().hex[:8]}@example.com"

    @classmethod
    def password(cls) -> str:
        return "StrongP@ssw0rd123!"

    @classmethod
    def full_name(cls) -> str:
        return "Test User"


class AccountCreateFactory(ModelFactory[AccountCreate]):
    __model__ = AccountCreate

    @classmethod
    def name(cls) -> str:
        return f"Checking {uuid.uuid4().hex[:4]}"

    @classmethod
    def type(cls) -> str:
        return "checking"

    @classmethod
    def currency(cls) -> str:
        return "USD"


class CategoryCreateFactory(ModelFactory[CategoryCreate]):
    __model__ = CategoryCreate

    @classmethod
    def name(cls) -> str:
        return f"Category {uuid.uuid4().hex[:4]}"

    @classmethod
    def kind(cls) -> str:
        return "expense"

    @classmethod
    def color(cls) -> str:
        return "#1E90FF"


class BudgetUpsertFactory(ModelFactory[BudgetUpsert]):
    __model__ = BudgetUpsert

    @classmethod
    def amount(cls) -> Decimal:
        return Decimal("500.00")
