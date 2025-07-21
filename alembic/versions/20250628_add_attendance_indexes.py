"""add attendance and wage management indexes

Revision ID: 20250628_attendance_indexes
Revises: 20250628_attendance_wage
Create Date: 2025-06-28 21:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250628_attendance_indexes'
down_revision: Union[str, None] = '20250628_attendance_wage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Self Attendance Indexes
    op.create_index(
        'idx_self_attendance_user_date',
        'self_attendance',
        ['user_id', 'attendance_date']
    )
    
    op.create_index(
        'idx_self_attendance_date',
        'self_attendance',
        ['attendance_date']
    )
    
    op.create_index(
        'idx_self_attendance_punch_in_location',
        'self_attendance',
        ['punch_in_latitude', 'punch_in_longitude']
    )
    
    op.create_index(
        'idx_self_attendance_punch_times',
        'self_attendance',
        ['punch_in_time', 'punch_out_time']
    )

    # Project Attendance Indexes
    op.create_index(
        'idx_project_attendance_project_date',
        'project_attendance',
        ['project_id', 'attendance_date']
    )
    
    op.create_index(
        'idx_project_attendance_engineer_date',
        'project_attendance',
        ['site_engineer_id', 'attendance_date']
    )
    
    op.create_index(
        'idx_project_attendance_contractor',
        'project_attendance',
        ['sub_contractor_id']
    )

    # Project Daily Wage Indexes
    op.create_index(
        'idx_project_daily_wage_project',
        'project_daily_wage',
        ['project_id']
    )
    
    op.create_index(
        'idx_project_daily_wage_effective_date',
        'project_daily_wage',
        ['effective_date']
    )
    
    op.create_index(
        'idx_project_daily_wage_project_date',
        'project_daily_wage',
        ['project_id', 'effective_date']
    )

    # Project Attendance Wage Indexes
    op.create_index(
        'idx_project_attendance_wage_attendance',
        'project_attendance_wage',
        ['project_attendance_id']
    )
    
    op.create_index(
        'idx_project_attendance_wage_daily_wage',
        'project_attendance_wage',
        ['project_daily_wage_id']
    )
    
    op.create_index(
        'idx_project_attendance_wage_calculated_at',
        'project_attendance_wage',
        ['calculated_at']
    )


def downgrade():
    # Drop indexes in reverse order
    op.drop_index('idx_project_attendance_wage_calculated_at')
    op.drop_index('idx_project_attendance_wage_daily_wage')
    op.drop_index('idx_project_attendance_wage_attendance')
    
    op.drop_index('idx_project_daily_wage_project_date')
    op.drop_index('idx_project_daily_wage_effective_date')
    op.drop_index('idx_project_daily_wage_project')
    
    op.drop_index('idx_project_attendance_contractor')
    op.drop_index('idx_project_attendance_engineer_date')
    op.drop_index('idx_project_attendance_project_date')
    
    op.drop_index('idx_self_attendance_punch_times')
    op.drop_index('idx_self_attendance_punch_in_location')
    op.drop_index('idx_self_attendance_date')
    op.drop_index('idx_self_attendance_user_date')
