import frappe

PAGE = "transportation-schedule"
ROLE = "Transportation Manager"
# What Transportation Supervisor already holds on Route Plan, mirrored rather than
# invented so the two transport roles work the same board the same way.
ROUTE_PLAN_PERMS = {
	"select": 1, "read": 1, "write": 1, "create": 1, "delete": 1,
	"report": 1, "export": 1, "share": 1, "print": 1, "email": 1,
}


def execute():
	"""Let Transportation Manager open and run the Transportation Schedule (WI-002162).

	The AC is that Transportation Manager and Transportation Supervisor may click
	"Generate Shipments" and update the shipment cards. Relaxing the whitelisted
	method's role gate is only half of it: the page itself is role-restricted and the
	plan behind it is a Route Plan, so without these two grants a Transportation
	Manager never reaches the button to be refused by it.

	Transportation Supervisor already holds both and is left alone. Nothing is granted
	on Transportation Shipment: the generator writes those with ignore_permissions and
	the canvas reads them server-side, which is how the Supervisor already works.
	"""
	if not frappe.db.exists("Role", ROLE):
		return

	_grant_page_role()
	_grant_route_plan_perms()
	frappe.clear_cache()


def _grant_page_role():
	"""Add the role to the page's Custom Role, creating the record if there is none."""
	name = frappe.db.get_value("Custom Role", {"page": PAGE}, "name")
	if not name:
		# No Custom Role means the Page's own roles still apply; carry them over so
		# creating one here does not quietly lock the current holders out.
		page = frappe.get_doc("Page", PAGE)
		doc = frappe.new_doc(doctype="Custom Role")
		doc.page = PAGE
		for row in page.roles:
			doc.append("roles", {"role": row.role})
		doc.append("roles", {"role": ROLE})
		doc.insert(ignore_permissions=True)
		return

	doc = frappe.get_doc("Custom Role", name)
	if any(row.role == ROLE for row in doc.roles):
		return
	doc.append("roles", {"role": ROLE})
	doc.save(ignore_permissions=True)


def _grant_route_plan_perms():
	"""Give the role real access to Route Plan.

	Route Plan already carries Custom DocPerm rows, and once any exist Frappe stops
	honouring the DocType JSON's permissions for every other role — so the grant has
	to be a Custom DocPerm too, not an entry in the JSON.
	"""
	if frappe.db.exists("Custom DocPerm", {"parent": "Route Plan", "role": ROLE}):
		return

	frappe.get_doc({
		"doctype": "Custom DocPerm",
		"parent": "Route Plan",
		"parenttype": "DocType",
		"parentfield": "permissions",
		"role": ROLE,
		"permlevel": 0,
		**ROUTE_PLAN_PERMS,
	}).insert(ignore_permissions=True)
