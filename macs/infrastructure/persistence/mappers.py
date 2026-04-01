"""Mappers to bridge Infrastructure models and Domain entities without leakage."""

from typing import Any

from macs.domain.entities import PostMortemReport, Task
from macs.infrastructure.persistence.models import TaskTable


class DomainMapper:
    """Strict mapper for converting between DB models and Domain Entities.

    Reasoning:
        Explicit mapping prevents SQLAlchemy internal state from leaking into
        the Domain layer and ensures Pydantic validation is triggered.
    """

    @staticmethod
    def to_domain_task(table: TaskTable) -> Task:
        """Converts a SQLAlchemy TaskTable to a Domain Task entity.

        Args:
            table: The database model instance.

        Returns:
            Task: A validated Domain Entity.
        """
        post_mortem = None
        if table.post_mortem_report:
            post_mortem = PostMortemReport(
                hypothesis=table.post_mortem_report["hypothesis"],
                observed_error=table.post_mortem_report["observed_error"],
                blocker=table.post_mortem_report["blocker"],
                generated_at=table.post_mortem_report["generated_at"],
            )

        # Explicit construction to avoid __dict__ leakage
        return Task(
            id=table.id,
            title=table.title,
            description=table.description,
            status=table.status,
            assigned_agent_id=table.assigned_agent_id,
            strike_count=table.strike_count,
            thought_trace=table.thought_trace,
            post_mortem_report=post_mortem,
            created_at=table.created_at,
            updated_at=table.updated_at,
        )

    @staticmethod
    def to_table_task(entity: Task) -> dict[str, Any]:
        """Converts a Domain Task entity to a dictionary for SQLAlchemy update/insert.

        Args:
            entity: The Domain Entity.

        Returns:
            dict[str, Any]: A flat dictionary of table columns.
        """
        pm_data = None
        if entity.post_mortem_report:
            pm_data = entity.post_mortem_report.model_dump()

        return {
            "id": entity.id,
            "title": entity.title,
            "description": entity.description,
            "status": entity.status,
            "assigned_agent_id": entity.assigned_agent_id,
            "strike_count": entity.strike_count,
            "thought_trace": entity.thought_trace,
            "post_mortem_report": pm_data,
            "updated_at": entity.updated_at,
        }
