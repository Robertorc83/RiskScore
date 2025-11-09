"""Date manipulation utilities"""

from datetime import date, timedelta
from typing import List


def generate_date_range(start: date, end: date) -> List[date]:
    """Generate list of dates from start to end (inclusive)"""
    days = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(days)]


def add_business_days(from_date: date, days: int) -> date:
    """Add business days to a date (simple version, doesn't account for holidays)"""
    return from_date + timedelta(days=days)
