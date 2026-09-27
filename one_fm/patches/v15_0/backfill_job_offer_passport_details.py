"""WI-002599: fill in the passport and date-of-birth copies on existing Job Offers.

``fetch_from`` runs on validate, and a submitted Job Offer never validates again - so the
new fields would stay blank on every offer already in the system. That is over two and a
half thousand submitted offers, which is most of them, and a blank Passport Expires On is
exactly the thing a recruiter would read as "this applicant has no passport".

The same problem, and the same answer, as patches/v14_0/set_job_offer_field_valuse_from_
applicant, which backfilled agency, nationality and department after those fields were
added. Written with the Query Builder rather than that patch's string-formatted SQL.

Draft offers are left to fetch for themselves on their next save; only submitted ones need
writing directly.
"""

import frappe
from frappe.query_builder import DocType
from frappe.utils import create_batch

# Job Offer fieldname -> Job Applicant fieldname. The names match on purpose.
FIELDS = {
	"one_fm_passport_number": "one_fm_passport_number",
	"one_fm_passport_holder_of": "one_fm_passport_holder_of",
	"one_fm_passport_issued": "one_fm_passport_issued",
	"one_fm_passport_expire": "one_fm_passport_expire",
	"one_fm_date_of_birth": "one_fm_date_of_birth",
}

BATCH_SIZE = 500


def execute():
	if not all(frappe.db.has_column("Job Offer", field) for field in FIELDS):
		# The columns arrive with the custom fields. Nothing to do until they are there.
		return

	offers = frappe.get_all(
		"Job Offer",
		filters={"docstatus": 1, "job_applicant": ["is", "set"]},
		fields=["name", "job_applicant"],
	)

	# One transaction per batch rather than one for several thousand rows: a single long
	# write is the kind that gets killed halfway and leaves nothing behind.
	for batch in create_batch(offers, BATCH_SIZE):
		backfill(batch)
		frappe.db.commit()


def backfill(offers):
	"""Write the applicant's values onto these offers. Returns how many were touched.

	Kept apart from execute() so it can be pointed at a known set of rows - the caller
	decides what to write and when to commit.
	"""
	names = {offer.job_applicant for offer in offers if offer.job_applicant}
	if not names:
		return 0

	applicants = applicant_details(names)
	Offer = DocType("Job Offer")
	written = 0

	for offer in offers:
		source = applicants.get(offer.job_applicant)
		if not source:
			continue

		# Only what the applicant actually has. Writing a blank over a blank is noise, and
		# writing one over a value a human put there would be worse.
		values = {
			offer_field: source.get(applicant_field)
			for offer_field, applicant_field in FIELDS.items()
			if source.get(applicant_field)
		}
		if not values:
			continue

		query = frappe.qb.update(Offer).where(Offer.name == offer.name)
		for field, value in values.items():
			query = query.set(Offer[field], value)
		query.run()
		written += 1

	return written


def applicant_details(names):
	"""The source values, fetched once per applicant rather than once per offer."""
	rows = frappe.get_all(
		"Job Applicant",
		filters={"name": ["in", list(names)]},
		fields=["name"] + sorted(set(FIELDS.values())),
	)
	return {row.name: row for row in rows}
