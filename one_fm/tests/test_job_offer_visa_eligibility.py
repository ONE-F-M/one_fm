# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002599: a Visa Request is only offered for an applicant who can be issued one.

Two rules, both of them dates: the passport must have at least 18 months left, and the
applicant must be at least 21. Neither is new policy - what is new is that the Job Offer
now knows enough to check before offering the button.

The rule itself lives in job_offer.js, so the tests below RUN it rather than grep it. A
grep passes happily on an off-by-one, and both of these rules are boundaries: "18 months
from today" and "21 years old" are exactly the places an inclusive/exclusive slip hides.
"""

import json
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, getdate, today

from one_fm.custom.custom_field.job_offer import get_job_offer_custom_fields

HARNESS = frappe.get_app_path("one_fm", "tests", "js", "visa_request_blockers_harness.js")
TODAY = "2026-09-18"

PASSPORT_MESSAGE = (
	"The applicant's passport must be valid for at least 18 more months from today. "
	"The Visa Request cannot be created"
)
AGE_MESSAGE = (
	"The applicant must be at least 21 years old to create a Visa Request. "
	"The Visa Request cannot be created."
)


def blockers(offer=None, applicant=None):
	"""Run the shipped rule against fixed dates and return what it would say."""
	out = subprocess.run(
		["node", HARNESS, json.dumps(offer or {}), json.dumps(applicant or {})],
		capture_output=True,
		text=True,
		env={"TODAY": TODAY, "PATH": "/usr/bin:/bin:/usr/local/bin"},
		check=True,
	)
	return json.loads(out.stdout)


class TestTheRuleItself(FrappeTestCase):
	"""Today is pinned to 2026-09-18, so +18 months is 2028-03-18 and -21 years is
	2005-09-18."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not shutil.which("node"):
			raise cls.failureException("node is needed to run the shipped rule")

	def test_an_eligible_applicant_is_not_blocked(self):
		self.assertEqual(
			blockers(applicant={"one_fm_passport_expire": "2030-01-01",
								"one_fm_date_of_birth": "1990-01-01"}),
			[],
		)

	def test_a_passport_with_exactly_eighteen_months_left_is_enough(self):
		# "at least 18 months" - the boundary belongs to the applicant.
		self.assertEqual(
			blockers(applicant={"one_fm_passport_expire": "2028-03-18",
								"one_fm_date_of_birth": "1990-01-01"}),
			[],
		)

	def test_a_passport_one_day_short_is_not(self):
		self.assertEqual(
			blockers(applicant={"one_fm_passport_expire": "2028-03-17",
								"one_fm_date_of_birth": "1990-01-01"}),
			[PASSPORT_MESSAGE],
		)

	def test_an_applicant_who_turns_twenty_one_today_is_old_enough(self):
		self.assertEqual(
			blockers(applicant={"one_fm_passport_expire": "2030-01-01",
								"one_fm_date_of_birth": "2005-09-18"}),
			[],
		)

	def test_an_applicant_who_turns_twenty_one_tomorrow_is_not(self):
		self.assertEqual(
			blockers(applicant={"one_fm_passport_expire": "2030-01-01",
								"one_fm_date_of_birth": "2005-09-19"}),
			[AGE_MESSAGE],
		)

	def test_both_failings_are_reported_together(self):
		# A recruiter who fixes the passport should not then discover the age.
		self.assertEqual(
			blockers(applicant={"one_fm_passport_expire": "2027-01-01",
								"one_fm_date_of_birth": "2010-01-01"}),
			[PASSPORT_MESSAGE, AGE_MESSAGE],
		)

	def test_the_messages_are_the_ones_the_notes_specify(self):
		reported = blockers(applicant={"one_fm_passport_expire": "2027-01-01",
									   "one_fm_date_of_birth": "2010-01-01"})
		self.assertIn(PASSPORT_MESSAGE, reported)
		self.assertIn(AGE_MESSAGE, reported)


class TestWhereTheDatesAreReadFrom(FrappeTestCase):
	def test_the_job_offers_own_copy_is_what_is_checked(self):
		# The criterion says "Given the Job Offer contains ...".
		self.assertEqual(
			blockers(
				offer={"one_fm_passport_expire": "2030-01-01", "one_fm_date_of_birth": "1990-01-01"},
				applicant={"one_fm_passport_expire": "2027-01-01", "one_fm_date_of_birth": "2010-01-01"},
			),
			[],
		)

	def test_the_applicant_stands_in_when_the_offer_has_nothing(self):
		# This is not a nicety. fetch_from runs on validate, and a submitted Job Offer never
		# validates again - so every offer submitted before these fields existed has them
		# empty, and there are over a thousand of those. Without this fallback the rule
		# would pass every one of them.
		self.assertEqual(
			blockers(applicant={"one_fm_passport_expire": "2027-01-01",
								"one_fm_date_of_birth": "1990-01-01"}),
			[PASSPORT_MESSAGE],
		)

	def test_a_date_nobody_has_is_not_a_date_that_fails(self):
		# Deliberate: blocking on a blank would take the button away from applicants nobody
		# has said anything about, which is a different change from the one asked for.
		self.assertEqual(blockers(), [])
		self.assertEqual(blockers(applicant={"one_fm_date_of_birth": "1990-01-01"}), [])
		self.assertEqual(blockers(applicant={"one_fm_passport_expire": "2030-01-01"}), [])


class TestTheFieldsOnTheJobOffer(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.fields = {f["fieldname"]: f for f in get_job_offer_custom_fields()["Job Offer"]}

	def test_every_field_the_story_names_is_defined(self):
		for fieldname in (
			"one_fm_passport_number",
			"one_fm_passport_holder_of",
			"one_fm_passport_issued",
			"one_fm_passport_expire",
			"one_fm_date_of_birth",
		):
			self.assertIn(fieldname, self.fields)

	def test_each_one_fetches_from_the_job_applicant(self):
		for fieldname in (
			"one_fm_passport_number",
			"one_fm_passport_holder_of",
			"one_fm_passport_issued",
			"one_fm_passport_expire",
			"one_fm_date_of_birth",
		):
			self.assertEqual(
				self.fields[fieldname]["fetch_from"],
				f"job_applicant.{fieldname}",
				msg=fieldname,
			)

	def test_the_source_fields_really_exist_on_the_job_applicant(self):
		# A fetch_from pointing at nothing fails silently, which is the worst shape for this
		# to be wrong in - the field simply stays blank and the rule passes everyone.
		meta = frappe.get_meta("Job Applicant")
		for fieldname in (
			"one_fm_passport_number",
			"one_fm_passport_holder_of",
			"one_fm_passport_issued",
			"one_fm_passport_expire",
			"one_fm_date_of_birth",
		):
			self.assertIsNotNone(meta.get_field(fieldname), msg=fieldname)

	def test_they_are_read_only(self):
		# The Job Applicant is where these are maintained. A recruiter editing the copy here
		# would change who is eligible without changing what it was checked against.
		for fieldname in (
			"one_fm_passport_number",
			"one_fm_passport_holder_of",
			"one_fm_passport_issued",
			"one_fm_passport_expire",
			"one_fm_date_of_birth",
		):
			self.assertEqual(self.fields[fieldname].get("read_only"), 1, msg=fieldname)

	def test_the_types_match_the_source(self):
		meta = frappe.get_meta("Job Applicant")
		for fieldname in (
			"one_fm_passport_number",
			"one_fm_passport_holder_of",
			"one_fm_passport_issued",
			"one_fm_passport_expire",
			"one_fm_date_of_birth",
		):
			self.assertEqual(
				self.fields[fieldname]["fieldtype"],
				meta.get_field(fieldname).fieldtype,
				msg=fieldname,
			)


class TestTheBackfill(FrappeTestCase):
	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.backfill_job_offer_passport_details", patches)

	def test_it_copies_the_dates_onto_a_submitted_offer(self):
		applicant, offer = self._seed()

		self.assertEqual(self._backfill(offer, applicant), 1)

		values = frappe.db.get_value(
			"Job Offer", offer, ["one_fm_passport_number", "one_fm_passport_expire",
								 "one_fm_date_of_birth"], as_dict=True
		)
		self.assertEqual(values.one_fm_passport_number, "P-002599")
		self.assertEqual(getdate(values.one_fm_passport_expire), getdate(add_months(today(), 40)))
		self.assertEqual(getdate(values.one_fm_date_of_birth), getdate("1990-01-01"))

	def test_an_offer_whose_applicant_has_nothing_is_left_alone(self):
		applicant, offer = self._seed(passport_expire=None, date_of_birth=None, passport_number="")

		self.assertEqual(self._backfill(offer, applicant), 0)
		self.assertIsNone(frappe.db.get_value("Job Offer", offer, "one_fm_passport_expire"))

	def test_it_writes_nothing_for_an_offer_with_no_applicant(self):
		from one_fm.patches.v15_0.backfill_job_offer_passport_details import backfill

		self.assertEqual(backfill([frappe._dict(name="X", job_applicant=None)]), 0)

	def test_it_reads_each_applicant_once_however_many_offers_they_have(self):
		# Two offers for one applicant must not be two lookups; there are thousands of rows.
		from one_fm.patches.v15_0.backfill_job_offer_passport_details import applicant_details

		applicant, offer = self._seed()
		details = applicant_details({applicant, applicant})

		self.assertEqual(list(details), [applicant])

	def _backfill(self, offer, applicant):
		from one_fm.patches.v15_0.backfill_job_offer_passport_details import backfill

		# Scoped to the seeded row on purpose. execute() sweeps every submitted offer in the
		# system and commits per batch, which is right for a migration and wrong for a test.
		return backfill([frappe._dict(name=offer, job_applicant=applicant)])

	def _seed(self, passport_expire=-1, date_of_birth="1990-01-01", passport_number="P-002599"):
		"""A submitted Job Offer with the fields blank, which is the state every existing
		one is in. Written with db_insert so neither controller runs - this patch is about
		rows, not about either document's business logic."""
		applicant = frappe.new_doc("Job Applicant")
		applicant.name = "WI-002599-APPLICANT"
		applicant.applicant_name = "WI-002599 Applicant"
		applicant.one_fm_passport_number = passport_number
		applicant.one_fm_passport_expire = (
			add_months(today(), 40) if passport_expire == -1 else passport_expire
		)
		applicant.one_fm_date_of_birth = date_of_birth
		applicant.status = "Open"
		applicant.db_insert()

		offer = frappe.new_doc("Job Offer")
		offer.name = "WI-002599-OFFER"
		offer.job_applicant = applicant.name
		offer.status = "Accepted"
		offer.docstatus = 1
		offer.offer_date = today()
		offer.db_insert()

		self.addCleanup(frappe.db.delete, "Job Offer", {"name": offer.name})
		self.addCleanup(frappe.db.delete, "Job Applicant", {"name": applicant.name})
		return applicant.name, offer.name
