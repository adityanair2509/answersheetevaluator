from db.session import AsyncSessionLocal
from db.models import SheetPage
from sqlalchemy import select
import asyncio
import os

async def check_pages():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SheetPage))
        pages = result.scalars().all()
        print(f"Total pages in DB: {len(pages)}")
        for p in pages:
            exists = os.path.exists(p.file_path)
            print(f"ID: {p.id}, Path: {p.file_path}, Exists: {exists}")

if __name__ == "__main__":
    asyncio.run(check_pages())
