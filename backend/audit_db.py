from sqlalchemy import select
from db.session import AsyncSessionLocal
from db.models import Exam, Question
import asyncio

async def check_db():
    async with AsyncSessionLocal() as session:
        # Check Exams
        res = await session.execute(select(Exam))
        exams = res.scalars().all()
        print(f"Exams found: {len(exams)}")
        for e in exams:
            print(f" - Exam ID: {e.id}, Title: {e.title}")

            # Check Questions for each exam
            q_res = await session.execute(select(Question).where(Question.exam_id == e.id))
            questions = q_res.scalars().all()
            print(f"   Questions: {len(questions)}")
            for q in questions:
                print(f"     Q{q.question_number}: {q.question_text[:30]}... (Max: {q.max_marks})")

if __name__ == "__main__":
    asyncio.run(check_db())
