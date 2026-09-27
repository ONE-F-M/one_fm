# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002605 / WI-002606: visa and PAM details reach the Employee without re-keying.

The Onboard Employee gains a Visa Request link and the fields that hang off it, and what
it fetched is carried onto the Employee when one is created from it.

Two departures from the BA site are deliberate and pinned here:

* **Types.** BA declared all six fields as Data. The Visa Request sources are Link,
  Currency and Date, and so are the Employee targets, so Data would store a salary as a
  string and a date as raw text and lose the PAM lookups. The matching types are used.
* **Where the expiry lands.** ``one_fm_date_of_issuance_of_visa``, which WI-002618
  relabels "Date of Visa Expiry" for exactly this reason - the field is the visa expiry
  now, and only its column name still says issuance. Renaming the column would break
  Work Permit's ``fetch_from`` and every report that names it, so it stays.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.hiring.utils import DEAD_VISA_REQUEST_STATES, get_visa_request_for_job_offer
from one_fm.hiring.doctype.onboard_employee.onboard_employee import (
	VISA_AND_PAM_FIELDS,
	set_visa_and_pam_details,
)

DOCTYPE = "Onboard Employee"


class TestTheFieldsAreOnTheForm(FrappeTestCase):
	"""AC: the six fields are available, fetched from the Visa Request."""

	EXPECTED = {
		"pam_designation": ("Link", "visa_request.custom_pam_designation_list"),
		"pam_file": ("Link", "visa_request.custom_pam_file"),
		"work_permit_salary": ("Currency", "visa_request.work_permit_salary"),
		"visa_centralized_number": ("Data", "visa_request.moi_reference_number"),
		"visa_reference_number": ("Data", "visa_request.visa_reference_number"),
		"visa_date_of_expiry": ("Date", "visa_request.visa_expiry_date"),
	}

	def test_each_field_exists_with_its_fetch(self):
		meta = frappe.get_meta(DOCTYPE)
		for fieldname, (fieldtype, fetch_from) in self.EXPECTED.items():
			field = meta.get_field(fieldname)
			self.assertIsNotNone(field, fieldname)
			self.assertEqual(field.fieldtype, fieldtype, fieldname)
			self.assertEqual(field.fetch_from, fetch_from, fieldname)

	def test_there_is_a_visa_request_to_fetch_from(self):
		# Every fetch above is rooted here; without the link none of them resolve.
		field = frappe.get_meta(DOCTYPE).get_field("visa_request")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Visa Request")

	def test_every_source_field_exists_on_visa_request(self):
		# A fetch_from naming a field that is not there fails silently - the value is
		# simply never set - so the other side is checked rather than assumed.
		source = frappe.get_meta("Visa Request")
		for fieldtype, fetch_from in self.EXPECTED.values():
			self.assertIsNotNone(source.get_field(fetch_from.split(".", 1)[1]), fetch_from)

	def test_the_moi_number_is_relabelled(self):
		# The criteria mark this one "(Already there*)" - it existed but was unconnected.
		field = frappe.get_meta(DOCTYPE).get_field("visa_centralized_number")
		self.assertEqual(field.label, "Visa Centralized Number (MOI Reference Number)")


class TestTheDetailsReachTheEmployee(FrappeTestCase):
	"""AC: the HR user does not re-enter what the onboarding already holds."""

	def test_every_target_exists_on_employee(self):
		employee = frappe.get_meta("Employee")
		for target in VISA_AND_PAM_FIELDS.values():
			self.assertIsNotNone(employee.get_field(target), target)

	def test_the_values_are_carried_over(self):
		onboarding = frappe._dict({
			"pam_file": "PAM-TEST-0001",
			"work_permit_salary": 450,
			"visa_centralized_number": "MOI-123",
			"visa_reference_number": "VR-456",
			"visa_date_of_expiry": "2027-01-31",
		})
		employee = frappe.new_doc("Employee")
		set_visa_and_pam_details(onboarding, employee)

		self.assertEqual(employee.pam_file, "PAM-TEST-0001")
		self.assertEqual(employee.work_permit_salary, 450)
		self.assertEqual(employee.one_fm_centralized_number, "MOI-123")
		self.assertEqual(employee.one_fm_visa_reference_number, "VR-456")
		self.assertEqual(employee.one_fm_date_of_issuance_of_visa, "2027-01-31")

	def test_an_onboarding_with_no_visa_request_blanks_nothing(self):
		# Not every onboarding has a Visa Request. Copying its empty fields over would
		# wipe details the Employee already carries from the Job Offer or the GRD flow.
		employee = frappe.new_doc("Employee")
		employee.one_fm_centralized_number = "ALREADY-SET"
		employee.work_permit_salary = 300

		set_visa_and_pam_details(frappe._dict(), employee)

		self.assertEqual(employee.one_fm_centralized_number, "ALREADY-SET")
		self.assertEqual(employee.work_permit_salary, 300)

	def test_pam_designation_keeps_its_own_fallback_chain(self):
		# It is handled separately in create_employee, where it falls back to Job Applicant
		# then ERF. Folding it into the plain copy would lose that.
		self.assertNotIn("pam_designation", VISA_AND_PAM_FIELDS)


class TestTheExpiryLandsOnTheRelabelledField(FrappeTestCase):
	def test_it_goes_to_the_field_wi_002618_relabels(self):
		self.assertEqual(
			VISA_AND_PAM_FIELDS["visa_date_of_expiry"], "one_fm_date_of_issuance_of_visa"
		)

	def test_that_field_is_labelled_as_the_expiry(self):
		# The two stories have to agree, or this writes an expiry into a field the form
		# still calls an issuance date. WI-002618 is the base of this branch.
		field = next(
			f for f in get_employee_custom_fields()["Employee"]
			if f["fieldname"] == "one_fm_date_of_issuance_of_visa"
		)
		self.assertEqual(field["label"], "Date of Visa Expiry")

	def test_work_permit_reads_that_same_field(self):
		# The consequence of the decision, asserted so it is visible: a Work Permit raised
		# for one of these employees shows the visa EXPIRY under "Date of Issuance of Visa".
		field = frappe.get_meta("Work Permit").get_field("date_of_issuance_of_visa")
		self.assertIsNotNone(field)
		self.assertEqual(field.fetch_from, "employee.one_fm_date_of_issuance_of_visa")


class TestTheVisaRequestIsFoundFromTheJobOffer(FrappeTestCase):
	"""The note added to WI-002606 on 2026-09-21.

	"when I click Onboard Employee from a Job Offer, the Visa Request associated with that
	specific offer is correctly fetched." The link field on its own does not do that - it
	is a plain Link, so somebody has to pick the record - so the onboarding is given it at
	creation, before the save that fetches everything hanging off it.
	"""

	def test_an_offer_with_no_visa_request_gets_nothing(self):
		self.assertIsNone(get_visa_request_for_job_offer("HR-OFF-DOES-NOT-EXIST"))

	def test_no_job_offer_is_not_an_error(self):
		# create_onboarding_from_job_offer is reached from paths where the offer may be
		# missing; this must return rather than query for an empty link.
		self.assertIsNone(get_visa_request_for_job_offer(None))
		self.assertIsNone(get_visa_request_for_job_offer(""))

	def test_a_live_request_beats_a_newer_rejected_one(self):
		# The case that makes "most recent" wrong. On live data HR-OFF-2026-00505-1 has a
		# Completed request from 1 Aug and a Rejected By Operator one from 3 Aug; the
		# onboarding must carry the Completed one.
		offer = frappe.get_all(
			"Visa Request",
			filters={"workflow_state": ["in", DEAD_VISA_REQUEST_STATES], "job_offer": ["is", "set"]},
			pluck="job_offer", limit=20)
		for name in offer:
			states = frappe.get_all("Visa Request", filters={"job_offer": name},
									fields=["name", "workflow_state"], order_by="creation desc")
			live = [r for r in states if r.workflow_state not in DEAD_VISA_REQUEST_STATES]
			if not live or len(states) < 2:
				continue
			self.assertIn(get_visa_request_for_job_offer(name), [r.name for r in live])
			return
		self.skipTest("no job offer on this site carries both a live and a dead Visa Request")

	def test_a_dead_request_is_better_than_an_empty_field(self):
		# Every request rejected: the offer still had one, and the officer is better off
		# seeing it than seeing nothing.
		for name in frappe.get_all("Visa Request", filters={"job_offer": ["is", "set"]},
								   pluck="job_offer", limit=60):
			states = frappe.get_all("Visa Request", filters={"job_offer": name}, pluck="workflow_state")
			if states and all(s in DEAD_VISA_REQUEST_STATES for s in states):
				self.assertIsNotNone(get_visa_request_for_job_offer(name))
				return
		self.skipTest("no job offer on this site has only dead Visa Requests")

	def test_the_creation_path_sets_it_before_saving(self):
		# Setting it after the save would leave every fetched field empty until somebody
		# opened the onboarding again - which is the whole complaint in the note.
		import inspect
		from one_fm.hiring import utils
		source = inspect.getsource(utils.create_onboarding_from_job_offer)
		set_at = source.index("o_employee.visa_request = get_visa_request_for_job_offer")
		self.assertLess(set_at, source.index("o_employee.save("))


class TestTheBackfillReadsTheMappingFromTheDoctype(FrappeTestCase):
	def test_every_fetched_field_is_discovered(self):
		# The patch derives the mapping from fetch_from rather than repeating it, so a
		# field added later is backfilled without anyone editing the patch.
		from one_fm.patches.v15_0.backfill_onboard_employee_visa_request import fetched_fields

		mapping = fetched_fields()
		self.assertEqual(
			set(mapping),
			{"pam_designation", "pam_file", "work_permit_salary",
			 "visa_centralized_number", "visa_reference_number", "visa_date_of_expiry"},
		)
		self.assertEqual(mapping["visa_date_of_expiry"], "visa_expiry_date")
		self.assertEqual(mapping["visa_centralized_number"], "moi_reference_number")
