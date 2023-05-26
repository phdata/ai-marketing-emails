import datetime


def humanize_date(
    date: datetime.date, current_date: datetime.date = datetime.date.today()
) -> str:
    """
    Returns a human-readable version of a date using relative language

    :param date: The date to be humanized.
    :param current_date: The current date.
    :return: A human-readable version of the date.
    """
    if date is None:
        return None
    delta = current_date - date
    year_delta = current_date.year - date.year
    month_delta = current_date.month - date.month
    week_delta = current_date.isocalendar()[1] - date.isocalendar()[1]
    if delta.days == 0:
        return "today"
    elif delta.days == 1:
        return "yesterday"
    elif delta.days < 5:
        return "a couple days ago"
    elif week_delta == 1 and year_delta == 0:
        return "last week"
    elif week_delta > 0 and week_delta < 3 and year_delta == 0:
        return "a couple weeks ago"
    elif year_delta == 0 and month_delta == 0:
        return "earlier this month"
    elif year_delta == 0 and month_delta == 1:
        return "last month"
    elif year_delta == 0:
        return f"last {date.strftime('%B')}"
    elif year_delta == 1 and month_delta < 0:
        return f"last {date.strftime('%B')}"
    elif year_delta == 1:
        return "last year"
    elif year_delta < 5:
        return f"{year_delta} years ago"
    else:
        return date.strftime("%B %d, %Y")


if __name__ == "__main__":
    current_date = datetime.date.today()

    for i in range(0, 45, 1):
        date = current_date - datetime.timedelta(days=i)
        print(date, "=>", humanize_date(date, current_date))

    for i in range(45, 600, 30):
        date = current_date - datetime.timedelta(days=i)
        print(date, "=>", humanize_date(date, current_date))
