"""
LuxeLife API — v1 route aggregator.

Collects all v1 routers into a single router that is mounted on the app.
"""

from fastapi import APIRouter

from app.api.v1.agreements import router as agreements_router
from app.api.v1.auth import router as auth_router
from app.api.v1.disputes import router as disputes_router
from app.api.v1.inspections import router as inspections_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.kyc import router as kyc_router
from app.api.v1.messaging import router as messaging_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.payments import router as payments_router
from app.api.v1.properties import router as properties_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.users import router as users_router

v1_router = APIRouter()
v1_router.include_router(agreements_router)
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(properties_router)
v1_router.include_router(payments_router)
v1_router.include_router(jobs_router)
v1_router.include_router(inspections_router)
v1_router.include_router(kyc_router)
v1_router.include_router(notifications_router)
v1_router.include_router(messaging_router)
v1_router.include_router(disputes_router)
v1_router.include_router(uploads_router)
