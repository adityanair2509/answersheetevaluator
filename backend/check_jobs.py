
import asyncio
from db.session import AsyncSessionLocal
from sqlalchemy import select
from db.models import ProcessingJob

async def check_jobs():
    print("Checking last 5 processing jobs...")
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ProcessingJob).order_by(ProcessingJob.id.desc()).limit(5))
        jobs = res.scalars().all()
        if not jobs:
            print("No jobs found in database.")
            return
        for j in jobs:
            print(f"Job ID {j.id}: Status={j.status}, Stage={j.stage}, Error={j.error_message}")

if __name__ == '__main__':
    asyncio.run(check_jobs())
