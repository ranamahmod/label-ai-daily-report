from datetime import datetime, timedelta


def parse_amount(value: str) -> float:
    """Safely parse a currency string to float."""
    try:
        return float(str(value).replace("₱", "").replace(",", "").replace(" ", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def get_week_range(offset_weeks: int = 0):
    """Get start and end date for a week (0 = this week, -1 = last week)."""
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=offset_weeks)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.date(), end_of_week.date()


def parse_date(date_str: str):
    """Try multiple date formats."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(date_str).strip(), fmt).date()
        except ValueError:
            continue
    return None


def analyze_revenue(rows: list[list]) -> dict:
    """Analyze revenue data. Rows: [date, source, amount]"""
    this_week_start, this_week_end = get_week_range(0)
    last_week_start, last_week_end = get_week_range(-1)

    this_week_total = 0.0
    last_week_total = 0.0
    by_source = {}
    all_entries = []

    for row in rows[1:]:  # skip header
        if len(row) < 3:
            continue
        date = parse_date(row[0])
        source = str(row[1]).strip()
        amount = parse_amount(row[2])

        if not date:
            continue

        all_entries.append({"date": date, "source": source, "amount": amount})
        by_source[source] = by_source.get(source, 0) + amount

        if this_week_start <= date <= this_week_end:
            this_week_total += amount
        if last_week_start <= date <= last_week_end:
            last_week_total += amount

    trend = "up" if this_week_total >= last_week_total else "down"
    trend_pct = (
        ((this_week_total - last_week_total) / last_week_total * 100)
        if last_week_total > 0
        else 0
    )

    return {
        "this_week_total": this_week_total,
        "last_week_total": last_week_total,
        "trend": trend,
        "trend_pct": round(abs(trend_pct), 1),
        "by_source": by_source,
        "total_entries": len(all_entries),
    }


def analyze_leads(rows: list[list]) -> dict:
    """Analyze leads data. Rows: [date, name, status, source]"""
    this_week_start, this_week_end = get_week_range(0)

    total = 0
    converted = 0
    this_week_leads = 0
    by_status = {}
    by_source = {}

    for row in rows[1:]:  # skip header
        if len(row) < 3:
            continue
        date = parse_date(row[0])
        status = str(row[2]).strip().lower() if len(row) > 2 else "unknown"
        source = str(row[3]).strip() if len(row) > 3 else "unknown"

        total += 1
        by_status[status] = by_status.get(status, 0) + 1
        by_source[source] = by_source.get(source, 0) + 1

        if status in ("converted", "closed", "won", "client"):
            converted += 1

        if date and this_week_start <= date <= this_week_end:
            this_week_leads += 1

    conversion_rate = round((converted / total * 100), 1) if total > 0 else 0

    return {
        "total": total,
        "converted": converted,
        "conversion_rate": conversion_rate,
        "this_week_leads": this_week_leads,
        "by_status": by_status,
        "by_source": by_source,
    }


def analyze_tasks(rows: list[list]) -> dict:
    """Analyze tasks. Rows: [task, status, due_date]"""
    today = datetime.today().date()

    total = 0
    completed = 0
    overdue = []
    pending = []
    done_this_week = []
    this_week_start, this_week_end = get_week_range(0)

    for row in rows[1:]:  # skip header
        if len(row) < 2:
            continue
        task = str(row[0]).strip()
        status = str(row[1]).strip().lower()
        due_date = parse_date(row[2]) if len(row) > 2 else None

        total += 1

        if status in ("done", "complete", "completed", "finished"):
            completed += 1
            if due_date and this_week_start <= due_date <= this_week_end:
                done_this_week.append(task)
        else:
            pending.append(task)
            if due_date and due_date < today:
                overdue.append({"task": task, "due": str(due_date)})

    completion_rate = round((completed / total * 100), 1) if total > 0 else 0

    return {
        "total": total,
        "completed": completed,
        "completion_rate": completion_rate,
        "overdue": overdue,
        "pending": pending[:10],  # top 10
        "done_this_week": done_this_week,
    }


def build_summary_data(revenue: dict, leads: dict, tasks: dict) -> dict:
    """Combine all metrics into a single summary dict for prompts."""
    return {
        "date": datetime.today().strftime("%B %d, %Y"),
        "revenue": revenue,
        "leads": leads,
        "tasks": tasks,
    }
