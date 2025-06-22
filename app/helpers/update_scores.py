import sys

from sqlalchemy import text

from app.core.database import UnitOfWork
from app.services.location_service import LocationService


# !/usr/bin/env python3


sys.path.append("app")


def update_all_accessibility_scores():
    """Update accessibility_score for all locations based on their verified assessments."""
    with UnitOfWork() as uow:
        location_service = LocationService(uow)

        # Get all locations that have verified assessments
        result = uow.db.execute(
            text(
                """
            SELECT DISTINCT location_id
            FROM locationsetassessments
            WHERE status = 'verified'
            AND overall_score IS NOT NULL
        """
            )
        )
        locations = result.fetchall()

        print(f"Found {len(locations)} locations with verified assessments")

        for (location_id,) in locations:
            print(f"Updating accessibility score for location {location_id}")
            try:
                new_score = location_service.update_accessibility_score(
                    location_id
                )
                print(
                    f"Successfully updated location {location_id} with score: {new_score}")
            except Exception as e:
                print(f"Error updating location {location_id}: {e}")


if __name__ == "__main__":
    update_all_accessibility_scores()
