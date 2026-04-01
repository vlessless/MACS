"""Mappers to bridge Infrastructure models and Domain entities without leakage."""

from datetime import UTC, datetime
from typing import Any

from macs.domain.entities import PostMortemReport, Task
from macs.infrastructure.persistence.models import TaskTable


class DomainMapper:
    """Strict mapper for converting between DB models and Domain Entities.

    Reasoning:
        Explicit mapping prevents SQLAlchemy internal state from leaking into
        the Domain layer and ensures Pydantic validation is triggered.
        Prohibits .model_dump() to maintain strict control over JSONB structure.
    """

    @staticmethod
    def to_domain_task(table: TaskTable) -> Task:
        """Converts a SQLAlchemy TaskTable to a Domain Task entity.

        Args:
            table: The database model instance.

        Returns:
            Task: A validated Domain Entity.
        """
        post_mortem = DomainMapper._map_pm_to_domain(table.post_mortem_report)

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
        """Converts a Domain Task entity to a dictionary for SQLAlchemy.

        Args:
            entity: The Domain Entity.

        Returns:
            dict[str, Any]: A flat dictionary of table columns.
        """
        pm_data = DomainMapper._map_pm_to_persistence(entity.post_mortem_report)

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

    @staticmethod
    def _map_pm_to_domain(data: dict[str, Any] | None) -> PostMortemReport | None:
        """Safely maps JSONB data to a PostMortemReport entity.

        Args:
            data: Raw dictionary from JSONB column.

        Returns:
            PostMortemReport | None: The domain entity or None.
        """
        if not data:
            return None

        # Fix: Parse the ISO string back to datetime to satisfy strict typing
        raw_date = data.get("generated_at")
        parsed_date: datetime
        if isinstance(raw_date, str):
            try:
                parsed_date = datetime.fromisoformat(raw_date)
            except (ValueError, TypeError):
                parsed_date = datetime.now(UTC)
        else:
            parsed_date = datetime.now(UTC)

        return PostMortemReport(
            hypothesis=str(data.get("hypothesis", "No hypothesis provided")),
            observed_error=str(data.get("observed_error", "No error recorded")),
            blocker=str(data.get("blocker", "Unknown blocker")),
            generated_at=parsed_date,
        )

    @staticmethod
    def _map_pm_to_persistence(
        report: PostMortemReport | None,
    ) -> dict[str, Any] | None:
        """Explicitly maps a PostMortemReport to a persistence dictionary.

        Args:
            report: The domain report entity.

        Returns:
            dict[str, Any] | None: The serialized data for JSONB.
        """
        if not report:
            return None

        return {
            "hypothesis": report.hypothesis,
            "observed_error": report.observed_error,
            "blocker": report.blocker,
            "generated_at": report.generated_at.isoformat(),
        }
