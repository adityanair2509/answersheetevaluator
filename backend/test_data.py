import asyncio
import sys

sys.path.insert(0, r"D:\PROJECTS\AUTO_SHEET_EVALUATOR\backend")

from db.session import engine
from db.models import Exam, Question, AnswerSheet, ExtractedAnswer, EvaluationResult
from packages.common.enums import ExamStatus, SheetStatus, ReviewStatus, ConfidenceBand
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async def create_test_data():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Create Exam
        exam = Exam(
            title='Test Exam',
            course_code='CS101',
            status=ExamStatus.ACCEPTING_UPLOADS
        )
        session.add(exam)
        await session.flush()
        
        # Create Question
        question = Question(
            exam_id=exam.id,
            question_number=1,
            question_text='What is 2+2?',
            expected_answer='4',
            max_marks=10.0
        )
        session.add(question)
        await session.flush()
        
        # Create Answer Sheet
        sheet = AnswerSheet(
            exam_id=exam.id,
            student_roll='TEST-001',
            original_filename='test.pdf',
            page_count=1,
            status=SheetStatus.EVALUATED
        )
        session.add(sheet)
        await session.flush()
        
        # Create Extracted Answer
        extracted = ExtractedAnswer(
            answer_sheet_id=sheet.id,
            question_number=1,
            raw_text='I think it is 4',
            confidence=0.8
        )
        session.add(extracted)
        await session.flush()
        
        # Create Evaluation Result (NEEDS_REVIEW)
        eval_res = EvaluationResult(
            extracted_answer_id=extracted.id,
            score=8.0,
            max_score=10.0,
            reasoning='Good enough.',
            confidence=0.8,
            confidence_band=ConfidenceBand.MEDIUM,
            review_status=ReviewStatus.NEEDS_REVIEW
        )
        session.add(eval_res)
        await session.commit()
        
        print("Created Exam ID:", exam.id)
        print("Created Sheet ID:", sheet.id)
        print("Created Eval ID:", eval_res.id)

if __name__ == '__main__':
    asyncio.run(create_test_data())
