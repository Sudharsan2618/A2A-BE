import asyncio
from app.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as db:
        for table in ["users", "properties", "payments", "jobs", "notifications"]:
            r = await db.execute(text(f"SELECT count(*) FROM {table}"))
            print(f"  {table}: {r.scalar()}")

asyncio.run(check())
