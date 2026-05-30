def executive_summary_prompt(data: dict) -> str:
    r = data["revenue"]
    l = data["leads"]
    t = data["tasks"]

    return f"""You are writing a daily business performance report for Rana, founder of The Label AI Studios PH — a one-person AI automation studio based in the Philippines.

Today's date: {data["date"]}

Business data:
REVENUE
- This week: ₱{r["this_week_total"]:,.2f}
- Last week: ₱{r["last_week_total"]:,.2f}
- Trend: {r["trend"].upper()} {r["trend_pct"]}%
- Top sources: {", ".join(f"{k}: ₱{v:,.0f}" for k, v in sorted(r["by_source"].items(), key=lambda x: -x[1])[:3])}

LEADS
- Total leads: {l["total"]}
- Converted: {l["converted"]}
- Conversion rate: {l["conversion_rate"]}%
- New leads this week: {l["this_week_leads"]}
- Top sources: {", ".join(f"{k}: {v}" for k, v in sorted(l["by_source"].items(), key=lambda x: -x[1])[:3])}

TASKS
- Total tasks: {t["total"]}
- Completed: {t["completed"]} ({t["completion_rate"]}%)
- Overdue: {len(t["overdue"])}
- Completed this week: {", ".join(t["done_this_week"][:3]) or "none"}

Write exactly 3 paragraphs:
1. Overall business health — revenue trend, momentum, what it means
2. Lead pipeline status — quality, conversion, what's working
3. Operational health — task completion, what to watch

Tone: like a sharp business advisor briefing a founder over morning coffee — direct, human, no corporate fluff. Use real numbers. Be honest if something needs attention.

Return ONLY the 3 paragraphs. No headings, no labels."""


def wins_prompt(data: dict) -> str:
    r = data["revenue"]
    l = data["leads"]
    t = data["tasks"]

    return f"""Based on this week's business data for The Label AI Studios PH, identify the top 3 wins.

Data:
- Revenue this week: ₱{r["this_week_total"]:,.2f} ({r["trend"]} {r["trend_pct"]}% vs last week)
- New leads this week: {l["this_week_leads"]}
- Conversion rate: {l["conversion_rate"]}%
- Tasks completed this week: {", ".join(t["done_this_week"]) or "none recorded"}
- Top revenue source: {max(r["by_source"], key=r["by_source"].get) if r["by_source"] else "N/A"}

Write exactly 3 wins as short punchy bullet points.
- Start each with a strong verb (Closed, Generated, Hit, Completed, Grew, Launched)
- Include a specific number or metric in each
- Max 15 words per bullet

Return ONLY the 3 bullet points, one per line, starting with "•"."""


def attention_prompt(data: dict) -> str:
    r = data["revenue"]
    l = data["leads"]
    t = data["tasks"]

    overdue_list = ", ".join([x["task"] for x in t["overdue"][:3]]) or "none"
    pending_list = ", ".join(t["pending"][:5]) or "none"

    return f"""Based on this business data, identify the top 3 things that need attention today for The Label AI Studios PH.

Data:
- Revenue trend: {r["trend"]} {r["trend_pct"]}% vs last week
- Lead conversion rate: {l["conversion_rate"]}% (industry avg ~20%)
- Overdue tasks: {overdue_list}
- Pending tasks: {pending_list}
- Leads by status: {", ".join(f"{k}: {v}" for k, v in l["by_status"].items())}

Write exactly 3 action items as bullet points.
- Be specific — name the actual problem, not a vague concern
- Each ends with a clear suggested action
- Max 20 words per bullet
- Honest but not alarmist

Return ONLY the 3 bullet points, one per line, starting with "•"."""
