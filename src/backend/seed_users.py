#!/usr/bin/env python
"""Seed script — run inside api container: python seed_users.py"""

import asyncio
import os
import uuid

import bcrypt as _bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://", 1)

USERS = [
    {"email": "frank@learnflow.local",     "password": "changeme1", "role": "knowledge_owner"},
    {"email": "niklaus@learnflow.local",   "password": "changeme2", "role": "admin"},
    {"email": "reto@learnflow.local",      "password": "changeme3", "role": "knowledge_owner"},
    {"email": "christoph@learnflow.local", "password": "changeme4", "role": "knowledge_owner"},
    {"email": "stefan@learnflow.local",    "password": "changeme5", "role": "knowledge_owner"},
    {"email": "lara@learnflow.local",      "password": "changeme6", "role": "learner"},
]

async def seed() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        for u in USERS:
            result = await db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": u["email"]},
            )
            existing = result.scalar_one_or_none()
            hashed = _bcrypt.hashpw(u["password"].encode(), _bcrypt.gensalt()).decode()

            if existing:
                await db.execute(
                    text("UPDATE users SET hashed_password = :pw, role = :role WHERE email = :email"),  # noqa: E501
                    {"pw": hashed, "role": u["role"], "email": u["email"]},
                )
                print(f"  updated  {u['email']} ({u['role']})")
            else:
                await db.execute(
                    text("""
                        INSERT INTO users (id, email, hashed_password, role, is_active)
                        VALUES (:id, :email, :pw, :role, true)
                    """),
                    {"id": str(uuid.uuid4()), "email": u["email"], "pw": hashed, "role": u["role"]},
                )
                print(f"  created  {u['email']} ({u['role']})")

        await db.commit()

    await engine.dispose()
    print("Done.")

asyncio.run(seed())
