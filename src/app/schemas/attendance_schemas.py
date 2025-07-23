from typing import Optional, Any, List
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
from pytz import timezone

# Configure default timezone
ist = timezone("Asia/Kolkata")

class AttendanceStatus(str, Enum):
    absent   = "absent"
    present  = "present"
    off_day  = "off day"

class LocationData(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude must be between -90 and 90")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude must be between -180 and 180")
    address: Optional[str] = Field(None, description="Optional location address")

    @field_validator("latitude")
    def validate_latitude(cls, value):
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return value

    @field_validator("longitude")
    def validate_longitude(cls, value):
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return value


class AttendanceResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }


# Self Attendance Schemas
class SelfAttendancePunchIn(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Punch in latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Punch in longitude")
    location_address: Optional[str] = Field(None, description="Optional punch in location address")



class SelfAttendancePunchOut(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Punch out latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Punch out longitude")
    location_address: Optional[str] = Field(None, description="Optional punch out location address")



class ProjectInfo(BaseModel):
    uuid: UUID
    name: str


class SelfAttendanceResponse(BaseModel):
    uuid: UUID
    user_id: UUID
    user_name: str
    attendance_date: date
    punch_in_time: datetime
    punch_in_location: LocationData
    punch_out_time: Optional[datetime] = None
    punch_out_location: Optional[LocationData] = None
    total_hours: Optional[str] = None
    assigned_projects: List[ProjectInfo] = []
    status: AttendanceStatus

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda dt: dt.astimezone(ist).isoformat() if dt.tzinfo else ist.localize(dt).isoformat()
        }
    )
    
    @field_validator("punch_in_time", mode="before")
    def validate_punch_in_time(cls, v):
        if v and not v.tzinfo:
            return ist.localize(v)
        return v
        
    @field_validator("punch_out_time", mode="before")
    def validate_punch_out_time(cls, v):
        if v and not v.tzinfo:
            return ist.localize(v)
        return v


class SelfAttendanceStatus(BaseModel):
    uuid: Optional[UUID] = None
    user_id: UUID
    user_name: str
    attendance_date: date
    is_punched_in: bool
    punch_in_time: Optional[datetime] = None
    punch_out_time: Optional[datetime] = None
    current_hours: Optional[str] = None
    status: Optional[AttendanceStatus] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda dt: dt.astimezone(ist).isoformat() if dt.tzinfo else ist.localize(dt).isoformat()
        }
    )
    
    @field_validator("punch_in_time", mode="before")
    def validate_punch_in_time(cls, v):
        if v and not v.tzinfo:
            return ist.localize(v)
        return v
        
    @field_validator("punch_out_time", mode="before")
    def validate_punch_out_time(cls, v):
        if v and not v.tzinfo:
            return ist.localize(v)
        return v


# Project Attendance Schemas
class ProjectAttendanceCreate(BaseModel):
    project_id: UUID = Field(..., description="Project UUID")
    item_id: UUID = Field(..., description="Item UUID")
    sub_contractor_id: UUID = Field(..., description="Sub-contractor person UUID")
    no_of_labours: int = Field(..., gt=0, description="Number of labours (must be positive)")
    latitude: float = Field(..., ge=-90, le=90, description="Attendance marking latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Attendance marking longitude")
    location_address: Optional[str] = Field(None, description="Optional location address")
    notes: Optional[str] = Field(None, description="Optional notes")

    @field_validator("no_of_labours")
    def validate_no_of_labours(cls, value):
        if value <= 0:
            raise ValueError("Number of labours must be positive")
        return value


class PersonInfo(BaseModel):
    uuid: UUID
    name: str


class WageCalculationInfo(BaseModel):
    uuid: UUID
    daily_wage_rate: float
    total_wage_amount: float
    wage_config_effective_date: date

class ItemListView(BaseModel):
    uuid: UUID
    name: str
    category: Optional[str]

class ProjectAttendanceResponse(BaseModel):
    uuid: UUID
    project: ProjectInfo
    item: ItemListView
    sub_contractor: PersonInfo
    no_of_labours: int
    attendance_date: date
    photo_path: Optional[str] = None
    marked_at: datetime
    location: LocationData
    notes: Optional[str] = None
    wage_calculation: Optional[WageCalculationInfo] = None

    model_config = {"from_attributes": True}


# Daily Wage Management Schemas
class DailyWageCreate(BaseModel):
    daily_wage_rate: float = Field(..., gt=0, description="Daily wage rate (must be positive)")
    effective_date: Optional[date] = Field(None, description="Effective date (defaults to current date)")

    @field_validator("daily_wage_rate")
    def validate_daily_wage_rate(cls, value):
        if value <= 0:
            raise ValueError("Daily wage rate must be positive")
        return value


class DailyWageUpdate(BaseModel):
    daily_wage_rate: float = Field(..., gt=0, description="Daily wage rate (must be positive)")
    effective_date: date = Field(..., description="Effective date")

    @field_validator("daily_wage_rate")
    def validate_daily_wage_rate(cls, value):
        if value <= 0:
            raise ValueError("Daily wage rate must be positive")
        return value


class UserInfo(BaseModel):
    uuid: UUID
    name: str
    role: str


class DailyWageResponse(BaseModel):
    uuid: UUID
    project_id: UUID
    daily_wage_rate: float
    effective_date: date
    configured_by: UserInfo

    model_config = {"from_attributes": True}


# Pagination and History Schemas
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (starts from 1)")
    limit: int = Field(10, ge=1, le=100, description="Items per page (1-100)")


class AttendanceHistoryParams(BaseModel):
    start_date: Optional[date] = Field(None, description="Start date for filtering")
    end_date: Optional[date] = Field(None, description="End date for filtering")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=100, description="Items per page")


class ProjectAttendanceHistoryParams(BaseModel):
    project_id: Optional[UUID] = Field(None, description="Filter by project ID")
    start_date: Optional[date] = Field(None, description="Start date for filtering")
    end_date: Optional[date] = Field(None, description="End date for filtering")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=100, description="Items per page")


class AttendanceHistoryResponse(BaseModel):
    attendances: List[SelfAttendanceResponse]
    total_count: int
    page: int
    limit: int

    model_config = {"from_attributes": True}


class ProjectAttendanceSummary(BaseModel):
    total_labour_days: int
    unique_contractors: int
    average_daily_labours: float


class ProjectAttendanceHistoryResponse(BaseModel):
    attendances: List[ProjectAttendanceResponse]
    total_count: int
    page: int
    limit: int
    summary: Optional[ProjectAttendanceSummary] = None

    model_config = {"from_attributes": True}


# Reporting Schemas
class DailyAttendanceSummary(BaseModel):
    date: date
    project: Optional[ProjectInfo] = None
    self_attendances: int
    project_attendances: int
    total_labours: int
    total_wage_amount: float
    current_daily_wage_rate: float
    contractors: List[PersonInfo] = []

    model_config = {"from_attributes": True}


# Attendance Analytics Schemas
class AttendanceAnalyticsData(BaseModel):
    current_month: dict = Field(..., description="Current month attendance analytics")

    model_config = {"from_attributes": True}


class AttendanceAnalyticsResponse(BaseModel):
    data: AttendanceAnalyticsData
    message: str
    status_code: int

    def to_dict(self):
        return {
            "data": self.data.model_dump(),
            "message": self.message,
            "status_code": self.status_code
        }


class AdminAttendanceAnalyticsRequest(BaseModel):
    month: str = Field(..., description="Month in MM-YYYY format (e.g., '12-2024')")
    user_id: UUID = Field(..., description="UUID of the user to analyze")

    @field_validator("month")
    def validate_month_format(cls, value):
        import re
        if not re.match(r"^\d{2}-\d{4}$", value):
            raise ValueError("Month must be in MM-YYYY format (e.g., '12-2024')")

        month_part, year_part = value.split("-")
        month_num = int(month_part)
        year_num = int(year_part)

        if month_num < 1 or month_num > 12:
            raise ValueError("Month must be between 01 and 12")

        if year_num < 2020 or year_num > 2030:
            raise ValueError("Year must be between 2020 and 2030")

        return value
