"""Central API V1 Router aggregation."""
from fastapi import APIRouter
from app.api.v1.accounts import router as accounts_router
from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.categories import router as categories_router
from app.api.v1.ops import router as ops_router
from app.api.v1.reports import router as reports_router
from app.api.v1.transactions import router as transactions_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(accounts_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(budgets_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(ops_router)
