#!/usr/bin/env python3
from sqlalchemy import text
from core.database import UnitOfWork
from services.assessment_service import AssessmentService

def fix_all_scores():
    with UnitOfWork() as uow:
        service = AssessmentService(uow)
        
        # Get all verified assessments with null scores
        result = uow.db.execute(text(
            "SELECT assessment_id FROM locationsetassessments WHERE status = 'verified' AND overall_score IS NULL"
        ))
        assessments = result.fetchall()
        
        print(f"Found {len(assessments)} verified assessments with null scores")
        
        for (assessment_id,) in assessments:
            print(f'Fixing assessment {assessment_id}')
            try:
                service.fix_assessment_score(assessment_id)
                print(f'Successfully fixed assessment {assessment_id}')
            except Exception as e:
                print(f'Error fixing assessment {assessment_id}: {e}')

if __name__ == "__main__":
    fix_all_scores() 