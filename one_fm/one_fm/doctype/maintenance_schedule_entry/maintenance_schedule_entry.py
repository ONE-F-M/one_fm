# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, get_datetime, getdate, today

# Standard start-of-day for a generated maintenance slot (08:00 local time).
DEFAULT_EXECUTION_TIME = "08:00:00"

# Slot statuses used across the automation routines.
STATUS_OPEN = "Open"
STATUS_WORK_ORDER_CREATED = "Work Order Created"

# Safety cap so a mis-configured (tiny) frequency can never spin an unbounded loop.
MAX_GENERATED_SLOTS = 1000


class MaintenanceScheduleEntry(Document):
	def validate(self):
		self.fetch_object_details()
		self.set_frequency_days()
		self.set_planned_execution_datetime()

	def fetch_object_details(self):
		"""Trace the asset's category and Space -> Floor -> Building -> Site -> Project
		location chain from the master Object record, mirroring Maintenance Work Order.

		Only fills fields that are currently empty so manual overrides are preserved.
		"""
		if not self.object:
			return

		obj = frappe.db.get_value(
			"Object",
			self.object,
			["object_category", "space"],
			as_dict=True,
		)
		if not obj:
			return

		if not self.object_category:
			self.object_category = obj.object_category
		if not self.space:
			self.space = obj.space

		if self.space:
			space = frappe.db.get_value(
				"Space",
				self.space,
				["maintenance_floor", "building_name", "operations_site", "project"],
				as_dict=True,
			)
			if space:
				if not self.maintenance_floor:
					self.maintenance_floor = space.maintenance_floor
				if not self.building:
					self.building = space.building_name
				if not self.operations_site:
					self.operations_site = space.operations_site
				if not self.project:
					self.project = space.project

	def set_frequency_days(self):
		"""Resolve Frequency (Days) from the linked Maintenance Frequency when it
		has not already been populated (the form also fetches this via fetch_from).
		"""
		if self.frequency_days:
			return
		if self.maintenance_frequency:
			self.frequency_days = frappe.db.get_value(
				"Maintenance Frequency", self.maintenance_frequency, "frequency_days"
			)

	def set_planned_execution_datetime(self):
		"""Derive the Planned Execution Datetime for this maintenance slot.

		Base-date resolution order (per user story):
		  1. Object's Last Service Date
		  2. else the Object's Commissioning Date
		  3. else the Object's system Creation Date

		The resolved base date plus Frequency (Days) is set at 08:00 local time.
		Computed only when the datetime is not already set, so a generated slot
		keeps a stable planned time.
		"""
		if self.planned_execution_datetime:
			return
		if not self.object or not self.frequency_days:
			return

		obj = frappe.db.get_value(
			"Object",
			self.object,
			["last_service_date", "commissioning_date", "creation"],
			as_dict=True,
		)
		if not obj:
			return

		base_date = obj.last_service_date or obj.commissioning_date or getdate(obj.creation)
		planned_date = add_days(getdate(base_date), cint(self.frequency_days))
		self.planned_execution_datetime = get_datetime(f"{planned_date} {DEFAULT_EXECUTION_TIME}")


# ─────────────────────────────────────────────────────────────────────────────
# Preventive Maintenance Automation
#
# Terminology (per the user story):
#   * "Maintenance Object"      -> the submittable ``Object`` asset record.
#   * "schedule directory"      -> the set of ``Maintenance Schedule Entry`` slots
#                                  linked to that Object via the ``object`` field.
#   * Global configuration      -> the ``Maintenance Settings`` single doctype:
#         - ``schedule_generation_months``          (how far ahead to build slots)
#         - ``work_order_generation_lead_time_days`` (look-ahead to raise Work Orders)
# ─────────────────────────────────────────────────────────────────────────────


def _get_settings():
	"""Return the cached Maintenance Settings single document."""
	from one_fm.one_fm.doctype.maintenance_settings.maintenance_settings import (
		get_maintenance_settings,
	)

	return get_maintenance_settings()


def _resolve_base_date(obj):
	"""Start point for the schedule: the Object's Last Service Date, falling back
	to today's date when the asset has never been serviced.
	"""
	return getdate(obj.last_service_date or today())


def _get_category_checklist(object_category):
	"""Return the master Object Maintenance Checklist for an Object Category, or
	None when the category has no checklist template configured.
	"""
	if not object_category:
		return None

	name = frappe.db.get_value(
		"Object Maintenance Checklist", {"object_category": object_category}, "name"
	)
	if not name:
		return None

	return frappe.get_doc("Object Maintenance Checklist", name)


def _slot_exists(object_name, maintenance_task, planned_dt):
	"""Idempotency guard: True if a slot already exists for this Object + task +
	planned datetime. The task is part of the key because a single Object may have
	several checklist tasks legitimately landing on the same planned date.
	"""
	return bool(
		frappe.db.exists(
			"Maintenance Schedule Entry",
			{
				"object": object_name,
				"maintenance_task": maintenance_task,
				"planned_execution_datetime": planned_dt,
			},
		)
	)


def _create_slot(obj, task, planned_dt):
	"""Create a single empty 'Open' schedule slot for one checklist task.

	The task's frequency and description are carried onto the slot; the entry's
	own ``validate`` traces the object category / location chain, and the pre-set
	``planned_execution_datetime`` / ``frequency_days`` are preserved.
	"""
	entry = frappe.get_doc(
		{
			"doctype": "Maintenance Schedule Entry",
			"object": obj.name,
			"status": STATUS_OPEN,
			"maintenance_task": task.task_description,
			"maintenance_frequency": task.maintenance_frequency,
			"frequency_days": task.frequency_days,
			"planned_execution_datetime": planned_dt,
		}
	)
	entry.insert(ignore_permissions=True)
	return entry


def build_schedule(object_name):
	"""Generate empty 'Open' schedule slots for an Object from its category checklist.

	Algorithm:
	  1. Start point : the Object's Last Service Date (or today if never serviced).
	  2. Stop line   : today + Schedule Generation (Months) (from Maintenance Settings).
	  3. Template    : the Object Maintenance Checklist whose ``object_category``
	                   matches the Object's category.
	  4. Nested loop : for every task row in that checklist, step forward by the
	                   task's own ``frequency_days`` and create a slot for each
	                   planned date up to the stop line.

	Idempotent: an existing slot for the same Object + task + planned datetime is
	never duplicated. Returns the number of newly created slots.
	"""
	obj = frappe.get_doc("Object", object_name)

	months = cint(_get_settings().schedule_generation_months)
	if months <= 0:
		return 0
	stop_date = getdate(add_months(today(), months))

	checklist = _get_category_checklist(obj.object_category)
	if not checklist:
		# No master checklist for this category -> nothing to schedule.
		return 0

	base_date = _resolve_base_date(obj)

	created = 0
	for task in checklist.object_maintenance_checklist_items:
		interval_days = cint(task.frequency_days)
		if interval_days <= 0:
			# A task without a valid frequency cannot be scheduled.
			continue

		current_date = getdate(base_date)
		guard = MAX_GENERATED_SLOTS
		while guard > 0:
			guard -= 1
			current_date = add_days(current_date, interval_days)
			if getdate(current_date) > stop_date:
				break

			planned_dt = get_datetime(f"{getdate(current_date)} {DEFAULT_EXECUTION_TIME}")
			if not _slot_exists(object_name, task.task_description, planned_dt):
				_create_slot(obj, task, planned_dt)
				created += 1

	return created


def _get_due_entry_names(lead_days, object_name=None):
	"""Open slots whose planned date falls inside the look-ahead window.

	The window is every Open slot due on or before ``today + lead_days`` (this
	naturally includes any past-due Open slots that still need a Work Order).
	Returns rows with ``name``, ``object`` and ``planned_execution_datetime``,
	ordered by object, datetime, name so slots can be grouped per object and day.
	"""
	window_end = get_datetime(f"{add_days(today(), lead_days)} 23:59:59")
	filters = {
		"status": STATUS_OPEN,
		"planned_execution_datetime": ["<=", window_end],
	}
	if object_name:
		filters["object"] = object_name

	return frappe.get_all(
		"Maintenance Schedule Entry",
		filters=filters,
		fields=["name", "object", "planned_execution_datetime"],
		order_by="object asc, planned_execution_datetime asc, name asc",
	)


def create_work_order_from_entries(entries):
	"""Create one Preventive Maintenance Work Order for the due slots of one
	object on one date.

	``entries`` are the Maintenance Schedule Entry documents of a single object
	and planned date. The Work Order checklist holds exactly one row per entry
	(never the full category template); each row is linked back to its entry.
	Row details come from the matching master checklist item (matched by task
	description) and fall back to the entry's own task and frequency. The Work
	Order's ``maintenance_schedule`` is the first entry (all share the date), and
	its own ``before_save`` fills the rest (space + location chain from the object).
	``priority`` and ``assigned_maintenance_team`` are optional and left blank.

	Returns the created Work Order document.
	"""
	first = entries[0]

	object_category = frappe.db.get_value("Object", first.object, "object_category")
	checklist_name = None
	if object_category:
		checklist_name = frappe.db.get_value(
			"Object Maintenance Checklist", {"object_category": object_category}, "name"
		)

	master_by_task = {}
	if checklist_name:
		master_items = frappe.get_all(
			"Object Maintenance Checklist Items",
			filters={"parent": checklist_name},
			fields=[
				"sequence_no", "task_description", "photo_required",
				"reference_image", "maintenance_frequency", "frequency_days",
			],
			order_by="idx asc",
		)
		for item in master_items:
			master_by_task.setdefault(item.task_description, item)

	work_order = frappe.get_doc(
		{
			"doctype": "Maintenance Work Order",
			"maintenance_type": "Preventive Maintenance",
			"status": STATUS_OPEN,
			"object": first.object,
			"maintenance_schedule": first.name,
			"object_maintenance_checklist": checklist_name,
		}
	)

	for entry in entries:
		master = master_by_task.get(entry.maintenance_task)
		if master:
			row = {
				"sequence_no": master.sequence_no,
				"task_description": master.task_description,
				"reference_image": master.reference_image,
				"maintenance_frequency": master.maintenance_frequency,
				"frequency_days": master.frequency_days,
				"is_required": master.photo_required or 0,
			}
		else:
			row = {
				"task_description": entry.maintenance_task,
				"maintenance_frequency": entry.maintenance_frequency,
				"frequency_days": entry.frequency_days,
				"is_required": 0,
			}
		row["maintenance_schedule_entry"] = entry.name
		work_order.append("object_maintenance_checklist_items", row)

	work_order.insert(ignore_permissions=True)
	return work_order


ENTRY_FIELDS = [
	"name",
	"object",
	"maintenance_task",
	"maintenance_frequency",
	"frequency_days",
	"planned_execution_datetime",
	"status",
	"work_order",
]


def _find_existing_work_orders(entry_names):
	"""``{entry: work_order}`` for entries a live Work Order already covers.

	A Work Order covers an entry when one of its checklist rows points at it, or (for
	Work Orders raised before the rows carried that link) when its
	``maintenance_schedule`` is the entry. Cancelled Work Orders are ignored.
	"""
	if not entry_names:
		return {}

	work_order = frappe.qb.DocType("Maintenance Work Order")
	checklist = frappe.qb.DocType("Maintenance Work Order Checklist")
	rows = (
		frappe.qb.from_(checklist)
		.join(work_order)
		.on(checklist.parent == work_order.name)
		.select(checklist.maintenance_schedule_entry, work_order.name)
		.where(checklist.parenttype == "Maintenance Work Order")
		.where(checklist.maintenance_schedule_entry.isin(entry_names))
		.where(work_order.docstatus < 2)
		.orderby(work_order.creation)
	).run()
	existing = {}
	for entry, name in rows:
		existing.setdefault(entry, name)

	for row in frappe.get_all(
		"Maintenance Work Order",
		filters={"maintenance_schedule": ["in", entry_names], "docstatus": ["<", 2]},
		fields=["name", "maintenance_schedule"],
		order_by="creation asc",
	):
		existing.setdefault(row.maintenance_schedule, row.name)

	return existing


def _process_group(names):
	"""Give the due entries of one object and date exactly one Work Order.

	All or nothing: the entries are locked, the Work Order is created and every entry
	is linked and flipped to 'Work Order Created' in one UPDATE, inside a savepoint.
	Any error rolls the savepoint back, so no Work Order is kept and the entries stay
	Open for the next run. Entries already covered by a live Work Order are linked to
	it instead of getting a new one.

	Known limit: when an existing Work Order covers only part of the group, the rest
	get a new Work Order rather than being appended to it.

	Returns 1 when a Work Order was created, else 0.
	"""
	save_point = f"mwo_{frappe.generate_hash(length=8)}"
	frappe.db.savepoint(save_point)
	try:
		# skip_locked: a concurrent run holding these rows is skipped, not waited on.
		rows = frappe.db.get_values(
			"Maintenance Schedule Entry",
			{"name": ["in", names]},
			ENTRY_FIELDS,
			as_dict=True,
			for_update=True,
			skip_locked=True,
			order_by="name asc",
		)
		if len(rows) != len(names):
			frappe.db.release_savepoint(save_point)
			return 0

		pending = [row for row in rows if row.status == STATUS_OPEN and not row.work_order]
		links = _find_existing_work_orders([row.name for row in pending])
		to_create = [row for row in pending if row.name not in links]

		created = 0
		if to_create:
			work_order = create_work_order_from_entries(to_create)
			links.update({row.name: work_order.name for row in to_create})
			created = 1

		for work_order_name in set(links.values()):
			frappe.db.set_value(
				"Maintenance Schedule Entry",
				{"name": ["in", [entry for entry, wo in links.items() if wo == work_order_name]]},
				{"work_order": work_order_name, "status": STATUS_WORK_ORDER_CREATED},
			)

		frappe.db.release_savepoint(save_point)
		return created
	except Exception:
		frappe.db.rollback(save_point=save_point)
		frappe.log_error(
			title="Maintenance Work Order Generation Failed",
			message=frappe.get_traceback(),
		)
		return 0


def generate_due_work_orders(object_name=None):
	"""Raise Work Orders for every 'Open' slot inside the lead-time window.

	Shared by the immediate on-submit routine (``object_name`` supplied) and the
	nightly scheduler (``object_name`` omitted -> all objects). Due slots are
	grouped by object and planned date and each group is handled by
	``_process_group``: one Work Order listing only its due task(s), created and
	linked atomically. A failed group is logged and retried on the next run
	without stopping the others.

	Returns the number of Work Orders created.
	"""
	lead_days = max(0, cint(_get_settings().work_order_generation_lead_time_days))

	groups = {}
	for row in _get_due_entry_names(lead_days, object_name):
		key = (row.object, getdate(row.planned_execution_datetime))
		groups.setdefault(key, []).append(row.name)

	# Rows arrive ordered by object, date, name, so groups lock in a stable order.
	return sum(_process_group(names) for names in groups.values())


def process_object_schedule(object_name):
	"""On-submit background routine for a new Maintenance Object.

	Runs the two routines in order:
	  1. Build Schedule    -> generate the empty 'Open' slots up to the months limit.
	  2. Catch Immediate Work -> raise Work Orders for any of those slots already
	     inside the Work Order lead-time window.
	"""
	build_schedule(object_name)
	generate_due_work_orders(object_name=object_name)
