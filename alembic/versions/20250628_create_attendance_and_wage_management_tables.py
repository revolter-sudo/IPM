"""create attendance and wage management tables

Revision ID: 20250628_attendance_wage
Revises: 20250625_inquiry_data
Create Date: 2025-06-28 21:15:00.000000

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import UUID
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250628_attendance_wage'
down_revision: Union[str, None] = '20250625_inquiry_data'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create self_attendance table
    op.create_table(
        'self_attendance',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
        sa.Column('attendance_date', sa.Date, nullable=False),
        
        # Punch In Details
        sa.Column('punch_in_time', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('punch_in_latitude', sa.Float, nullable=False),
        sa.Column('punch_in_longitude', sa.Float, nullable=False),
        sa.Column('punch_in_location_address', sa.Text, nullable=True),
        
        # Punch Out Details (can be NULL if user forgets to punch out)
        sa.Column('punch_out_time', sa.TIMESTAMP, nullable=True),
        sa.Column('punch_out_latitude', sa.Float, nullable=True),
        sa.Column('punch_out_longitude', sa.Float, nullable=True),
        sa.Column('punch_out_location_address', sa.Text, nullable=True),
        
        sa.Column('assigned_projects', sa.Text, nullable=True),  # JSON string
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )

    # Create project_attendance table
    op.create_table(
        'project_attendance',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('site_engineer_id', UUID(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.Column('sub_contractor_id', UUID(as_uuid=True), sa.ForeignKey('person.uuid'), nullable=False),
        sa.Column('no_of_labours', sa.Integer, nullable=False),
        sa.Column('attendance_date', sa.Date, nullable=False),
        sa.Column('marked_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('latitude', sa.Float, nullable=False),
        sa.Column('longitude', sa.Float, nullable=False),
        sa.Column('location_address', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )

    # Create project_daily_wage table
    op.create_table(
        'project_daily_wage',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.uuid'), nullable=False),
        sa.Column('daily_wage_rate', sa.Float, nullable=False),
        sa.Column('effective_date', sa.Date, nullable=False),
        sa.Column('configured_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.uuid'), nullable=False),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )

    # Create project_attendance_wage table
    op.create_table(
        'project_attendance_wage',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uuid', UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('project_attendance_id', UUID(as_uuid=True), sa.ForeignKey('project_attendance.uuid'), nullable=False),
        sa.Column('project_daily_wage_id', UUID(as_uuid=True), sa.ForeignKey('project_daily_wage.uuid'), nullable=False),
        sa.Column('no_of_labours', sa.Integer, nullable=False),
        sa.Column('daily_wage_rate', sa.Float, nullable=False),
        sa.Column('total_wage_amount', sa.Float, nullable=False),
        sa.Column('calculated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now(), nullable=False),
    )

    # Add constraints
    op.create_unique_constraint(
        'unique_user_date_self_attendance',
        'self_attendance',
        ['user_id', 'attendance_date', 'is_deleted']
    )
    
    op.create_unique_constraint(
        'unique_project_effective_date',
        'project_daily_wage',
        ['project_id', 'effective_date', 'is_deleted']
    )
    
    op.create_unique_constraint(
        'unique_attendance_wage',
        'project_attendance_wage',
        ['project_attendance_id', 'is_deleted']
    )

    # Add check constraints
    op.create_check_constraint(
        'check_no_of_labours_positive',
        'project_attendance',
        'no_of_labours > 0'
    )
    
    op.create_check_constraint(
        'check_daily_wage_rate_positive',
        'project_daily_wage',
        'daily_wage_rate > 0'
    )


def downgrade():
    # Drop tables in reverse order due to foreign key dependencies
    op.drop_table('project_attendance_wage')
    op.drop_table('project_daily_wage')
    op.drop_table('project_attendance')
    op.drop_table('self_attendance')
