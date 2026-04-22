import frappe
from frappe.website.utils import get_home_page


# Routes that Subcontractor users are allowed to see in the portal sidebar
SUBCONTRACTOR_ALLOWED_ROUTES = {
	"/subcontractor-attendance",  # Subcontractor Attendance Records
	"/me",                         # My Account
}


def get_website_user_home_page(user: str) -> str:
	"""Return the home page for website users based on their role."""
	return "me"

def filter_subcontractor_sidebar(context):
	"""update_website_context hook — filter sidebar to Subcontractor-only items.
	Only applies to users who have the Subcontractor role but NOT System Manager.
	"""
	if frappe.session.user == "Guest":
		return
	roles = frappe.get_roles()
	# Never filter for System Managers (admins) or users without the Subcontractor role
	if "Subcontractor" not in roles or "System Manager" in roles:
		return
	if not context.get("sidebar_items"):
		return
	context.sidebar_items = [
		item for item in context.sidebar_items
		if item.get("route") in SUBCONTRACTOR_ALLOWED_ROUTES
	]




@frappe.whitelist()
def get_my_supplier():
	"""Return the Supplier linked to the current portal user via User Permission.
	Safe to call from the Web Form JS — no direct User Permission read required.
	"""
	supplier = frappe.db.get_value(
		"User Permission",
		{"user": frappe.session.user, "allow": "Supplier"},
		"for_value"
	)
	return supplier or ""




@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(
	new_password: str,
	logout_all_sessions: int = 0,
	key: str | None = None,
	old_password: str | None = None,
):
	"""Override frappe.core.doctype.user.user.update_password.
	Intercepts redirect for Website Users to send them to /me instead of /app/wiki.
	"""
	from frappe.core.doctype.user.user import update_password as _update_password

	result = _update_password(
		new_password=new_password,
		logout_all_sessions=logout_all_sessions,
		key=key,
		old_password=old_password,
	)

	# If a redirect to /app/... was returned for a Website User, correct it
	user = frappe.session.user
	user_type = frappe.db.get_value("User", user, "user_type")
	if user_type != "System User" and result and str(result).startswith("/app"):
		return get_home_page() or "/me"

	return result


@frappe.whitelist()
def submit_attendance(docname):
	"""Process the 'Submit' workflow action from the Web Form for Subcontract Staff Attendance."""
	doc = frappe.get_doc("Subcontract Staff Attendance", docname)

	# Security check: verify this belongs to the logged-in user's Supplier
	supplier = frappe.db.get_value(
		"User Permission",
		{"user": frappe.session.user, "allow": "Supplier"},
		"for_value"
	)
	if doc.subcontractor_name != supplier:
		frappe.throw("Not Permitted")

	from frappe.model.workflow import apply_workflow
	apply_workflow(doc, "Submit for Review")
	return "Success"

