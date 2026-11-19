# Copyright (c) 2026, oneaborance and contributors
# See license.txt

import contextlib
import io

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, today

from one_fm.operations.doctype.route_plan.route_plan import get_plan_rows
from one_fm.patches.v15_0 import route_plan_assignment_standalone as patch_module

ROLES = (
	"System Manager",
	"Transportation Supervisor",
	"Transportation Manager",
	"Operations Manager",
)


def make_route_plan(rows=(), title=None, **header):
	"""Insert a Route Plan and its assignments; returns the plan name.

	Rows are written as they come, without the plan-wide rules: a test that wants the
	rules runs PlanRules itself or goes through the page save.
	"""
	plan = frappe.get_doc({
		"doctype": "Route Plan",
		"title": title or frappe.generate_hash("RP-TEST", 8),
		"status": "Draft",
		"effective_from": today(),
		**header,
	})
	plan.flags.ignore_mandatory = True
	plan.insert(ignore_permissions=True)
	for idx, row in enumerate(rows, start=1):
		insert_assignment(plan.name, row, idx=idx)
	return plan.name


def insert_assignment(plan, values, idx=None):
	"""One Route Plan Assignment on ``plan``; fixture vehicles need not exist."""
	doc = frappe.get_doc({
		**{key: value for key, value in dict(values).items() if key not in ("name", "doctype")},
		"doctype": "Route Plan Assignment",
		"route_plan": plan,
		"idx": idx,
	})
	doc.flags.plan_checked = True
	doc.flags.ignore_links = True
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc


def make_card_shipment(headcount, direction="Outward"):
	"""A shipment the seat rules can weigh: it boards at a camp and drops at a site.

	Returns None when the site has no Accommodation or Location to hang it on. Without a
	camp and a stop the run's stop walk is empty and every bus reads as carrying nobody.
	"""
	camp = frappe.get_all("Accommodation", limit=1, pluck="name")
	site = frappe.get_all("Location", limit=1, pluck="name")
	if not (camp and site):
		return None
	doc = frappe.new_doc("Transportation Shipment")
	doc.update({
		"status": "Unassigned", "trip_direction": direction, "accommodation": camp[0],
		"stop_location": site[0], "start_time": "08:00:00", "end_time": "17:00:00",
		"generation_key": frappe.generate_hash("TS-RPA", 10),
	})
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
	frappe.db.set_value("Transportation Shipment", doc.name, "headcount", headcount)
	return doc.name


def _child_rows(plan, rows):
	"""Write ``rows`` the way they were stored while this was a child table of ``plan``."""
	now = now_datetime()
	fields = ["name", "parent", "parenttype", "parentfield", "idx", "card_id", "vehicle",
			  "direction", "trip_group", "stop_index", "start_time", "headcount",
			  "creation", "modified", "owner", "modified_by"]
	values, names = [], []
	for idx, row in enumerate(rows, start=1):
		name = frappe.generate_hash(length=10)
		names.append(name)
		values.append([
			name, row.get("parent", plan), "Route Plan", "assignments", row.get("idx", idx),
			row["card_id"], row.get("vehicle", "V-1"), row.get("direction", "OUTBOUND"),
			row.get("trip_group"), row.get("stop_index", 0), row.get("start_time"),
			row.get("headcount", 1), now, now, "Administrator", "Administrator",
		])
	frappe.db.bulk_insert("Route Plan Assignment", fields=fields, values=values)
	return names


def _run_patch():
	out = io.StringIO()
	with contextlib.redirect_stdout(out):
		patch_module.execute()
	return out.getvalue()


def _snapshot(names):
	return frappe.db.get_values(
		"Route Plan Assignment", {"name": ["in", names]},
		["name", "idx", "card_id", "vehicle", "direction", "trip_group", "stop_index",
		 "start_time", "headcount", "modified"],
		as_dict=True, order_by="name asc",
	)


class TestTheChildRowsBecomeRecords(FrappeTestCase):
	"""The patch copies each child row's parent into route_plan and nothing else."""

	def setUp(self):
		if not frappe.db.has_column("Route Plan Assignment", "parent"):
			self.skipTest("this site never had Route Plan Assignment as a child table")
		self.plan = make_route_plan()
		# Two runs whose stop numbers and start times both disagree with the table order.
		self.rows = [
			{"card_id": "C-A3", "trip_group": "T-A", "stop_index": 3, "start_time": "2026-11-01T07:00:00Z"},
			{"card_id": "C-B1", "trip_group": "T-B", "stop_index": 1, "start_time": "2026-11-01T05:00:00Z"},
			{"card_id": "C-A1", "trip_group": "T-A", "stop_index": 1, "start_time": "2026-11-01T09:00:00Z"},
			{"card_id": "C-B2", "trip_group": "T-B", "stop_index": 0, "start_time": "2026-11-01T04:00:00Z"},
			{"card_id": "C-A2", "trip_group": "T-A", "stop_index": 2, "start_time": "2026-11-01T06:00:00Z"},
		]
		self.names = _child_rows(self.plan, self.rows)

	def test_every_row_is_linked_with_its_values_unchanged(self):
		before = _snapshot(self.names)

		log = _run_patch()

		self.assertEqual(_snapshot(self.names), before)
		linked = frappe.get_all("Route Plan Assignment", filters={"name": ["in", self.names]},
								pluck="route_plan")
		self.assertEqual(set(linked), {self.plan})
		self.assertIn("linked", log)
		self.assertIn("updated", log)

	def test_a_second_run_changes_nothing(self):
		_run_patch()
		once = _snapshot(self.names)

		log = _run_patch()

		self.assertEqual(_snapshot(self.names), once)
		self.assertIn("updated 0", log)

	def test_a_row_whose_plan_is_gone_is_listed_and_left(self):
		(orphan,) = _child_rows(self.plan, [{"card_id": "C-ORPHAN", "parent": "RP-DOES-NOT-EXIST"}])

		log = _run_patch()

		self.assertIsNone(frappe.db.get_value("Route Plan Assignment", orphan, "route_plan"))
		self.assertIn(orphan, log)

	def test_a_repeated_card_keeps_only_its_first_row(self):
		(repeat,) = _child_rows(self.plan, [{"card_id": "C-A3", "trip_group": "T-A", "idx": 99}])

		log = _run_patch()

		self.assertIsNone(frappe.db.get_value("Route Plan Assignment", repeat, "route_plan"))
		self.assertEqual(frappe.db.get_value("Route Plan Assignment", self.names[0], "route_plan"), self.plan)
		self.assertIn(repeat, log)

	def test_the_stops_of_each_trip_come_out_in_the_order_they_were_shown(self):
		# The child table was always read by idx, so that is the order the board, the
		# manifest and the leg walk saw. The records must read back the same way.
		def by_trip(rows):
			trips = {}
			for row in rows:
				trips.setdefault(row.trip_group, []).append(row.card_id)
			return trips

		as_child = frappe.get_all(
			"Route Plan Assignment", filters={"name": ["in", self.names]},
			fields=["card_id", "trip_group"], order_by="idx asc",
		)

		_run_patch()

		self.assertEqual(by_trip(get_plan_rows(self.plan)), by_trip(as_child))
		self.assertEqual(by_trip(as_child), {
			"T-A": ["C-A3", "C-A1", "C-A2"], "T-B": ["C-B1", "C-B2"],
		})

	def test_rollback_turns_new_records_back_into_child_rows(self):
		_run_patch()
		new = insert_assignment(self.plan, {"card_id": "C-NEW", "vehicle": "V-1", "direction": "OUTBOUND"})

		with contextlib.redirect_stdout(io.StringIO()):
			patch_module.rollback()

		parent = frappe.qb.DocType("Route Plan Assignment")
		row = (
			frappe.qb.from_(parent).select(parent.parent, parent.parenttype, parent.parentfield)
			.where(parent.name == new.name)
		).run(as_dict=True)[0]
		self.assertEqual((row.parent, row.parenttype, row.parentfield),
						 (self.plan, "Route Plan", "assignments"))


class TestTheRecordShape(FrappeTestCase):
	def test_it_is_a_record_with_a_required_link_to_its_plan(self):
		meta = frappe.get_meta("Route Plan Assignment")
		field = meta.get_field("route_plan")

		self.assertFalse(meta.istable)
		self.assertEqual((field.fieldtype, field.options, field.reqd), ("Link", "Route Plan", 1))
		self.assertEqual(meta.autoname, "format:RPA-{#######}")

	def test_the_route_plan_form_no_longer_embeds_them(self):
		meta = frappe.get_meta("Route Plan")

		self.assertIsNone(meta.get_field("assignments"))
		self.assertIn("Route Plan Assignment", [link.link_doctype for link in meta.links])

	def test_the_common_lookups_are_indexed(self):
		table = "tabRoute Plan Assignment"
		for column in ("route_plan", "vehicle", "trip_group", "transportation_shipment"):
			self.assertTrue(frappe.db.get_column_index(table, column), column)
		self.assertTrue(frappe.db.has_index(table, "route_plan_vehicle_index"))

	def test_a_card_is_placed_once_per_plan(self):
		plan = make_route_plan()
		insert_assignment(plan, {"card_id": "C-1", "vehicle": "V-1", "direction": "OUTBOUND"})

		with self.assertRaises(frappe.UniqueValidationError):
			insert_assignment(plan, {"card_id": "C-1", "vehicle": "V-2", "direction": "OUTBOUND"})

	def test_new_records_get_readable_names(self):
		plan = make_route_plan()

		row = insert_assignment(plan, {"card_id": "C-1", "vehicle": "V-1", "direction": "OUTBOUND"})

		self.assertTrue(row.name.startswith("RPA-"), row.name)

	def test_deleting_a_plan_deletes_its_assignments(self):
		plan = make_route_plan([{"card_id": "C-1", "vehicle": "V-1", "direction": "OUTBOUND"}])

		frappe.delete_doc("Route Plan", plan, ignore_permissions=True)

		self.assertFalse(frappe.db.exists("Route Plan Assignment", {"route_plan": plan}))


class TestWhoMayChangeAssignments(FrappeTestCase):
	"""Whoever could change a plan's rows by writing the plan can change the records."""

	def _user(self, role):
		email = f"rpa-{frappe.scrub(role or 'nobody')}@example.com"
		if not frappe.db.exists("User", email):
			user = frappe.get_doc({
				"doctype": "User", "email": email, "first_name": role or "Nobody",
				"send_welcome_email": 0, "roles": [{"role": role}] if role else [],
			})
			user.flags.ignore_permissions = True
			user.insert()
		return email

	def test_each_planning_role_can_read_write_create_and_delete(self):
		for role in ROLES:
			user = self._user(role)
			for ptype in ("read", "write", "create", "delete"):
				self.assertTrue(
					frappe.has_permission("Route Plan Assignment", ptype, user=user),
					f"{role} lacks {ptype}",
				)

	def test_a_user_without_those_roles_cannot(self):
		user = self._user(None)
		for ptype in ("read", "write", "create", "delete"):
			self.assertFalse(frappe.has_permission("Route Plan Assignment", ptype, user=user))
