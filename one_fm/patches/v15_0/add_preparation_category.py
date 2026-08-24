import frappe

# WI-002101: Preparation carries a Category now, and its name is built from it. Existing
# records keep the names they were given under format:PRE-{posting_date}-{######}; what they
# need is a Category, because the field is mandatory and every one of them would otherwise
# refuse the next save.
#
# A batch's Category follows from the Actions its rows carry, which is the same rule the
# validation applies from now on.
from one_fm.grd.doctype.preparation.preparation import CATEGORIES

DEFAULT_CATEGORY = "Renewal"


def execute():
	frappe.reload_doc("grd", "doctype", "preparation")

	for name in frappe.get_all("Preparation", filters={"category": ["in", ["", None]]}, pluck="name"):
		frappe.db.set_value("Preparation", name, "category", category_for(name), update_modified=False)


def category_for(preparation):
	"""The Category the Actions on this batch imply.

	Renewal for anything unclear: the monthly schedule builds renewal batches and they are
	the overwhelming majority, and a stated Category that is wrong is easier for an operator
	to see and correct than a blank one that blocks the save.
	"""
	actions = set(
		frappe.get_all(
			"Preparation Record",
			filters={"parent": preparation, "parenttype": "Preparation"},
			pluck="renewal_or_extend",
		)
	) - {None, ""}
	if not actions:
		return DEFAULT_CATEGORY

	for category, rules in CATEGORIES.items():
		if actions <= set(rules["actions"]):
			return category

	return DEFAULT_CATEGORY
