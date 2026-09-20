import frappe

# WI-002301: a uniform replacement is reported by size, so the line carries one.
#
# Required Date stopped being unconditionally mandatory at the same time, so an employee
# can report damage without knowing when they need the replacement. Every rule the uniform
# flow adds is scoped to type Individual, and the controller restores the old
# unconditional rule for every other type - mandatory_depends_on is a form rule, and the
# server only ever checked `reqd`.
FIELDS = {
	"Request for Material Item": ("size",),
	"Request for Material": ("schedule_date",),
}


def execute():
	frappe.reload_doc("purchase", "doctype", "request_for_material_item")
	frappe.reload_doc("purchase", "doctype", "request_for_material")

	verify()


def verify():
	item_meta = frappe.get_meta("Request for Material Item")

	size = item_meta.get_field("size")
	if not size:
		frappe.throw("WI-002301: Request for Material Item has no Size field.")
	if 'parent.type == "Individual"' not in (size.depends_on or ""):
		frappe.throw(
			"WI-002301: Size is not scoped to an Individual request, so it would appear on "
			"every other request type."
		)

	schedule_date = frappe.get_meta("Request for Material").get_field("schedule_date")
	if schedule_date.reqd:
		frappe.throw(
			"WI-002301: Required Date is still unconditionally mandatory, so a uniform "
			"request cannot be started without one."
		)
	if 'doc.type != "Individual"' not in (schedule_date.mandatory_depends_on or ""):
		frappe.throw(
			"WI-002301: Required Date no longer stays mandatory for the other request "
			"types."
		)

	print("WI-002301: uniform request fields in place")
