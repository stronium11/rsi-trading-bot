"""
Market Holidays Module
Calculates US stock market holidays (NYSE/NASDAQ closed days)
"""

from datetime import date, timedelta
from typing import Set


class MarketHolidays:
    """
    US Stock Market Holidays
    Markets are closed on weekends and federal holidays
    """

    # Fixed date holidays (these occur on the same date every year)
    FIXED_HOLIDAYS = [
        (1, 1),    # New Year's Day - January 1
        (6, 19),   # Juneteenth - June 19
        (7, 4),    # Independence Day - July 4
        (12, 25),  # Christmas Day - December 25
    ]

    def __init__(self):
        """Initialize with pre-calculated holidays through 2035"""
        self._holidays = self._calculate_holidays_through_2035()

    def _calculate_holidays_through_2035(self) -> Set[date]:
        """Calculate all market holidays from 2025 through 2035"""
        holidays = set()

        for year in range(2025, 2036):
            # Fixed date holidays
            for month, day in self.FIXED_HOLIDAYS:
                holiday_date = date(year, month, day)
                # If holiday falls on weekend, market closed on observed day
                if holiday_date.weekday() == 5:  # Saturday
                    holidays.add(holiday_date - timedelta(days=1))  # Friday
                elif holiday_date.weekday() == 6:  # Sunday
                    holidays.add(holiday_date + timedelta(days=1))  # Monday
                else:
                    holidays.add(holiday_date)

            # Memorial Day - Last Monday of May
            memorial_day = self._last_monday_of_month(year, 5)
            holidays.add(memorial_day)

            # Labor Day - First Monday of September
            labor_day = self._first_monday_of_month(year, 9)
            holidays.add(labor_day)

            # Thanksgiving - Fourth Thursday of November
            thanksgiving = self._nth_weekday_of_month(year, 11, 3, 4)  # 4th Thursday
            holidays.add(thanksgiving)

        return holidays

    def _first_monday_of_month(self, year: int, month: int) -> date:
        """Find the first Monday of a given month"""
        first_day = date(year, month, 1)
        # Monday is weekday 0
        days_until_monday = (7 - first_day.weekday()) % 7
        if days_until_monday == 0 and first_day.weekday() != 0:
            days_until_monday = 7
        return first_day + timedelta(days=days_until_monday)

    def _last_monday_of_month(self, year: int, month: int) -> date:
        """Find the last Monday of a given month"""
        # Start from the last day of the month
        if month == 12:
            last_day = date(year, 12, 31)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # Go backwards to find the last Monday
        days_back = (last_day.weekday() - 0) % 7
        return last_day - timedelta(days=days_back)

    def _nth_weekday_of_month(self, year: int, month: int, weekday: int, n: int) -> date:
        """
        Find the nth occurrence of a weekday in a month
        weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        n: which occurrence (1=first, 2=second, etc.)
        """
        first_day = date(year, month, 1)
        # Find the first occurrence of the weekday
        days_until_weekday = (weekday - first_day.weekday()) % 7
        first_occurrence = first_day + timedelta(days=days_until_weekday)
        # Add weeks to get to nth occurrence
        return first_occurrence + timedelta(weeks=n - 1)

    def is_market_holiday(self, check_date: date) -> bool:
        """
        Check if a given date is a market holiday

        Args:
            check_date: Date to check

        Returns:
            True if market is closed (holiday), False otherwise
        """
        return check_date in self._holidays

    def is_weekend(self, check_date: date) -> bool:
        """
        Check if a given date is a weekend

        Args:
            check_date: Date to check

        Returns:
            True if Saturday or Sunday, False otherwise
        """
        return check_date.weekday() in (5, 6)  # Saturday or Sunday

    def is_trading_day(self, check_date: date) -> bool:
        """
        Check if market is open on a given date

        Args:
            check_date: Date to check

        Returns:
            True if market is open, False if weekend or holiday
        """
        return not (self.is_weekend(check_date) or self.is_market_holiday(check_date))

    def get_all_holidays(self) -> Set[date]:
        """Get all calculated holidays"""
        return self._holidays.copy()

    def get_holidays_for_year(self, year: int) -> Set[date]:
        """Get all holidays for a specific year"""
        return {d for d in self._holidays if d.year == year}


# Singleton instance
_market_holidays = None


def get_market_holidays() -> MarketHolidays:
    """Get the singleton MarketHolidays instance"""
    global _market_holidays
    if _market_holidays is None:
        _market_holidays = MarketHolidays()
    return _market_holidays


# For testing
if __name__ == "__main__":
    holidays = get_market_holidays()

    print("US Stock Market Holidays (2025-2035)")
    print("=" * 70)

    for year in range(2025, 2036):
        year_holidays = sorted(holidays.get_holidays_for_year(year))
        print(f"\n{year}:")
        for holiday in year_holidays:
            print(f"  {holiday.strftime('%A, %B %d, %Y')}")

    # Test today
    today = date.today()
    print(f"\n\nToday ({today}):")
    print(f"  Is weekend? {holidays.is_weekend(today)}")
    print(f"  Is holiday? {holidays.is_market_holiday(today)}")
    print(f"  Is trading day? {holidays.is_trading_day(today)}")
