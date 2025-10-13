from datetime import date, timedelta


def get_current_month_date_range() -> tuple[date, date]:
    """Returns the start and end date of the current month."""
    today = date.today()
    first_day = today.replace(day=1)
    if today.month == 12:
        last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(
            days=1
        )
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return first_day, last_day
