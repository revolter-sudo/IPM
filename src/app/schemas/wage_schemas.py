from typing import Optional, Any, List, Dict
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator


class WageResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }


# Wage Configuration Schemas
class WageConfigurationCreate(BaseModel):
    daily_wage_rate: float = Field(..., gt=0, description="Daily wage rate (must be positive)")
    effective_date: Optional[date] = Field(None, description="Effective date (defaults to current date)")

    @field_validator("daily_wage_rate")
    def validate_daily_wage_rate(cls, value):
        if value <= 0:
            raise ValueError("Daily wage rate must be positive")
        return value

    @field_validator("effective_date")
    def validate_effective_date(cls, value):
        if value and value > date.today():
            raise ValueError("Effective date cannot be in the future")
        return value


class WageConfigurationUpdate(BaseModel):
    daily_wage_rate: float = Field(..., gt=0, description="Daily wage rate (must be positive)")
    effective_date: date = Field(..., description="Effective date")

    @field_validator("daily_wage_rate")
    def validate_daily_wage_rate(cls, value):
        if value <= 0:
            raise ValueError("Daily wage rate must be positive")
        return value

    @field_validator("effective_date")
    def validate_effective_date(cls, value):
        if value > date.today():
            raise ValueError("Effective date cannot be in the future")
        return value


class UserInfo(BaseModel):
    uuid: UUID
    name: str
    role: str


class WageConfigurationResponse(BaseModel):
    uuid: UUID
    project_id: UUID
    daily_wage_rate: float
    effective_date: date
    configured_by: UserInfo
    created_at: datetime

    model_config = {"from_attributes": True}


# Wage Calculation Schemas
class AttendanceInfo(BaseModel):
    uuid: UUID
    attendance_date: date
    marked_at: datetime
    no_of_labours: int
    site_engineer: UserInfo
    sub_contractor: UserInfo


class WageCalculationInfo(BaseModel):
    uuid: UUID
    daily_wage_rate: float
    total_wage_amount: float
    calculated_at: datetime


class WageConfigurationInfo(BaseModel):
    uuid: UUID
    effective_date: date
    configured_by: UserInfo
    configured_at: datetime


class WageCalculationDetail(BaseModel):
    attendance: AttendanceInfo
    wage_calculation: WageCalculationInfo
    wage_configuration: WageConfigurationInfo

    model_config = {"from_attributes": True}


# Wage Summary and Reporting Schemas
class WageSummary(BaseModel):
    total_wage_amount: float
    total_labour_days: int
    average_daily_wage: float
    unique_contractors: int


class WageSummaryParams(BaseModel):
    start_date: Optional[date] = Field(None, description="Start date for filtering")
    end_date: Optional[date] = Field(None, description="End date for filtering")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=100, description="Items per page")


class WageSummaryResponse(BaseModel):
    wage_calculations: List[WageCalculationDetail]
    summary: WageSummary
    total_count: int
    page: int
    limit: int

    model_config = {"from_attributes": True}


# Wage History Schemas
class WageRateChange(BaseModel):
    effective_date: date
    old_rate: Optional[float] = None
    new_rate: float
    configured_by: UserInfo


class MonthlySummary(BaseModel):
    total_amount: float
    total_labour_days: int
    rate_change_impact: float


class WageHistoryResponse(BaseModel):
    wage_history: List[WageCalculationDetail]
    rate_changes: List[WageRateChange]
    monthly_summary: MonthlySummary

    model_config = {"from_attributes": True}


# Wage Rate History Schemas
class WageRateHistoryParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=100, description="Items per page")


class WageRateHistoryResponse(BaseModel):
    wage_rates: List[WageConfigurationResponse]
    total_count: int
    page: int
    limit: int

    model_config = {"from_attributes": True}


# Specific Attendance Wage Details
class AttendanceWageDetailsResponse(BaseModel):
    attendance: AttendanceInfo
    wage_calculation: WageCalculationInfo
    wage_configuration: WageConfigurationInfo

    model_config = {"from_attributes": True}


# Bulk Operations Schemas
class BulkWageConfigurationCreate(BaseModel):
    project_ids: List[UUID] = Field(..., min_length=1, description="List of project UUIDs")
    daily_wage_rate: float = Field(..., gt=0, description="Daily wage rate for all projects")
    effective_date: Optional[date] = Field(None, description="Effective date (defaults to current date)")

    @field_validator("daily_wage_rate")
    def validate_daily_wage_rate(cls, value):
        if value <= 0:
            raise ValueError("Daily wage rate must be positive")
        return value

    @field_validator("project_ids")
    def validate_project_ids(cls, value):
        if len(value) == 0:
            raise ValueError("At least one project ID is required")
        return value


class BulkWageConfigurationResponse(BaseModel):
    successful_configurations: List[WageConfigurationResponse]
    failed_configurations: List[Dict[str, Any]]
    total_processed: int
    successful_count: int
    failed_count: int

    model_config = {"from_attributes": True}


# Analytics Schemas
class WageAnalytics(BaseModel):
    project_id: UUID
    project_name: str
    total_wage_amount: float
    total_labour_days: int
    average_daily_wage: float
    highest_daily_wage: float
    lowest_daily_wage: float
    wage_trend: str  # "increasing", "decreasing", "stable"
    last_updated: datetime

    model_config = {"from_attributes": True}


class WageAnalyticsParams(BaseModel):
    start_date: Optional[date] = Field(None, description="Start date for analytics")
    end_date: Optional[date] = Field(None, description="End date for analytics")
    project_ids: Optional[List[UUID]] = Field(None, description="Filter by specific projects")


class WageAnalyticsResponse(BaseModel):
    analytics: List[WageAnalytics]
    overall_summary: WageSummary
    period_start: date
    period_end: date

    model_config = {"from_attributes": True}


# Validation Schemas
class WageValidationError(BaseModel):
    field: str
    error: str
    value: Any


class WageValidationResponse(BaseModel):
    is_valid: bool
    errors: List[WageValidationError] = []
    warnings: List[str] = []

    model_config = {"from_attributes": True}
