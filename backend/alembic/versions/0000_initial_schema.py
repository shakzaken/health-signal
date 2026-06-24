"""initial schema

Revision ID: 0000_initial_schema
Revises:
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0000_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "blood_test", "lab_report", "symptom_note", "supplement_list",
                "diet_note", "doctor_summary", "journal",
                name="documenttype", create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column(
            "processing_status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="processingstatus", create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "lab_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("test_date", sa.Date(), nullable=False),
        sa.Column("lab_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "lab_markers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lab_result_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("reference_low", sa.Float(), nullable=True),
        sa.Column("reference_high", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "normal", "low", "high", "borderline_low", "borderline_high",
                name="markerstatus", create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lab_result_id"], ["lab_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "supplement_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("dosage", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Date(), nullable=True),
        sa.Column("stopped_at", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "symptom_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("symptom_name", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("mild", "moderate", "severe", name="symptomseverity", create_constraint=True),
            nullable=True,
        ),
        sa.Column("occurred_at", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "lab_result", "symptom", "supplement_change", "diet_change", "note",
                name="eventtype", create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reference_id", sa.UUID(), nullable=False),
        sa.Column("reference_table", sa.Text(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("timeline_events")
    op.drop_table("symptom_entries")
    op.drop_table("supplement_entries")
    op.drop_table("lab_markers")
    op.drop_table("lab_results")
    op.drop_table("documents")
