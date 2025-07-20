"""
Attendance utility functions for calculating working days, analytics, and other attendance-related operations.
"""

import calendar
from datetime import date, datetime, timedelta
from typing import List, Tuple
from src.app.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_working_days_in_month(year: int, month: int) -> int:
    """
    Calculate the number of working days in a given month.
    Working days exclude only Sundays (6-day work week: Monday to Saturday).

    Args:
        year (int): The year
        month (int): The month (1-12)

    Returns:
        int: Number of working days in the month
    """
    try:
        # Get the number of days in the month
        days_in_month = calendar.monthrange(year, month)[1]

        working_days = 0
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            # Monday = 0, Sunday = 6
            # Only Sunday (6) is a holiday, Monday to Saturday (0-5) are working days
            if current_date.weekday() != 6:  # Monday to Saturday
                working_days += 1

        return working_days
    except Exception as e:
        logger.error(f"Error calculating working days for {year}-{month}: {str(e)}")
        return 0


def get_working_days_up_to_date(target_date: date) -> int:
    """
    Calculate the number of working days from the start of the month up to the target date (inclusive).
    Working days exclude only Sundays (6-day work week: Monday to Saturday).

    Args:
        target_date (date): The target date

    Returns:
        int: Number of working days from start of month to target date
    """
    try:
        year = target_date.year
        month = target_date.month

        working_days = 0
        for day in range(1, target_date.day + 1):
            current_date = date(year, month, day)
            # Monday = 0, Sunday = 6
            # Only Sunday (6) is a holiday, Monday to Saturday (0-5) are working days
            if current_date.weekday() != 6:  # Monday to Saturday
                working_days += 1

        return working_days
    except Exception as e:
        logger.error(f"Error calculating working days up to {target_date}: {str(e)}")
        return 0


def calculate_attendance_percentage(present_days: int, total_working_days: int) -> float:
    """
    Calculate attendance percentage.
    
    Args:
        present_days (int): Number of days present
        total_working_days (int): Total working days in the period
    
    Returns:
        float: Attendance percentage (0-100)
    """
    try:
        if total_working_days == 0:
            return 0.0
        
        percentage = (present_days / total_working_days) * 100
        return round(percentage, 2)
    except Exception as e:
        logger.error(f"Error calculating attendance percentage: {str(e)}")
        return 0.0


def get_attendance_feedback(percentage: float) -> str:
    """
    Get feedback message based on attendance percentage.
    
    Args:
        percentage (float): Attendance percentage
    
    Returns:
        str: Feedback message
    """
    try:
        if percentage >= 90:
            return "Excellent Attendance Record"
        elif percentage >= 70:
            return "Good Attendance Record"
        elif percentage >= 50:
            return "Average Attendance Record"
        else:
            return "Poor Attendance Record"
    except Exception as e:
        logger.error(f"Error getting attendance feedback: {str(e)}")
        return "Unable to determine attendance record"


def parse_month_year(month_str: str) -> Tuple[int, int]:
    """
    Parse month string in MM-YYYY format to month and year integers.

    Args:
        month_str (str): Month string in MM-YYYY format (e.g., "12-2024")

    Returns:
        Tuple[int, int]: (month, year)

    Raises:
        ValueError: If the format is invalid
    """
    try:
        if not month_str or not isinstance(month_str, str):
            raise ValueError("Month string cannot be empty")

        if "-" not in month_str:
            raise ValueError("Month format must include '-' separator")

        parts = month_str.split("-")
        if len(parts) != 2:
            raise ValueError("Month format must have exactly one '-' separator")

        month_part, year_part = parts

        if len(month_part) != 2:
            raise ValueError("Month part must be 2 digits (e.g., '01', '12')")

        if len(year_part) != 4:
            raise ValueError("Year part must be 4 digits (e.g., '2024')")

        month = int(month_part)
        year = int(year_part)

        if month < 1 or month > 12:
            raise ValueError("Month must be between 01 and 12")

        if year < 2020 or year > 2030:
            raise ValueError("Year must be between 2020 and 2030")

        return month, year
    except ValueError:
        raise  # Re-raise ValueError as is
    except Exception as e:
        logger.error(f"Error parsing month string '{month_str}': {str(e)}")
        raise ValueError(f"Invalid month format. Use MM-YYYY format (e.g., '12-2024')")


def get_month_date_range(year: int, month: int) -> Tuple[date, date]:
    """
    Get the start and end dates for a given month.
    
    Args:
        year (int): The year
        month (int): The month (1-12)
    
    Returns:
        Tuple[date, date]: (start_date, end_date) of the month
    """
    try:
        start_date = date(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        end_date = date(year, month, days_in_month)
        
        return start_date, end_date
    except Exception as e:
        logger.error(f"Error getting month date range for {year}-{month}: {str(e)}")
        raise ValueError(f"Invalid year or month: {year}-{month}")


def is_working_day(check_date: date) -> bool:
    """
    Check if a given date is a working day (Monday to Saturday).
    Only Sundays are considered holidays in a 6-day work week.

    Args:
        check_date (date): The date to check

    Returns:
        bool: True if it's a working day, False otherwise
    """
    try:
        # Monday = 0, Sunday = 6
        # Only Sunday (6) is a holiday, Monday to Saturday (0-5) are working days
        return check_date.weekday() != 6
    except Exception as e:
        logger.error(f"Error checking if {check_date} is a working day: {str(e)}")
        return False


def get_current_month_working_days() -> int:
    """
    Get the number of working days in the current month.
    
    Returns:
        int: Number of working days in current month
    """
    try:
        today = date.today()
        return get_working_days_in_month(today.year, today.month)
    except Exception as e:
        logger.error(f"Error getting current month working days: {str(e)}")
        return 0


def get_current_month_working_days_up_to_today() -> int:
    """
    Get the number of working days from the start of current month up to today.
    
    Returns:
        int: Number of working days from start of current month to today
    """
    try:
        today = date.today()
        return get_working_days_up_to_date(today)
    except Exception as e:
        logger.error(f"Error getting current month working days up to today: {str(e)}")
        return 0
