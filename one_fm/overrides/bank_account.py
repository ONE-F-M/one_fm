import frappe
from frappe import _

# A Kuwaiti IBAN is exactly 30 characters (e.g. KW48NBOK0000000000204576567).
IBAN_LENGTH = 30


def normalise_iban(iban: str) -> str:
	"""Strip every space out of an IBAN.

	Banks print an IBAN in groups of four, so a pasted or typed value routinely
	arrives with grouping spaces. Pure/stdlib so it is cheap to test.
	"""
	return "".join((iban or "").split())


def validate_civil_id(doc, method=None):
	"""Require a Civil ID on personal Bank Accounts (WI-004063).

	Company accounts and accounts held by a non-Employee party (Supplier, ...) are
	exempt. For an Employee account an empty field is filled from the Employee's
	Civil ID; a value typed by the user is kept. PACI auto-creation sets
	`flags.ignore_civil_id` so the Draft account can still be saved.
	"""
	if doc.is_company_account:
		return
	if doc.party_type and doc.party_type != "Employee":
		return

	doc.civil_id = (doc.civil_id or "").strip()

	if not doc.civil_id and doc.party_type == "Employee" and doc.party:
		doc.civil_id = (frappe.db.get_value("Employee", doc.party, "one_fm_civil_id") or "").strip()

	if not doc.civil_id and not doc.flags.ignore_civil_id:
		frappe.throw(_("Civil ID is mandatory"), title=_("Missing Civil ID"))


def validate_iban(doc, method=None):
	"""Normalise the IBAN and hold a changed one to its fixed length (WI-001797).

	Spaces are always removed: the payroll export reads this field raw, so a
	value carrying the bank's grouping spaces is unusable downstream.

	The length rule is enforced only when the IBAN actually changes. Applied to
	every save it would freeze any legacy account whose stored IBAN is not 30
	characters - blocking edits and workflow transitions that have nothing to do
	with the IBAN - so an untouched legacy value is left alone and becomes
	compliant the next time someone edits it.
	"""
	if not doc.iban:
		return

	cleaned = normalise_iban(doc.iban)
	doc.iban = cleaned

	before = doc.get_doc_before_save()
	# Compare normalised to normalised, so merely stripping the spaces out of a
	# legacy value does not read as a change and trip the length check.
	if before and normalise_iban(before.iban) == cleaned:
		return

	if len(cleaned) != IBAN_LENGTH:
		frappe.throw(_("IBAN must be exactly {0} characters long.").format(IBAN_LENGTH))
