from collections import defaultdict
from typing import Dict, List

from sqlalchemy import text

from app.domain.unit_of_work import UnitOfWork
from app.schemas.statistics_schema import (
    BuildingAssessmentSummary,
    CategoryStats,
    LocationStats,
    RegionStats,
)
from app.utils.logger import get_logger


logger = get_logger("statistics_service")


class DashboardStatisticsService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def get_by_category_and_region(self) -> List[CategoryStats]:
        """
        Get hierarchical statistics: Category -> Region -> Building Type -> Good/Bad.
        """
        with self.uow:
            # Get building assessment summaries
            summaries = self._get_building_summaries_data()

            # Group by category and region
            category_data = defaultdict(
                lambda: {
                    "category_name": "",
                    "regions": defaultdict(
                        lambda: {
                            "region_name": "",
                            "stats": self._empty_location_stats(),
                        }
                    ),
                }
            )

            # First pass: collect region and category names, and aggregate
            # stats
            for summary in summaries:
                cat_id = summary["category_id"]
                region_id = summary["region_id"]

                # Store names
                if not category_data[cat_id]["category_name"]:
                    category_data[cat_id]["category_name"] = summary[
                        "category_name"
                    ]
                if not category_data[cat_id]["regions"][region_id][
                    "region_name"
                ]:
                    category_data[cat_id]["regions"][region_id][
                        "region_name"
                    ] = summary["region_name"]

                # Aggregate statistics
                stats = category_data[cat_id]["regions"][region_id]["stats"]
                stats["total_locations"] += 1

                status = summary["status"]
                is_good = summary["is_good"]

                if status == "new":
                    stats["new_buildings"]["total"] += 1
                    if is_good:
                        stats["new_buildings"]["good"] += 1
                    else:
                        stats["new_buildings"]["bad"] += 1
                elif status == "old":
                    stats["old_buildings"]["total"] += 1
                    if is_good:
                        stats["old_buildings"]["good"] += 1
                    else:
                        stats["old_buildings"]["bad"] += 1
                elif status == "active":
                    # Treat active status as old buildings
                    # (existing/operational)
                    stats["old_buildings"]["total"] += 1
                    if is_good:
                        stats["old_buildings"]["good"] += 1
                    else:
                        stats["old_buildings"]["bad"] += 1
                elif status == "under_construction":
                    stats["under_construction"] += 1
                elif status == "inactive":
                    stats["inactive"] += 1
                elif status == "closed":
                    stats["closed"] += 1

            # Convert to response format
            result = []
            for cat_id, cat_data in category_data.items():
                # Calculate total stats for category
                total_stats = self._empty_location_stats()
                regions_list = []

                for region_id, region_data in cat_data["regions"].items():
                    region_stats = LocationStats(**region_data["stats"])
                    regions_list.append(
                        RegionStats(
                            region_id=region_id,
                            region_name=region_data["region_name"],
                            stats=region_stats,
                        )
                    )

                    # Add to total
                    self._add_stats(total_stats, region_data["stats"])

                result.append(
                    CategoryStats(
                        category_id=cat_id,
                        category_name=cat_data["category_name"],
                        regions=regions_list,
                        total_stats=LocationStats(**total_stats),
                    )
                )

            return result

    def get_building_assessment_summaries(
        self,
    ) -> List[BuildingAssessmentSummary]:
        """Get building assessment summaries for classification."""
        with self.uow:
            summaries = self._get_building_summaries_data()
            return [
                BuildingAssessmentSummary(**summary) for summary in summaries
            ]

    def get_category_region_details(
        self, category_id: int, region_id: int
    ) -> LocationStats:
        """Get detailed statistics for a specific category and region."""
        with self.uow:
            summaries = self._get_building_summaries_data()

            # Filter by category and region
            filtered = [
                s
                for s in summaries
                if s["category_id"] == category_id
                and s["region_id"] == region_id
            ]

            stats = self._empty_location_stats()

            for summary in filtered:
                stats["total_locations"] += 1
                status = summary["status"]
                is_good = summary["is_good"]

                if status == "new":
                    stats["new_buildings"]["total"] += 1
                    if is_good:
                        stats["new_buildings"]["good"] += 1
                    else:
                        stats["new_buildings"]["bad"] += 1
                elif status == "old":
                    stats["old_buildings"]["total"] += 1
                    if is_good:
                        stats["old_buildings"]["good"] += 1
                    else:
                        stats["old_buildings"]["bad"] += 1
                elif status == "active":
                    # Treat active status as old buildings
                    # (existing/operational)
                    stats["old_buildings"]["total"] += 1
                    if is_good:
                        stats["old_buildings"]["good"] += 1
                    else:
                        stats["old_buildings"]["bad"] += 1
                elif status == "under_construction":
                    stats["under_construction"] += 1
                elif status == "inactive":
                    stats["inactive"] += 1
                elif status == "closed":
                    stats["closed"] += 1

            return LocationStats(**stats)

    def _get_building_summaries_data(self) -> List[Dict]:
        """Get raw building summaries data from database."""
        query = text(
            """
            WITH RECURSIVE category_hierarchy AS (
                -- Base case: get all categories
                SELECT
                    category_id,
                    category_name,
                    parent_category_id,
                    category_id as root_category_id,
                    category_name as root_category_name
                FROM category
                WHERE parent_category_id IS NULL

                UNION ALL

                -- Recursive case: get children and their root
                SELECT
                    c.category_id,
                    c.category_name,
                    c.parent_category_id,
                    ch.root_category_id,
                    ch.root_category_name
                FROM category c
                INNER JOIN category_hierarchy ch ON c.parent_category_id = ch.category_id
            )
            SELECT
                l.location_id,
                l.location_name,
                l.status,
                l.region_id,
                ch.root_category_id as category_id,
                r.region_name,
                ch.root_category_name as category_name,
                COALESCE(AVG(CAST(lsa.overall_score AS FLOAT)), 0) as average_score,
                COUNT(lsa.assessment_id) as total_assessments,
                CASE
                    WHEN COALESCE(AVG(CAST(lsa.overall_score AS FLOAT)), 0) >= 7.0 THEN true
                    ELSE false
                END as is_good
            FROM locations l
            LEFT JOIN region r ON l.region_id = r.region_id
            LEFT JOIN category_hierarchy ch ON l.category_id = ch.category_id
            LEFT JOIN location_set_assessments lsa ON l.location_id::text = lsa.location_id::text
                AND lsa.status = 'verified'
            WHERE ch.root_category_id IS NOT NULL
            GROUP BY l.location_id, l.location_name, l.status, l.region_id, ch.root_category_id, r.region_name, ch.root_category_name
            ORDER BY ch.root_category_name, r.region_name, l.location_name
        """
        )

        result = self.uow.db.execute(query)
        return [
            {
                "location_id": row.location_id,
                "location_name": row.location_name,
                "status": row.status,
                "region_id": row.region_id,
                "category_id": row.category_id,
                "region_name": row.region_name,
                "category_name": row.category_name,
                "average_score": (
                    float(row.average_score) if row.average_score else None
                ),
                "total_assessments": int(row.total_assessments),
                "is_good": bool(row.is_good),
            }
            for row in result
        ]

    def _empty_location_stats(self) -> Dict:
        """Create empty location stats dictionary."""
        return {
            "total_locations": 0,
            "new_buildings": {"total": 0, "good": 0, "bad": 0},
            "old_buildings": {"total": 0, "good": 0, "bad": 0},
            "under_construction": 0,
            "inactive": 0,
            "closed": 0,
        }

    def _add_stats(self, target: Dict, source: Dict):
        """Add source stats to target stats."""
        target["total_locations"] += source["total_locations"]
        target["new_buildings"]["total"] += source["new_buildings"]["total"]
        target["new_buildings"]["good"] += source["new_buildings"]["good"]
        target["new_buildings"]["bad"] += source["new_buildings"]["bad"]
        target["old_buildings"]["total"] += source["old_buildings"]["total"]
        target["old_buildings"]["good"] += source["old_buildings"]["good"]
        target["old_buildings"]["bad"] += source["old_buildings"]["bad"]
        target["under_construction"] += source["under_construction"]
        target["inactive"] += source["inactive"]
        target["closed"] += source["closed"]
