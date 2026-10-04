# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002594: an Employee master change reaching the GRD forms still in flight."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd import employee_sync
from one_fm.grd.employee_sync import (
	CANCELLED,
	FIELD_MAP,
	TITLED_DOCTYPES,
	WATCHED_FIELDS,
	sync_to_sub_documents,
)


class _Employee:
	"""Just enough Employee to drive the handler: what changed, and what it now holds."""

	def __init__(self, name="HR-EMP-04448", changed=(), **values):
		self.name = name
		self.flags = frappe._dict(in_insert=False)
		self._changed = set(changed)
		self._values = values

	def has_value_changed(self, fieldname):
		return fieldname in self._changed

	def get(self, fieldname):
		return self._values.get(fieldname)


class _Recorder:
	"""Stands in for the two db calls, so the rule can be run without a fixture."""

	def __init__(self, rows_by_doctype):
		self.rows_by_doctype = rows_by_doctype
		self.queried = []
		self.written = []

	def get_all(self, doctype, filters=None, fields=None):
		self.queried.append((doctype, filters))
		return [dict(row) for row in self.rows_by_doctype.get(doctype, [])]

	def set_value(self, doctype, name, values, update_modified=None):
		self.written.append((doctype, name, values, update_modified))


class _SyncTestCase(FrappeTestCase):
	def _run(self, employee, rows_by_doctype=None):
		recorder = _Recorder(rows_by_doctype or {})
		original_get_all = employee_sync.frappe.get_all
		original_set_value = employee_sync.frappe.db.set_value
		employee_sync.frappe.get_all = recorder.get_all
		employee_sync.frappe.db.set_value = recorder.set_value
		try:
			sync_to_sub_documents(employee)
		finally:
			employee_sync.frappe.get_all = original_get_all
			employee_sync.frappe.db.set_value = original_set_value
		return recorder


class TestWhenItRuns(_SyncTestCase):
	def test_a_save_that_touched_nothing_copied_does_nothing(self):
		"""An Employee is saved constantly; most saves move none of these four."""
		recorder = self._run(_Employee(changed=["cell_number"]))
		self.assertEqual(recorder.queried, [])
		self.assertEqual(recorder.written, [])

	def test_an_insert_does_nothing(self):
		"""Nothing has been raised for an employee that did not exist a moment ago."""
		employee = _Employee(changed=WATCHED_FIELDS, one_fm_civil_id="288010101234")
		employee.flags.in_insert = True
		recorder = self._run(employee)
		self.assertEqual(recorder.written, [])

	def test_a_civil_id_reaches_all_four_doctypes(self):
		employee = _Employee(changed=["one_fm_civil_id"], one_fm_civil_id="288010101234")
		recorder = self._run(employee)
		self.assertEqual(
			[doctype for doctype, _filters in recorder.queried],
			["Work Permit", "Medical Insurance", "Residency", "PACI"],
		)

	def test_a_salary_change_reaches_only_the_work_permit(self):
		"""Only the Work Permit carries the work permit salary."""
		employee = _Employee(changed=["work_permit_salary"], work_permit_salary="450")
		recorder = self._run(employee)
		self.assertEqual([doctype for doctype, _filters in recorder.queried], ["Work Permit"])


class TestWhatItWrites(_SyncTestCase):
	def test_it_writes_the_fieldname_each_doctype_uses(self):
		"""Residency spells the Civil ID one_fm_civil_id; the other three spell it civil_id."""
		employee = _Employee(changed=["one_fm_civil_id"], one_fm_civil_id="288010101234")
		rows = {
			doctype: [{"name": f"{doctype}-0001", "civil_id": "", "one_fm_civil_id": ""}]
			for doctype in FIELD_MAP
		}
		written = {
			doctype: values for doctype, _name, values, _mod in self._run(employee, rows).written
		}
		self.assertEqual(written["Residency"]["one_fm_civil_id"], "288010101234")
		for doctype in ("Work Permit", "Medical Insurance", "PACI"):
			self.assertEqual(written[doctype]["civil_id"], "288010101234")

	def test_the_pam_file_number_lands_on_residencys_company_field(self):
		employee = _Employee(changed=["pam_file_number"], pam_file_number="2921143")
		rows = {"Residency": [{"name": "RES-0001"}]}
		written = self._run(employee, rows).written
		self.assertEqual(written[0][2]["company_pam_file_number"], "2921143")

	def test_a_new_civil_id_re_titles_the_two_derived_doctypes(self):
		"""db_set writes past the controller, so the title WI-002593 derives on save has
		to be derived here as well - and a Civil ID arriving is exactly why it changes."""
		employee = _Employee(changed=["one_fm_civil_id"], one_fm_civil_id="288010101234")
		rows = {
			doctype: [{"name": f"{doctype}-0001", "civil_id": "", "employee_id": "EMP-0001"}]
			for doctype in FIELD_MAP
		}
		written = {
			doctype: values for doctype, _name, values, _mod in self._run(employee, rows).written
		}
		for doctype in TITLED_DOCTYPES:
			self.assertEqual(written[doctype]["title"], "288010101234")
		for doctype in ("Medical Insurance", "Residency"):
			self.assertNotIn("title", written[doctype])

	def test_it_does_not_bump_modified(self):
		"""The operator holding the form did not touch it, and the GRD lists sort by it."""
		employee = _Employee(changed=["one_fm_civil_id"], one_fm_civil_id="288010101234")
		rows = {"PACI": [{"name": "PACI-0001"}]}
		self.assertIs(self._run(employee, rows).written[0][3], False)


class TestWhatItLeavesAlone(_SyncTestCase):
	def test_only_unsubmitted_records_are_asked_for(self):
		"""A submitted form is what went to the ministry. Correcting a value afterwards
		does not change what was filed."""
		employee = _Employee(changed=["one_fm_civil_id"], one_fm_civil_id="288010101234")
		for _doctype, filters in self._run(employee).queried:
			self.assertIn(["docstatus", "=", 0], filters)

	def test_cancelled_records_are_excluded_by_name(self):
		"""The GRD workflows all give Cancelled a draft docstatus, so docstatus alone
		would keep writing to closed records."""
		employee = _Employee(changed=["one_fm_civil_id"], one_fm_civil_id="288010101234")
		for _doctype, filters in self._run(employee).queried:
			self.assertIn(["workflow_state", "!=", CANCELLED], filters)


class TestTheMapMatchesTheDocTypes(FrappeTestCase):
	def test_every_source_is_a_field_on_employee(self):
		meta = frappe.get_meta("Employee")
		for fieldname in WATCHED_FIELDS:
			self.assertTrue(meta.get_field(fieldname), fieldname)

	def test_every_target_is_a_field_on_its_doctype(self):
		"""A target that is not a field is a write that raises, inside an Employee save."""
		for doctype, field_map in FIELD_MAP.items():
			meta = frappe.get_meta(doctype)
			for target in field_map.values():
				self.assertTrue(meta.get_field(target), f"{doctype}.{target}")

	def test_every_doctype_can_be_filtered_on_its_workflow_state(self):
		for doctype in FIELD_MAP:
			self.assertTrue(frappe.get_meta(doctype).get_field("workflow_state"), doctype)

	def test_the_handler_is_registered_on_employee(self):
		from one_fm import hooks

		self.assertIn(
			"one_fm.grd.employee_sync.sync_to_sub_documents",
			hooks.doc_events["Employee"]["on_update"],
		)
