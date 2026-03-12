"""
LuxeLife API — Property service.

Business logic for property CRUD, search, and filtering.
All database operations use the async session passed in.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models import generate_cuid
from app.models.property import Furnishing, Occupancy, Property, PropertyType
from app.models.user import User
from app.schemas.property import property_to_response


class PropertyService:
    """Handles property operations."""

    @staticmethod
    async def create(
        db: AsyncSession,
        owner: User,
        **data,
    ) -> dict:
        """Create a new property listing."""
        prop = Property(
            id=generate_cuid(),
            name=data["name"],
            unit=data["unit"],
            address=data["address"],
            city=data["city"],
            state=data["state"],
            pincode=data["pincode"],
            type=PropertyType(data["type"]),
            bhk=data["bhk"],
            sqft=data["sqft"],
            furnishing=Furnishing(data["furnishing"]),
            floor=data["floor"],
            total_floors=data["total_floors"],
            facing=data.get("facing"),
            rent=data["rent"],
            security_deposit=data["security_deposit"],
            maintenance_charges=data["maintenance_charges"],
            description=data.get("description"),
            images=data.get("images", []),
            premium=data.get("premium", False),
            amenities=data.get("amenities", []),
            owner_id=owner.id,
        )
        db.add(prop)
        await db.flush()
        return property_to_response(prop)

    @staticmethod
    async def get_by_id(db: AsyncSession, property_id: str) -> dict:
        """Get a property by ID."""
        result = await db.execute(
            select(Property).where(Property.id == property_id)
        )
        prop = result.scalar_one_or_none()
        if not prop:
            raise NotFoundError("Property")
        return property_to_response(prop)

    @staticmethod
    async def update(
        db: AsyncSession,
        property_id: str,
        user: User,
        **data,
    ) -> dict:
        """Update a property. Only the owner or admin can update."""
        result = await db.execute(
            select(Property).where(Property.id == property_id)
        )
        prop = result.scalar_one_or_none()
        if not prop:
            raise NotFoundError("Property")

        # Permission check
        if prop.owner_id != user.id and user.active_role.value != "admin":
            raise ForbiddenError("You can only update your own properties")

        # Apply partial updates
        updatable = [
            "name", "address", "rent", "security_deposit",
            "maintenance_charges", "description", "premium",
            "amenities", "images", "tenant_id",
            "lease_start", "lease_end",
        ]
        for field in updatable:
            if field in data and data[field] is not None:
                setattr(prop, field, data[field])

        if "furnishing" in data and data["furnishing"] is not None:
            prop.furnishing = Furnishing(data["furnishing"])
        if "occupancy" in data and data["occupancy"] is not None:
            prop.occupancy = Occupancy(data["occupancy"])

        await db.flush()
        return property_to_response(prop)

    @staticmethod
    async def delete(
        db: AsyncSession, property_id: str, user: User
    ) -> dict:
        """Soft-delete a property. Only the owner or admin can delete."""
        result = await db.execute(
            select(Property).where(Property.id == property_id)
        )
        prop = result.scalar_one_or_none()
        if not prop:
            raise NotFoundError("Property")

        if prop.owner_id != user.id and user.active_role.value != "admin":
            raise ForbiddenError("You can only delete your own properties")

        await db.delete(prop)
        await db.flush()
        return {"message": "Property deleted successfully"}

    @staticmethod
    async def search(
        db: AsyncSession,
        *,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
        city: str | None = None,
        type: str | None = None,
        furnishing: str | None = None,
        occupancy: str | None = None,
        min_rent: int | None = None,
        max_rent: int | None = None,
        bhk: str | None = None,
        premium: bool | None = None,
        owner_id: str | None = None,
        tenant_id: str | None = None,
        sort: str = "-created_at",
    ) -> tuple[list[dict], int]:
        """
        Search and filter properties with pagination.

        Supports text search across name, address, city, and description.
        """
        query = select(Property)

        # ── Filters ──
        if city:
            query = query.where(Property.city.ilike(f"%{city}%"))
        if type:
            query = query.where(Property.type == PropertyType(type))
        if furnishing:
            query = query.where(Property.furnishing == Furnishing(furnishing))
        if occupancy:
            query = query.where(Property.occupancy == Occupancy(occupancy))
        if min_rent is not None:
            query = query.where(Property.rent >= min_rent)
        if max_rent is not None:
            query = query.where(Property.rent <= max_rent)
        if bhk:
            query = query.where(Property.bhk.ilike(f"%{bhk}%"))
        if premium is not None:
            query = query.where(Property.premium == premium)
        if owner_id:
            query = query.where(Property.owner_id == owner_id)
        if tenant_id:
            query = query.where(Property.tenant_id == tenant_id)

        # ── Text Search ──
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Property.name.ilike(pattern),
                    Property.address.ilike(pattern),
                    Property.city.ilike(pattern),
                    Property.description.ilike(pattern),
                )
            )

        # ── Count ──
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # ── Sort ──
        if sort.startswith("-"):
            col = getattr(Property, sort[1:], Property.created_at)
            query = query.order_by(col.desc())
        else:
            col = getattr(Property, sort, Property.created_at)
            query = query.order_by(col.asc())

        # ── Paginate ──
        query = query.offset((page - 1) * limit).limit(limit)

        result = await db.execute(query)
        properties = result.scalars().all()

        return [property_to_response(p) for p in properties], total

    @staticmethod
    async def get_owner_properties(
        db: AsyncSession, owner_id: str
    ) -> list[dict]:
        """Get all properties owned by a user."""
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Property)
            .options(selectinload(Property.tenant))
            .where(Property.owner_id == owner_id)
            .order_by(Property.created_at.desc())
        )
        props = []
        for p in result.scalars().all():
            d = property_to_response(p)
            d["tenant_name"] = p.tenant.name if p.tenant else None
            props.append(d)
        return props

    @staticmethod
    async def get_tenant_property(
        db: AsyncSession, tenant_id: str
    ) -> list[dict]:
        """Get properties where the user is a tenant."""
        result = await db.execute(
            select(Property)
            .where(Property.tenant_id == tenant_id)
            .order_by(Property.created_at.desc())
        )
        return [property_to_response(p) for p in result.scalars().all()]
