# Copyright (c) 2020, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from one_fm.legal.doctype.penalty_issuance.penalty_issuance import PenaltyIssuance, submit_through_process
from one_fm.patches.v15_0.move_penalty_issuance_to_processa import ISSUER_ROLES, allow_issuers_to_create
from one_fm.patches.v15_0.move_legal_investigation_lifecycle_to_processa import set_third_party_damage


def make_penalty_issuance(**fields):
	employee = frappe.db.get_value("Employee", {"status": "Active"}, ["name", "employee_name", "designation"])
	penalty_type = frappe.db.get_value("Penalty Type", {})
	if not employee or not penalty_type:
		raise frappe.DoesNotExistError("An active Employee and a Penalty Type are needed")

	return frappe.get_doc(
		{
			"doctype": "Penalty Issuance",
			"penalty_category": "Accomodation",
			"penalty_location": "Camp",
			"penalty_occurence_time": add_to_date(now_datetime(), hours=-1),
			"employees": [{"employee_id": employee[0], "employee_name": employee[1], "designation": employee[2]}],
			"penalty_issuance_details": [{"penalty_type": penalty_type}],
			**fields,
		}
	)


class TestPenaltyIssuance(FrappeTestCase):
	def test_submitting_no_longer_routes_in_the_controller(self):
		for method in ("on_submit", "issue_penalty", "open_legal_investigation"):
			self.assertFalse(hasattr(PenaltyIssuance, method), msg=method)

	def test_submit_through_process_submits(self):
		try:
			issuance = make_penalty_issuance().insert(ignore_permissions=True)
		except frappe.DoesNotExistError as error:
			self.skipTest(str(error))

		submit_through_process(issuance)

		self.assertEqual(frappe.db.get_value("Penalty Issuance", issuance.name, "docstatus"), 1)
		self.assertFalse(frappe.db.exists("Penalty", {"penalty_issuance": issuance.name}))

	def test_legacy_damage_flags_become_third_party_damage(self):
		if not frappe.db.has_column("Penalty Issuance", "company_damage"):
			self.skipTest("Legacy damage columns are not on this site")
		try:
			flagged = make_penalty_issuance().insert(ignore_permissions=True)
			clean = make_penalty_issuance().insert(ignore_permissions=True)
		except frappe.DoesNotExistError as error:
			self.skipTest(str(error))
		table = frappe.qb.DocType("Penalty Issuance")
		frappe.qb.update(table).set(table.company_damage, 1).where(table.name == flagged.name).run()

		set_third_party_damage("Penalty Issuance")

		self.assertEqual(frappe.db.get_value("Penalty Issuance", flagged.name, "third_party_damage"), 1)
		self.assertEqual(frappe.db.get_value("Penalty Issuance", clean.name, "third_party_damage"), 0)

	def test_issuers_may_create_what_the_process_creates(self):
		allow_issuers_to_create("Legal Investigation", "Penalty")
		for doctype in ("Legal Investigation", "Penalty"):
			for role in ISSUER_ROLES:
				with self.subTest(doctype=doctype, role=role):
					self.assertEqual(
						frappe.db.get_value(
							"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0}, "create"
						),
						1,
					)
