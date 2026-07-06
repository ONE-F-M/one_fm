# Copyright (c) 2026, One FM and contributors
# For license information, please see license.txt

"""Server-side data provider for the Maintenance Scheduler page.

The scheduler renders Maintenance Work Orders on an interactive, high-density
grid that can be viewed at six different time granularities (viewports):

    Hourly    - one day split into 24 hourly slots
    Daily     - one week (Sun - Sat) as 7 day columns
    Weekly    - the weeks (Sun-start) that cover one month
    Monthly   - a 7-column Sun - Sat calendar of the selected month
    Quarterly - the 3 months of the selected quarter
    Yearly    - the 12 months of the selected year

Each Work Order is placed on the axis by its ``planned_deadline``; when that is
not set the ``creation_datetime`` is used as a fallback (matching how the board
is meant to reflect *planned* execution while still surfacing un-planned orders).

Cascading location filters run top-down:
    Project -> Operations Site -> Building -> Maintenance Floor -> Space
"""

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	add_to_date,
	get_datetime,
	get_first_day,
	get_last_day,
	getdate,
	now_datetime,
	nowdate,
)

# A day card / bucket shows this many Work Orders, then collapses the rest
# behind a "+X more" link (expanded client-side). Kept in sync with the JS.
MAX_VISIBLE = 5

VIEWS = ("hourly", "daily", "weekly", "monthly", "quarterly", "yearly")

# Location filter chain, ordered top -> bottom, for reference:
#   project           Project
#   operations_site   Operations Site  (link: project)
#   building          Building         (link: operations_site, project)
#   maintenance_floor Maintenance Floor(link: building_name, operations_site, project)
#   space             Space            (link: maintenance_floor, building_name, ...)
# Note the field linking Floor/Space to a Building is "building_name", not
# "building". See get_location_filter_data() for how the ancestry is exposed.
LOCATION_LEVELS = ("project", "operations_site", "building", "maintenance_floor", "space")


# ---------------------------------------------------------------------------
# Cascading location filters
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_location_filter_data() -> dict:
	"""Return every cascading-filter level's options with full parent ancestry.

	The client loads this once and performs all cascade filtering and parent
	auto-fill in-memory (matching the Roster page's preload approach). This is
	what lets a user pick a lower level (e.g. a Space) and have every higher
	level (Floor / Building / Site / Project) fill in automatically.

	Each option carries an ``ancestors`` dict keyed by the *filter level* keys
	used on the client (project / operations_site / building /
	maintenance_floor). Note the naming quirk: the field linking Maintenance
	Floor and Space to a Building is ``building_name``, which we normalise to
	the ``building`` key here so the client sees a uniform ancestry map.

	Uses ``frappe.get_list`` so the user's read permissions are honoured.
	"""
	projects = frappe.get_list(
		"Project",
		fields=["name", "project_name"],
		order_by="project_name asc",
		limit_page_length=0,
	)
	operations_sites = frappe.get_list(
		"Operations Site",
		fields=["name", "project"],
		order_by="name asc",
		limit_page_length=0,
	)
	buildings = frappe.get_list(
		"Building",
		fields=["name", "operations_site", "project"],
		order_by="name asc",
		limit_page_length=0,
	)
	floors = frappe.get_list(
		"Maintenance Floor",
		fields=["name", "building_name", "operations_site", "project"],
		order_by="name asc",
		limit_page_length=0,
	)
	spaces = frappe.get_list(
		"Space",
		fields=["name", "maintenance_floor", "building_name", "operations_site", "project"],
		order_by="name asc",
		limit_page_length=0,
	)

	return {
		"project": [
			{"value": p.name, "label": p.project_name or p.name, "ancestors": {}}
			for p in projects
		],
		"operations_site": [
			{"value": s.name, "label": s.name, "ancestors": {"project": s.project}}
			for s in operations_sites
		],
		"building": [
			{
				"value": b.name,
				"label": b.name,
				"ancestors": {"operations_site": b.operations_site, "project": b.project},
			}
			for b in buildings
		],
		"maintenance_floor": [
			{
				"value": f.name,
				"label": f.name,
				"ancestors": {
					"building": f.building_name,
					"operations_site": f.operations_site,
					"project": f.project,
				},
			}
			for f in floors
		],
		"space": [
			{
				"value": sp.name,
				"label": sp.name,
				"ancestors": {
					"maintenance_floor": sp.maintenance_floor,
					"building": sp.building_name,
					"operations_site": sp.operations_site,
					"project": sp.project,
				},
			}
			for sp in spaces
		],
	}


# ---------------------------------------------------------------------------
# Grid data
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_schedule_data(view: str = "monthly", anchor: str | None = None, filters=None) -> dict:
	"""Return the bucketed grid for a viewport + anchor date + location filters.

	Args:
		view: one of VIEWS. Defaults to "monthly".
		anchor: reference date (YYYY-MM-DD) inside the period to display.
			Defaults to today.
		filters: dict (or JSON string) of selected location filters, any of
			project / operations_site / building / maintenance_floor / space.

	Returns dict: {view, anchor, period_label, buckets: [...]}.
	Each bucket is one cell/column of the grid with its Work Orders attached.
	"""
	view = (view or "monthly").strip().lower()
	if view not in VIEWS:
		view = "monthly"

	anchor_date = getdate(anchor) if anchor else getdate(nowdate())
	filters = _parse_filters(filters)

	start, end, buckets = _build_buckets(view, anchor_date)

	work_orders = _fetch_work_orders(start, end, filters)
	_assign_to_buckets(view, buckets, work_orders)

	return {
		"view": view,
		"anchor": anchor_date.isoformat(),
		"period_label": _period_label(view, anchor_date),
		"start": start.isoformat(),
		"end": end.isoformat(),
		"max_visible": MAX_VISIBLE,
		"buckets": buckets,
		"summary": _build_summary(work_orders),
	}


@frappe.whitelist(methods=["POST"])
def reschedule_work_order(name: str, new_date: str) -> dict:
	"""Move a Work Order to a new planned date (drag-and-drop reschedule).

	The Planned Deadline is a read-only field the controller derives from the
	SLA Trigger Time, so we shift the SLA Trigger Time by the same delta as the
	new date and write both values. Persisted with ``db_set`` so the move works
	on submitted Work Orders and applies as a straight last-write-wins update
	(no timestamp-mismatch conflict) when two users move the same task.

	Blocks Completed Work Orders and any drop onto a past date.
	"""
	if not name or not new_date:
		frappe.throw(_("Work Order and target date are required."))

	doc = frappe.get_doc("Maintenance Work Order", name)
	# Document-level permission gate (whitelisted method — never trust the caller).
	doc.check_permission("write")

	# AC: a Completed Work Order cannot be moved.
	if doc.status == "Completed":
		frappe.throw(_("Completed Work Orders cannot be rescheduled."))

	# AC: a Work Order cannot be dropped on a past date.
	target_date = getdate(new_date)
	if target_date < getdate(nowdate()):
		frappe.throw(_("A Work Order cannot be moved to a past date."))

	if not doc.planned_deadline:
		frappe.throw(_("This Work Order has no Planned Deadline to reschedule."))

	old_deadline = get_datetime(doc.planned_deadline)
	# Only the date changes — preserve the original time-of-day.
	new_deadline = get_datetime(f"{target_date.isoformat()} {old_deadline.strftime('%H:%M:%S')}")

	updates = {"planned_deadline": new_deadline}

	# Shift the SLA Trigger Time by the same delta so the SLA-derived model stays
	# consistent with the new planned date (per the reschedule design decision).
	if doc.sla_trigger_time:
		delta = new_deadline - old_deadline
		updates["sla_trigger_time"] = get_datetime(doc.sla_trigger_time) + delta

	doc.db_set(updates, update_modified=True)

	return {
		"name": doc.name,
		"planned_deadline": new_deadline.isoformat(),
		"status": doc.status,
	}


def _parse_filters(filters) -> dict:
	"""Normalise the filters argument (JSON string or dict) to a clean dict."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) if filters else {}
	filters = filters or {}
	return {k: v for k, v in filters.items() if k in LOCATION_LEVELS and v}


def _fetch_work_orders(start, end, filters: dict) -> list[dict]:
	"""Fetch Maintenance Work Orders overlapping [start, end] for the filters.

	Placement is by ``planned_deadline`` with a fallback to
	``creation_datetime``; both queries run through ``frappe.get_list`` so user
	permissions are enforced. Cancelled orders (docstatus 2) are excluded.
	"""
	base_filters = dict(filters)
	base_filters["docstatus"] = ["<", 2]

	fields = [
		"name",
		"object_name",
		"object",
		"maintenance_type",
		"status",
		"priority",
		"space",
		"maintenance_floor",
		"building",
		"operations_site",
		"project",
		"planned_deadline",
		"creation_datetime",
		"completion_time",
	]

	start_str = get_datetime(start).strftime("%Y-%m-%d %H:%M:%S")
	end_str = get_datetime(end).strftime("%Y-%m-%d %H:%M:%S")

	# Primary: orders with a planned deadline inside the window.
	planned = frappe.get_list(
		"Maintenance Work Order",
		filters={**base_filters, "planned_deadline": ["between", [start_str, end_str]]},
		fields=fields,
		order_by="planned_deadline asc",
		limit_page_length=0,
	)

	# Fallback: orders with no planned deadline, placed by creation time.
	unplanned = frappe.get_list(
		"Maintenance Work Order",
		filters={
			**base_filters,
			"planned_deadline": ["is", "not set"],
			"creation_datetime": ["between", [start_str, end_str]],
		},
		fields=fields,
		order_by="creation_datetime asc",
		limit_page_length=0,
	)

	# "Overdue" is a derived/virtual state (not a stored status): a Work Order is
	# overdue when its planned deadline has passed and it is not yet Completed.
	# Compared against a single "now" so all cards share one reference point.
	now = now_datetime()

	work_orders = []
	for wo in planned + unplanned:
		slot = wo.get("planned_deadline") or wo.get("creation_datetime")
		if not slot:
			continue
		slot_dt = get_datetime(slot)
		is_planned = bool(wo.get("planned_deadline"))
		is_completed = wo.get("status") == "Completed"
		planned_dt = get_datetime(wo.get("planned_deadline")) if is_planned else None
		is_overdue = bool(is_planned and not is_completed and planned_dt and planned_dt < now)

		# SLA: a planned order is "due" in the range; it counts as met when it was
		# completed on or before its planned deadline (contract deadline).
		completed_within_deadline = bool(
			is_completed
			and is_planned
			and wo.get("completion_time")
			and get_datetime(wo.get("completion_time")) <= planned_dt
		)

		work_orders.append(
			{
				"name": wo.name,
				"object_name": wo.object_name or wo.object,
				"maintenance_type": wo.maintenance_type,
				"status": wo.status,
				"priority": wo.priority,
				"space": wo.space,
				"building": wo.building,
				"operations_site": wo.operations_site,
				"project": wo.project,
				"slot": slot_dt.isoformat(),
				"time_label": slot_dt.strftime("%H:%M"),
				"date_key": slot_dt.date().isoformat(),
				"hour": slot_dt.hour,
				"is_planned": is_planned,
				"is_completed": is_completed,
				"is_overdue": is_overdue,
				# "due in the selected range" == has a planned deadline in the window.
				"is_due": is_planned,
				"completed_within_deadline": completed_within_deadline,
			}
		)
	return work_orders


def _build_summary(work_orders: list[dict]) -> dict:
	"""Aggregate footer counters + SLA % for the currently visible Work Orders.

	Recomputed on every load, so it stays live with the selected viewport,
	anchor date and location filters. Overdue takes precedence over the stored
	status when counting so Open / Completed / Overdue partition cleanly.

	SLA % = completed-within-planned-deadline / total-due-in-range * 100.
	"""
	summary = {
		"open": 0,
		"dispatched": 0,
		"on_hold": 0,
		"completed": 0,
		"overdue": 0,
		"total": len(work_orders),
		"due": 0,
		"completed_within_deadline": 0,
		"sla_percent": 0.0,
	}

	for wo in work_orders:
		if wo["is_overdue"]:
			summary["overdue"] += 1
		elif wo["status"] == "Completed":
			summary["completed"] += 1
		elif wo["status"] == "Open":
			summary["open"] += 1
		elif wo["status"] == "Dispatched":
			summary["dispatched"] += 1
		elif wo["status"] == "On Hold - Parts Required":
			summary["on_hold"] += 1

		if wo["is_due"]:
			summary["due"] += 1
			if wo["completed_within_deadline"]:
				summary["completed_within_deadline"] += 1

	if summary["due"]:
		summary["sla_percent"] = round(
			summary["completed_within_deadline"] / summary["due"] * 100, 1
		)

	return summary


# ---------------------------------------------------------------------------
# Bucket construction (one branch per viewport)
# ---------------------------------------------------------------------------


def _week_start(d):
	"""Sunday of the week containing date ``d`` (Sunday = start of week)."""
	# Python weekday(): Mon=0 .. Sun=6. Days since the preceding Sunday:
	return add_days(d, -((d.weekday() + 1) % 7))


def _build_buckets(view: str, anchor):
	"""Return (start_date, end_date, buckets[]) for the viewport.

	``start``/``end`` bound the DB query; ``buckets`` are the grid cells, each a
	dict with an empty ``work_orders`` list to be filled by ``_assign_to_buckets``.
	"""
	today = getdate(nowdate())

	if view == "hourly":
		buckets = [
			{
				"key": f"h{h}",
				"label": f"{h:02d}:00",
				"sublabel": _hour_period(h),
				"type": "hour",
				"hour": h,
				"is_current": (anchor == today and now_datetime().hour == h),
				"work_orders": [],
			}
			for h in range(24)
		]
		start = get_datetime(f"{anchor} 00:00:00")
		end = get_datetime(f"{anchor} 23:59:59")
		return start, end, buckets

	if view == "daily":
		week_start = _week_start(anchor)
		buckets = []
		for i in range(7):
			d = add_days(week_start, i)
			buckets.append(_day_bucket(d, today))
		start = get_datetime(f"{week_start} 00:00:00")
		end = get_datetime(f"{add_days(week_start, 6)} 23:59:59")
		return start, end, buckets

	if view == "weekly":
		first = get_first_day(anchor)
		last = get_last_day(anchor)
		week_start = _week_start(first)
		buckets = []
		cursor = week_start
		while cursor <= last:
			w_end = add_days(cursor, 6)
			buckets.append(
				{
					"key": f"w{cursor.isoformat()}",
					"label": _("Week of {0}").format(cursor.strftime("%b %-d")),
					"sublabel": f"{cursor.strftime('%b %-d')} - {w_end.strftime('%b %-d')}",
					"type": "week",
					"date": cursor.isoformat(),
					"is_current": (cursor <= today <= w_end),
					"work_orders": [],
				}
			)
			cursor = add_days(cursor, 7)
		start = get_datetime(f"{week_start} 00:00:00")
		end = get_datetime(f"{add_days(cursor, -1)} 23:59:59")
		return start, end, buckets

	if view == "monthly":
		first = get_first_day(anchor)
		last = get_last_day(anchor)
		buckets = []
		d = first
		while d <= last:
			buckets.append(_day_bucket(d, today))
			d = add_days(d, 1)
		start = get_datetime(f"{first} 00:00:00")
		end = get_datetime(f"{last} 23:59:59")
		return start, end, buckets

	if view == "quarterly":
		q_index = (anchor.month - 1) // 3
		first_month = getdate(f"{anchor.year}-{q_index * 3 + 1:02d}-01")
		buckets = []
		for i in range(3):
			m = add_to_date(first_month, months=i)
			buckets.append(_month_bucket(m, today))
		start = get_datetime(f"{first_month} 00:00:00")
		end = get_datetime(f"{get_last_day(add_to_date(first_month, months=2))} 23:59:59")
		return start, end, buckets

	# yearly
	first_month = getdate(f"{anchor.year}-01-01")
	buckets = []
	for i in range(12):
		m = add_to_date(first_month, months=i)
		buckets.append(_month_bucket(m, today))
	start = get_datetime(f"{anchor.year}-01-01 00:00:00")
	end = get_datetime(f"{anchor.year}-12-31 23:59:59")
	return start, end, buckets


def _day_bucket(d, today):
	"""A single-day grid cell (used by daily + monthly views)."""
	return {
		"key": f"d{d.isoformat()}",
		"label": str(d.day),
		"sublabel": d.strftime("%a"),
		"type": "day",
		"date": d.isoformat(),
		# weekday index with Sunday = 0, used client-side to align the calendar.
		"weekday": (d.weekday() + 1) % 7,
		"is_today": (d == today),
		"is_current": (d == today),
		"work_orders": [],
	}


def _month_bucket(m, today):
	"""A single-month grid cell (used by quarterly + yearly views)."""
	return {
		"key": f"m{m.year}-{m.month:02d}",
		"label": m.strftime("%B"),
		"sublabel": str(m.year),
		"type": "month",
		"date": m.isoformat(),
		"month_key": f"{m.year}-{m.month:02d}",
		"is_current": (m.year == today.year and m.month == today.month),
		"work_orders": [],
	}


def _assign_to_buckets(view: str, buckets: list[dict], work_orders: list[dict]):
	"""Distribute Work Orders into the correct grid cell for the viewport."""
	index = {}
	if view == "hourly":
		index = {b["hour"]: b for b in buckets}
		for wo in work_orders:
			bucket = index.get(wo["hour"])
			if bucket is not None:
				bucket["work_orders"].append(wo)

	elif view in ("daily", "monthly"):
		index = {b["date"]: b for b in buckets}
		for wo in work_orders:
			bucket = index.get(wo["date_key"])
			if bucket is not None:
				bucket["work_orders"].append(wo)

	elif view == "weekly":
		for wo in work_orders:
			ws = _week_start(getdate(wo["date_key"])).isoformat()
			bucket = next((b for b in buckets if b["date"] == ws), None)
			if bucket is not None:
				bucket["work_orders"].append(wo)

	else:  # quarterly, yearly - by month
		index = {b["month_key"]: b for b in buckets}
		for wo in work_orders:
			mkey = wo["date_key"][:7]
			bucket = index.get(mkey)
			if bucket is not None:
				bucket["work_orders"].append(wo)


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def _hour_period(h: int) -> str:
	suffix = "AM" if h < 12 else "PM"
	display = h % 12 or 12
	return f"{display} {suffix}"


def _period_label(view: str, anchor) -> str:
	if view == "hourly":
		return anchor.strftime("%A, %-d %B %Y")
	if view == "daily":
		ws = _week_start(anchor)
		we = add_days(ws, 6)
		return f"{ws.strftime('%-d %b')} - {we.strftime('%-d %b %Y')}"
	if view in ("weekly", "monthly"):
		return anchor.strftime("%B %Y")
	if view == "quarterly":
		q = (anchor.month - 1) // 3 + 1
		return f"Q{q} {anchor.year}"
	return str(anchor.year)
