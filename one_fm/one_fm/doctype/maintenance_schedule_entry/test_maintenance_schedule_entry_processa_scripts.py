# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Maintenance Schedule Entry processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one. The other Maintenance Schedule Entry tests read the rules from here through
rules(), and install_scripts() puts these bodies on the site for the hooks to run.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

# The Processa engine commits when an instance starts or fails. A test module starts this in
# setUpModule, so its records still roll back.
NO_COMMIT = patch("frappe.db.commit")

SCRIPTS = {
	"Build Maintenance Schedule": """# Builds the empty Open maintenance slots of submitted Objects, up to Schedule Generation (Months)
# in Maintenance Settings from today, one slot per checklist task each time its frequency comes round.
# The Object Lifecycle map runs it for the Object just submitted. The daily Maintenance Schedule
# Entry timer runs it for every submitted Object, so the schedule keeps rolling forward.
# A Maintenance Schedule Entry save runs prepare_entry, so a slot entered by hand is filled the same way.
# Slots are written with db_insert, because only System Manager may create a Schedule Entry.
DEFAULT_EXECUTION_TIME = "08:00:00"
# A mis-configured (tiny) frequency can never generate more slots than this per task.
MAX_GENERATED_SLOTS = 1000


# The category and the Space > Floor > Building > Site > Project chain from the Object, and the
# planned execution datetime. Fills only empty fields, so a manual value is kept.
def prepare_entry(entry):
	if not entry.object:
		return

	obj = frappe.db.get_value(
		"Object", entry.object,
		["object_category", "space", "last_service_date", "commissioning_date", "creation"],
		as_dict=True,
	)
	if not obj:
		return

	entry.object_category = entry.object_category or obj.object_category
	entry.space = entry.space or obj.space
	if entry.space:
		space = frappe.db.get_value(
			"Space", entry.space,
			["maintenance_floor", "building_name", "operations_site", "project"],
			as_dict=True,
		)
		if space:
			entry.maintenance_floor = entry.maintenance_floor or space.maintenance_floor
			entry.building = entry.building or space.building_name
			entry.operations_site = entry.operations_site or space.operations_site
			entry.project = entry.project or space.project

	# Last Service Date, else Commissioning Date, else the Object's creation, plus Frequency (Days), at 08:00.
	if not entry.planned_execution_datetime and frappe.utils.cint(entry.frequency_days):
		base_date = obj.last_service_date or obj.commissioning_date or frappe.utils.getdate(obj.creation)
		planned_date = frappe.utils.add_days(frappe.utils.getdate(base_date), frappe.utils.cint(entry.frequency_days))
		entry.planned_execution_datetime = frappe.utils.get_datetime(f"{planned_date} {DEFAULT_EXECUTION_TIME}")


def build_schedule(object_name):
	months = frappe.utils.cint(frappe.db.get_single_value("Maintenance Settings", "schedule_generation_months"))
	if months <= 0:
		return 0
	stop_date = frappe.utils.getdate(frappe.utils.add_months(frappe.utils.today(), months))

	obj = frappe.db.get_value("Object", object_name, ["name", "object_category", "last_service_date"], as_dict=True)
	checklist = obj and obj.object_category and frappe.db.get_value(
		"Object Maintenance Checklist", {"object_category": obj.object_category}, "name"
	)
	if not checklist:
		return 0

	created = 0
	for task in frappe.get_all(
		"Object Maintenance Checklist Items",
		filters={"parent": checklist, "parenttype": "Object Maintenance Checklist"},
		fields=["task_description", "maintenance_frequency", "frequency_days"],
		order_by="idx asc",
	):
		interval_days = frappe.utils.cint(task.frequency_days)
		if interval_days <= 0:
			continue

		# Step on from the latest slot already built for this task. Starting again from the base
		# date each day would move the dates of an Object never serviced, and duplicate its slots.
		latest = frappe.get_all(
			"Maintenance Schedule Entry",
			filters={"object": object_name, "maintenance_task": task.task_description},
			pluck="planned_execution_datetime",
			order_by="planned_execution_datetime desc",
			limit=1,
		)
		current_date = frappe.utils.getdate(latest[0] if latest and latest[0] else (obj.last_service_date or frappe.utils.today()))

		for _ in range(MAX_GENERATED_SLOTS):
			current_date = frappe.utils.getdate(frappe.utils.add_days(current_date, interval_days))
			if current_date > stop_date:
				break

			planned_dt = frappe.utils.get_datetime(f"{current_date} {DEFAULT_EXECUTION_TIME}")
			if frappe.db.exists("Maintenance Schedule Entry", {
				"object": object_name, "maintenance_task": task.task_description, "planned_execution_datetime": planned_dt,
			}):
				continue

			entry = frappe.get_doc({
				"doctype": "Maintenance Schedule Entry",
				"object": object_name,
				"status": "Open",
				"maintenance_task": task.task_description,
				"maintenance_frequency": task.maintenance_frequency,
				"frequency_days": task.frequency_days,
				"planned_execution_datetime": planned_dt,
			})
			prepare_entry(entry)
			entry.set_new_name()
			entry.set_user_and_timestamp()
			entry.db_insert()
			created += 1

	return created


# Only in a map: a save that runs prepare_entry has no bpmn_id. The Object map passes the Object it
# submitted. The timer passes no document, so every submitted Object is built.
if bpmn_id and doc.get("doctype") == "Object":
	result["slots_created"] = build_schedule(doc.name)
elif bpmn_id:
	result["slots_created"] = sum(
		build_schedule(name) for name in frappe.get_all("Object", filters={"docstatus": 1}, pluck="name")
	)
""",
	"Raise Due Work Orders": """# Raises one Preventive Maintenance Work Order per Object and planned date for the Open slots due
# within Work Order Generation Lead Time (Days) in Maintenance Settings, past-due slots included.
# The Object Lifecycle map runs it for the Object just submitted. The daily Maintenance Schedule
# Entry timer runs it for every Object.
# Each group is all or nothing inside a savepoint: a failure keeps no Work Order and leaves its
# slots Open for the next run, and is logged without stopping the other groups.

# The slots of each Work Order: one checklist row per slot, never the whole category template.
def create_work_order(entries):
	first = entries[0]
	object_category = frappe.db.get_value("Object", first.object, "object_category")
	checklist_name = object_category and frappe.db.get_value(
		"Object Maintenance Checklist", {"object_category": object_category}, "name"
	)

	master_by_task = {}
	if checklist_name:
		for item in frappe.get_all(
			"Object Maintenance Checklist Items",
			filters={"parent": checklist_name, "parenttype": "Object Maintenance Checklist"},
			fields=["sequence_no", "task_description", "photo_required", "reference_image",
				"maintenance_frequency", "frequency_days"],
			order_by="idx asc",
		):
			master_by_task.setdefault(item.task_description, item)

	work_order = frappe.get_doc({
		"doctype": "Maintenance Work Order",
		"maintenance_type": "Preventive Maintenance",
		"status": "Open",
		"object": first.object,
		"maintenance_schedule": first.name,
		"object_maintenance_checklist": checklist_name or None,
	})
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

	work_order.insert()
	return work_order


# {slot: Work Order} for slots a live Work Order already covers, through a checklist row or, for
# Work Orders older than that link, through maintenance_schedule. Cancelled Work Orders do not count.
def existing_work_orders(entry_names):
	if not entry_names:
		return {}

	work_order = frappe.qb.DocType("Maintenance Work Order")
	checklist = frappe.qb.DocType("Maintenance Work Order Checklist")
	rows = (
		frappe.qb.from_(checklist)
		.join(work_order).on(checklist.parent == work_order.name)
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


# The slots of one Object and date get exactly one Work Order, and are linked and set to
# Work Order Created. Known limit: when a live Work Order covers only part of the group, the rest
# get a new Work Order rather than being added to it.
def process_group(names):
	save_point = "mwo_" + frappe.generate_hash(length=8)
	frappe.db.savepoint(save_point)
	try:
		# skip_locked: a concurrent run holding these slots is skipped, not waited on.
		rows = frappe.db.get_values(
			"Maintenance Schedule Entry",
			{"name": ["in", names]},
			["name", "object", "maintenance_task", "maintenance_frequency", "frequency_days",
				"planned_execution_datetime", "status", "work_order"],
			as_dict=True, for_update=True, skip_locked=True, order_by="name asc",
		)
		if len(rows) != len(names):
			frappe.db.release_savepoint(save_point)
			return 0

		pending = [row for row in rows if row.status == "Open" and not row.work_order]
		links = existing_work_orders([row.name for row in pending])
		to_create = [row for row in pending if row.name not in links]

		created = 0
		if to_create:
			work_order = create_work_order(to_create)
			links.update({row.name: work_order.name for row in to_create})
			created = 1

		for work_order_name in set(links.values()):
			frappe.db.set_value(
				"Maintenance Schedule Entry",
				{"name": ["in", [entry for entry, wo in links.items() if wo == work_order_name]]},
				{"work_order": work_order_name, "status": "Work Order Created"},
			)

		frappe.db.release_savepoint(save_point)
		return created
	except Exception:
		frappe.db.rollback(save_point=save_point)
		frappe.log_error(title="Maintenance Work Order Generation Failed", message=frappe.get_traceback())
		return 0


def raise_due_work_orders(object_name=None):
	lead_days = max(0, frappe.utils.cint(
		frappe.db.get_single_value("Maintenance Settings", "work_order_generation_lead_time_days")
	))
	filters = {
		"status": "Open",
		"planned_execution_datetime": ["<=", frappe.utils.get_datetime(f"{frappe.utils.add_days(frappe.utils.today(), lead_days)} 23:59:59")],
	}
	if object_name:
		filters["object"] = object_name

	groups = {}
	for row in frappe.get_all(
		"Maintenance Schedule Entry",
		filters=filters,
		fields=["name", "object", "planned_execution_datetime"],
		order_by="object asc, planned_execution_datetime asc, name asc",
	):
		groups.setdefault((row.object, frappe.utils.getdate(row.planned_execution_datetime)), []).append(row.name)

	# Slots arrive ordered by object, date and name, so the groups lock in a stable order.
	return sum(process_group(names) for names in groups.values())


# The Object map passes the Object it submitted. The timer passes no document, so every Object is covered.
if bpmn_id and doc.get("doctype") == "Object":
	result["work_orders_created"] = raise_due_work_orders(doc.name)
elif bpmn_id:
	result["work_orders_created"] = raise_due_work_orders()
""",
}


class Rules:
	"""A script's functions and constants as attributes. The attributes are the script's own
	namespace, so patching one (patch.object(rules, "fn")) also changes what the other
	functions of the script call."""


def rules(script_name):
	"""The functions and constants a script defines, without taking its map step."""
	namespace = {"frappe": frappe, "doc": frappe._dict(), "task_data": {}, "result": {},
		"context_doctype": "", "context_docname": "", "bpmn_id": ""}
	exec(SCRIPTS[script_name], namespace)
	found = Rules()
	found.__dict__ = namespace
	return found


def run(script_name, doc=None, **task_data):
	"""Run a script the way the Processa engine does, as a map step, and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc or frappe._dict(),
		"task_data": task_data,
		"result": result,
		"context_doctype": doc.doctype if doc else "",
		"context_docname": doc.name if doc else "",
		"bpmn_id": "test",
	}
	namespace.update(task_data)
	exec(SCRIPTS[script_name], namespace)
	return result


def install_scripts():
	"""Put these bodies on the site, so the hooks under test run the reviewed scripts."""
	for name, body in SCRIPTS.items():
		if frappe.db.exists("Server Script", name):
			frappe.db.set_value("Server Script", name, {"script": body, "disabled": 0}, update_modified=False)
		else:
			frappe.get_doc({"doctype": "Server Script", "name": name, "script_type": "API",
				"api_method": frappe.scrub(name), "script": body}).db_insert()


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is not None:
				self.assertEqual(saved.strip(), body.strip(), msg=name)
