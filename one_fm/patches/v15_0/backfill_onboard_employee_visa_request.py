import frappe

from one_fm.hiring.utils import get_visa_request_for_job_offer

# WI-002606: the Visa Request link is new, so every onboarding created before it exists
# has an empty field - 138 of them on current data whose Job Offer does carry a Visa
# Request. Without this they would each have to be opened and saved by hand before the PAM
# and visa details the story is about appeared.
SOURCE = "visa_request."


def fetched_fields():
	"""{onboard fieldname: visa request fieldname} read off the doctype's own fetch_from.

	Read rather than listed so this cannot drift from the fields themselves: a fetch added
	or renamed later is picked up here without anyone remembering to edit a second copy.
	"""
	return {
		field.fieldname: field.fetch_from[len(SOURCE):]
		for field in frappe.get_meta("Onboard Employee").fields
		if (field.fetch_from or "").startswith(SOURCE)
	}


def execute():
	mapping = fetched_fields()

	rows = frappe.get_all(
		"Onboard Employee",
		filters={"job_offer": ["is", "set"], "visa_request": ["is", "not set"]},
		fields=["name", "job_offer"],
	)

	filled = 0
	for row in rows:
		visa_request = get_visa_request_for_job_offer(row.job_offer)
		if not visa_request:
			continue

		values = {"visa_request": visa_request}
		if mapping:
			source = frappe.db.get_value(
				"Visa Request", visa_request, list(mapping.values()), as_dict=True
			) or {}
			# The fetched fields are read-only and derived, so they are written here too.
			# db_set does not run the fetch, and leaving them empty would mean the link
			# was backfilled but the details it exists to carry were not.
			for target, origin in mapping.items():
				if source.get(origin):
					values[target] = source.get(origin)

		# update_modified=False: this is a repair, not an edit by whoever runs the migrate,
		# and it must not push 138 onboardings to the top of everyone's "recently modified".
		frappe.db.set_value("Onboard Employee", row.name, values, update_modified=False)
		filled += 1

	frappe.db.commit()
	print(f"WI-002606: linked a Visa Request on {filled} of {len(rows)} onboarding(s)")
