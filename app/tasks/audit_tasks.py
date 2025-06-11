from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user_model import User


class AuditTasks:
    @staticmethod
    def log_action(
        db: Session,
        table_name: str,
        record_id: str,
        operation: str,
        changed_data: dict,
        performed_by: str | None = None,
    ) -> None:
        # In a full implementation, insert a record into an AuditLogs table.
        # For this example, we simply print a log.
        print(
            f"Audit Log -> Table: {table_name}, Record: {record_id}, Operation: {operation}, Data: {changed_data}, By: {performed_by}"
        )


# Example usage:
# AuditTasks.log_action(db, "users", user.user_id, "UPDATE", {"field": "value"}, "admin_user_id")
