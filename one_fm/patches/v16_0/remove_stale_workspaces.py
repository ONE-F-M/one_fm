import frappe


def execute():
	"""WI-001332: remove Workspace records superseded by the v16 module pages.

	- GSD: empty module, its workspace was dropped from the app.
	- Fleet: renamed to "Fleet Management" to pair with its Workspace Sidebar.
	- Recruitment: renamed to "Hiring" to pair with its Workspace Sidebar.
	"""
	for name in ("GSD", "Fleet", "Recruitment"):
		frappe.delete_doc("Workspace", name, ignore_missing=True, force=True)
