import frappe

ASSIGNMENT_RULES = (
	"Accommodation Leave Movement-Site Supervisor",
	"Accommodation Leave Movement-Site Supervisor- CheckIn",
)


def execute():
	# The Processa Accommodation Leave Checkout and Check-In Lifecycle maps assign the
	# site supervisor themselves; the rules would assign each movement a second time.
	for rule in ASSIGNMENT_RULES:
		frappe.delete_doc("Assignment Rule", rule, ignore_missing=True, ignore_permissions=True)
