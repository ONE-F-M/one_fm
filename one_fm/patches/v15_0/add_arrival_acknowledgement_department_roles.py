import frappe


def execute():
	"""Create the "Transportation Manager" role (didn't exist anywhere in the system)
	and grant it, along with "Accommodation User" and "Finance User", to the specific
	people currently assigned to those departments on Arrival and Deployment records.

	Arrival Acknowledgement's permission model (see
	one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement.has_permission)
	grants access by department role rather than by the assigned_to field, so without
	this patch these three people would be locked out of their own currently-assigned
	acknowledgement records the moment it ships. Warehouse Supervisor (Rizwan Abbas) and
	Operation Admin (Supriya Aman Husain) already hold their respective role and are left
	untouched.
	"""
	if not frappe.db.exists("Role", "Transportation Manager"):
		frappe.get_doc({"doctype": "Role", "role_name": "Transportation Manager"}).insert()

	grants = {
		"i.anware@one-fm.com": "Transportation Manager",
		"2402059np185@one-fm.com": "Accommodation User",
		"n.alqedheebi@one-fm.com": "Finance User",
	}

	for user, role in grants.items():
		if not frappe.db.exists("User", user):
			continue
		if frappe.db.exists("Has Role", {"parent": user, "role": role}):
			continue
		frappe.get_doc({
			"doctype": "Has Role",
			"parent": user,
			"parenttype": "User",
			"parentfield": "roles",
			"role": role,
		}).insert()

	frappe.clear_cache(doctype="Arrival Acknowledgement")
