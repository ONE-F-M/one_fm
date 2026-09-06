import frappe

# WI-002233: PAM licence information is maintained on PAM License Details now, so every Link
# that named a PAM File names the licence instead.
#
# The file record stays: it still holds the file-level things a licence does not carry - the
# governorate, the company unified number, the MOCI trade name - and it is what owns the
# PAM Licenses table that lists a file's licences. What moves is which of the two a record
# points at when it says which PAM registration an employee, applicant or request belongs to.
LINK_FIELDS = (
	("Demand Letter", "pam_file"),
	("ERF", "pam_file"),
	("Employee", "pam_file"),
	("Job Applicant", "one_fm_pam_file_number"),
	("PAM Authorized Signatory List", "pam_file_name"),
	("PAM Salary Certificate", "pam_file_name"),
	("Visa Request", "custom_pam_file"),
	("Work Permit", "new_pam_file"),
)

TARGET = "PAM License Details"

# Each of those links pulled the PAM number alongside itself. The file states it as
# pam_file_number; the licence states the same number as civil_id_number_for_licensing,
# which is what the licence headcounts already match employees by (WI-002091), so the
# fetched value keeps meaning what it did.
FETCH_FIELDS = (
	("ERF", "pam_file_number", "pam_file.civil_id_number_for_licensing"),
	("Employee", "pam_file_number", "pam_file.civil_id_number_for_licensing"),
	("Job Applicant", "one_fm_file_number", "one_fm_pam_file_number.civil_id_number_for_licensing"),
	("PAM Authorized Signatory List", "pam_file_number", "pam_file_name.civil_id_number_for_licensing"),
	("PAM Salary Certificate", "pam_file_number", "pam_file_name.civil_id_number_for_licensing"),
	("Work Permit", "new_pam_file_number", "new_pam_file.civil_id_number_for_licensing"),
)

# The six that carry the change in their own doctype JSON. Employee and Job Applicant carry
# theirs as Custom Fields, which a reload does not touch.
DOCTYPES = (
	("one_fm", "demand_letter"),
	("one_fm", "erf"),
	("grd", "pam_authorized_signatory_list"),
	("grd", "pam_salary_certificate"),
	("grd", "work_permit"),
	("visa_management", "visa_request"),
)


def execute():
	if not frappe.db.exists("DocType", TARGET):
		frappe.throw(
			f"WI-002233: {TARGET} does not exist, so the links would point at nothing. "
			"one_fm.patches.v15_0.migrate_pam_license_configuration has to run first."
		)

	for module, doctype in DOCTYPES:
		frappe.reload_doc(module, "doctype", doctype)

	for doctype, fieldname in LINK_FIELDS:
		_set_custom_field(doctype, fieldname, "options", TARGET)

	for doctype, fieldname, fetch_from in FETCH_FIELDS:
		_set_custom_field(doctype, fieldname, "fetch_from", fetch_from)

	frappe.clear_cache()
	verify()


def _set_custom_field(doctype, fieldname, property, value):
	"""Carry the change onto a Custom Field, which reload_doc does not reach.

	Nothing to do for a field the doctype's own JSON owns - the reload has already written
	it, and there is no Custom Field row to find.
	"""
	name = f"{doctype}-{fieldname}"
	if frappe.db.exists("Custom Field", name):
		frappe.db.set_value("Custom Field", name, property, value)


def verify():
	"""Existing values are not migrated: they are PAM File names, and a file can carry more
	than one licence, so there is no mapping to apply. They stay as they are and no longer
	resolve until somebody picks the licence.

	That costs nothing beyond the dangling name. Frappe skips the fetch entirely when a link
	does not resolve, so the PAM numbers beside these fields keep their values rather than
	being blanked on the next save - which matters, because the licence headcounts and four
	downstream fetches all key on Employee.pam_file_number.
	"""
	wrong = []
	for doctype, fieldname in LINK_FIELDS:
		field = frappe.get_meta(doctype).get_field(fieldname)
		if not field:
			wrong.append(f"{doctype}.{fieldname} does not exist")
		elif field.options != TARGET:
			wrong.append(f"{doctype}.{fieldname} still points at {field.options!r}")

	for doctype, fieldname, fetch_from in FETCH_FIELDS:
		field = frappe.get_meta(doctype).get_field(fieldname)
		if not field:
			wrong.append(f"{doctype}.{fieldname} does not exist")
		elif field.fetch_from != fetch_from:
			wrong.append(f"{doctype}.{fieldname} still fetches {field.fetch_from!r}")

	if wrong:
		frappe.throw("WI-002233: " + "; ".join(wrong))
