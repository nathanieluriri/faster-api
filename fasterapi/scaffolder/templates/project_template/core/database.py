import os

from dotenv import load_dotenv

load_dotenv()

# mongodb, postgres, or supabase (Postgres through Supabase's connection pooler)
DB_TYPE = (os.getenv("DB_TYPE") or "mongodb").strip().lower()

if DB_TYPE == "mongodb":
    from motor.motor_asyncio import AsyncIOMotorClient

    MONGO_URL = os.getenv("MONGO_URL") or "mongodb://localhost:27017"
    DB_NAME = os.getenv("DB_NAME") or "app"

    client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]

    async def ping_database() -> None:
        await client.admin.command("ping")

elif DB_TYPE in {"postgres", "postgresql", "supabase"}:
    from core.postgres_store import PostgresDocumentStore

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError(f"DATABASE_URL is required when DB_TYPE={DB_TYPE}")

    db = PostgresDocumentStore(DATABASE_URL)

    async def ping_database() -> None:
        await db.ping()

else:
    raise ValueError("Unsupported DB_TYPE. Use 'mongodb', 'postgres' or 'supabase'.")
