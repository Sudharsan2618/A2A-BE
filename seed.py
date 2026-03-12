"""
Seed script — populates the database with sample data.

Run with:  python seed.py
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.database import async_session_factory
from app.models import generate_cuid
from app.models.job import Job, JobStatus
from app.models.notification import Notification
from app.models.payment import Payment, PaymentMethod, PaymentStatus, PaymentType
from app.models.property import Furnishing, Occupancy, Property, PropertyType
from app.models.user import Role, User, UserStatus


def dt(s: str) -> datetime:
    """Parse a date string to timezone-aware datetime."""
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


async def seed():
    async with async_session_factory() as db:
        print("🌱 Seeding database...")

        # ── Truncate all tables (cascade) ──
        print("  🗑️  Clearing existing data...")
        await db.execute(text(
            "TRUNCATE notifications, payments, jobs, inspections, "
            "kyc_documents, disputes, bank_accounts, messages, audit_logs, "
            "properties, users CASCADE"
        ))
        await db.flush()

        # ─────────────────── USERS ───────────────────

        pwd_owner = hash_password("Owner@123")
        pwd_tenant = hash_password("Tenant@123")
        pwd_provider = hash_password("Provider@123")
        pwd_admin = hash_password("Admin@123")

        users_data = [
            # Owner
            User(id="owner_rajesh_001", email="rajesh.mehta@gmail.com", phone="+971501234567",
                 password_hash=pwd_owner, name="Rajesh Mehta", initials="RM",
                 location="Dubai, UAE", roles=["owner"], active_role=Role.OWNER,
                 status=UserStatus.VERIFIED, kyc_progress=85, portfolio_value="₹12.5 Cr"),
            # Tenants
            User(id="tenant_priya_001", email="priya.sharma@gmail.com", phone="+919876543299",
                 password_hash=pwd_tenant, name="Priya Sharma", initials="PS",
                 location="Chennai, India", roles=["tenant"], active_role=Role.TENANT,
                 status=UserStatus.VERIFIED, kyc_progress=100),
            User(id="tenant_arjun_002", email="arjun.nair@gmail.com", phone="+919876500001",
                 password_hash=pwd_tenant, name="Arjun Nair", initials="AN",
                 location="Chennai, India", roles=["tenant"], active_role=Role.TENANT,
                 status=UserStatus.VERIFIED, kyc_progress=100),
            User(id="tenant_meera_003", email="meera.iyer@gmail.com", phone="+919876500002",
                 password_hash=pwd_tenant, name="Meera Iyer", initials="MI",
                 location="Chennai, India", roles=["tenant"], active_role=Role.TENANT,
                 status=UserStatus.PENDING, kyc_progress=60),
            # Providers
            User(id="provider_kumar_001", email="kumar.electric@gmail.com", phone="+919876500003",
                 password_hash=pwd_provider, name="Kumar Electricals", initials="KE",
                 location="Chennai, India", roles=["provider"], active_role=Role.PROVIDER,
                 status=UserStatus.VERIFIED, kyc_progress=100,
                 specialization="Plumbing & Electrical", rating=4.8, total_jobs=342),
            User(id="provider_ravi_002", email="ravi.paint@gmail.com", phone="+919876500004",
                 password_hash=pwd_provider, name="Ravi Painters", initials="RP",
                 location="Chennai, India", roles=["provider"], active_role=Role.PROVIDER,
                 status=UserStatus.VERIFIED, kyc_progress=100,
                 specialization="Painting & Carpentry", rating=4.5, total_jobs=128),
            User(id="provider_deepa_003", email="deepa.clean@gmail.com", phone="+919876500005",
                 password_hash=pwd_provider, name="Deepa Home Services", initials="DH",
                 location="Chennai, India", roles=["provider"], active_role=Role.PROVIDER,
                 status=UserStatus.AWAITING_REVIEW, kyc_progress=40,
                 specialization="Cleaning & Pest Control", rating=0, total_jobs=0),
            # Admin
            User(id="admin_luxelife_001", email="admin@luxelife.com", phone="+919000000000",
                 password_hash=pwd_admin, name="Admin User", initials="AU",
                 location="Chennai, India", roles=["admin"], active_role=Role.ADMIN,
                 status=UserStatus.VERIFIED, kyc_progress=100),
        ]
        for u in users_data:
            db.add(u)
        await db.flush()
        print(f"  ✅ {len(users_data)} users created")

        # ─────────────────── PROPERTIES (Chennai) ───────────────────

        props_data = [
            Property(
                id="prop_chennai_001", name="Marina Bay Apartments", unit="Flat 12B",
                address="15, Marina Beach Road, Mylapore", city="Chennai",
                state="Tamil Nadu", pincode="600004", type=PropertyType.APARTMENT,
                bhk="3 BHK", sqft=1500, furnishing=Furnishing.FULLY_FURNISHED,
                floor=12, total_floors=20, facing="East",
                rent=45000, security_deposit=135000, maintenance_charges=3000,
                description="A luxurious 3 BHK apartment with panoramic sea views near Marina Beach. Features Italian marble flooring, modular kitchen with chimney, and premium fixtures throughout.",
                images=["https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop",
                         "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600&h=400&fit=crop",
                         "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=600&h=400&fit=crop"],
                occupancy=Occupancy.OCCUPIED, premium=True,
                amenities=["parking", "pool", "gym", "security", "power_backup", "playground"],
                lease_start=dt("2025-12-01"), lease_end=dt("2026-11-30"),
                owner_id="owner_rajesh_001", tenant_id="tenant_priya_001",
            ),
            Property(
                id="prop_chennai_002", name="OMR Tech Park Residency", unit="Unit 7A",
                address="Plot 45, Rajiv Gandhi Salai, Sholinganallur", city="Chennai",
                state="Tamil Nadu", pincode="600119", type=PropertyType.APARTMENT,
                bhk="2 BHK", sqft=1200, furnishing=Furnishing.SEMI_FURNISHED,
                floor=7, total_floors=15, facing="North",
                rent=28000, security_deposit=84000, maintenance_charges=2000,
                description="Modern 2 BHK in the IT corridor. Close to TCS, Infosys, and Zoho campuses. Semi-furnished with wardrobes, geysers, and modular kitchen.",
                images=["https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&h=400&fit=crop"],
                occupancy=Occupancy.OCCUPIED, premium=False,
                amenities=["parking", "gym", "security"],
                lease_start=dt("2025-11-01"), lease_end=dt("2026-10-31"),
                owner_id="owner_rajesh_001", tenant_id="tenant_arjun_002",
            ),
            Property(
                id="prop_chennai_003", name="ECR Beachfront Villa", unit="Villa 5",
                address="12, East Coast Road, Neelankarai", city="Chennai",
                state="Tamil Nadu", pincode="600115", type=PropertyType.VILLA,
                bhk="4 BHK", sqft=3200, furnishing=Furnishing.FULLY_FURNISHED,
                floor=1, total_floors=2, facing="South",
                rent=120000, security_deposit=360000, maintenance_charges=8000,
                description="Exquisite beachfront villa on ECR with private pool, landscaped gardens, and direct beach access. 4 spacious bedrooms, home theatre, and rooftop terrace.",
                images=["https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=600&h=400&fit=crop"],
                occupancy=Occupancy.VACANT, premium=True,
                amenities=["parking", "pool", "gym", "security", "power_backup", "garden"],
                owner_id="owner_rajesh_001", tenant_id=None,
            ),
        ]
        for p in props_data:
            db.add(p)
        await db.flush()
        print(f"  ✅ {len(props_data)} properties created (Chennai)")

        # ─────────────────── PAYMENTS ───────────────────

        payments_data = [
            Payment(id="pay_rent_001", type=PaymentType.RENT, label="Monthly Rent — March 2026",
                    amount=45000, breakdown={"rent": 42000, "maintenance": 3000},
                    status=PaymentStatus.OVERDUE, due_date=dt("2026-03-05"),
                    property_id="prop_chennai_001", tenant_id="tenant_priya_001", owner_id="owner_rajesh_001"),
            Payment(id="pay_rent_002", type=PaymentType.RENT, label="Monthly Rent — March 2026",
                    amount=28000, breakdown={"rent": 26000, "maintenance": 2000},
                    status=PaymentStatus.PAID, due_date=dt("2026-03-01"), paid_date=dt("2026-02-28"),
                    method=PaymentMethod.UPI, reference_id="TXN-20260228-9845",
                    property_id="prop_chennai_002", tenant_id="tenant_arjun_002", owner_id="owner_rajesh_001"),
            Payment(id="pay_service_001", type=PaymentType.SERVICE, label="Plumbing Repair",
                    amount=2070, breakdown={"materials": 570, "labor": 1500},
                    status=PaymentStatus.ESCROWED, paid_date=dt("2026-03-02"),
                    method=PaymentMethod.CARD, reference_id="TXN-20260302-1122",
                    property_id="prop_chennai_001", tenant_id="tenant_priya_001",
                    owner_id="owner_rajesh_001", provider_id="provider_kumar_001"),
            Payment(id="pay_service_002", type=PaymentType.SERVICE, label="Electrical Wiring",
                    amount=4500, breakdown={"materials": 1500, "labor": 3000},
                    status=PaymentStatus.PAID, paid_date=dt("2026-02-20"),
                    method=PaymentMethod.NETBANKING, reference_id="TXN-20260220-3344",
                    property_id="prop_chennai_002", tenant_id="tenant_arjun_002",
                    owner_id="owner_rajesh_001", provider_id="provider_kumar_001"),
        ]
        for p in payments_data:
            db.add(p)
        await db.flush()
        print(f"  ✅ {len(payments_data)} payments created")

        # ─────────────────── JOBS ───────────────────

        jobs_data = [
            Job(id="job_plumb_001", service_type="Plumbing Repair", category="plumbing",
                description="Sink Leak — Kitchen", icon="🔧",
                address="15, Marina Beach Road, Mylapore, Flat 12B",
                tenant_name="Priya Sharma", provider_name="Kumar Electricals",
                status=JobStatus.ACTIVE, scheduled_date=dt("2026-03-06"),
                scheduled_time="10:00 AM - 12:00 PM", estimated_cost={"min": 500, "max": 1500},
                property_id="prop_chennai_001", tenant_id="tenant_priya_001", provider_id="provider_kumar_001"),
            Job(id="job_elec_002", service_type="Electrical Wiring", category="electrical",
                description="Faulty switch panel in master bedroom", icon="⚡",
                address="Plot 45, Rajiv Gandhi Salai, Unit 7A",
                tenant_name="Arjun Nair", provider_name="Kumar Electricals",
                status=JobStatus.COMPLETED, scheduled_date=dt("2026-02-20"),
                scheduled_time="02:00 PM - 04:00 PM", estimated_cost={"min": 400, "max": 1200},
                actual_cost=4500, completed_at=dt("2026-02-20"),
                property_id="prop_chennai_002", tenant_id="tenant_arjun_002", provider_id="provider_kumar_001"),
            Job(id="job_paint_003", service_type="Painting", category="painting",
                description="Full living room repaint — colour: Ivory White", icon="🎨",
                address="15, Marina Beach Road, Mylapore, Flat 12B",
                tenant_name="Priya Sharma", provider_name=None,
                status=JobStatus.SCHEDULED, scheduled_date=dt("2026-03-10"),
                scheduled_time="09:00 AM - 05:00 PM", estimated_cost={"min": 3000, "max": 8000},
                property_id="prop_chennai_001", tenant_id="tenant_priya_001", provider_id=None),
        ]
        for j in jobs_data:
            db.add(j)
        await db.flush()
        print(f"  ✅ {len(jobs_data)} jobs created")

        # ─────────────────── NOTIFICATIONS ───────────────────

        notifs = [
            Notification(id=generate_cuid(), user_id="tenant_priya_001", type="payment",
                         title="Rent Due Reminder", body="Your monthly rent of ₹45,000 for Marina Bay Apartments is due today.",
                         icon="💰", unread=True, action_label="Pay Now", action_target="/payments/pay_rent_001"),
            Notification(id=generate_cuid(), user_id="tenant_priya_001", type="maintenance",
                         title="Service Request Update", body="Plumbing repair for Flat 12B has been scheduled for March 6.",
                         icon="🔧", unread=True),
            Notification(id=generate_cuid(), user_id="tenant_arjun_002", type="payment",
                         title="Payment Confirmed", body="Rent payment of ₹28,000 received for OMR Tech Park Residency.",
                         icon="✅", unread=False),
            Notification(id=generate_cuid(), user_id="owner_rajesh_001", type="payment",
                         title="Rent Collected", body="₹28,000 collected from Arjun Nair for OMR Tech Park Residency.",
                         icon="💰", unread=True, action_label="View Details"),
        ]
        for n in notifs:
            db.add(n)
        await db.flush()
        print(f"  ✅ {len(notifs)} notifications created")

        # ── Commit ──
        await db.commit()
        print("\n🎉 Database seeded successfully!")
        print("\n── Login Credentials ──")
        print("  Owner:    rajesh.mehta@gmail.com / Owner@123")
        print("  Tenant 1: priya.sharma@gmail.com / Tenant@123")
        print("  Tenant 2: arjun.nair@gmail.com   / Tenant@123")
        print("  Tenant 3: meera.iyer@gmail.com   / Tenant@123")
        print("  Provider: kumar.electric@gmail.com / Provider@123")
        print("  Admin:    admin@luxelife.com      / Admin@123")


if __name__ == "__main__":
    asyncio.run(seed())
