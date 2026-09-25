import frappe
from frappe import _

# The site's only website-only role for clients (desk_access = 0). A portal user
# needs it to reach their own organisation's records.
CUSTOMER_PORTAL_ROLE = "Customer"


def get_linked_customer(contact) -> str | None:
	"""The Customer this Contact belongs to, if any."""
	for link in contact.get("links") or []:
		if link.link_doctype == "Customer":
			return link.link_name
	return None


@frappe.whitelist()
def invite_user(contact: str):
	"""Invite a Contact to the portal (WI-001785).

	Overrides ``frappe.contacts.doctype.contact.contact.invite_user`` to add what
	the framework's version leaves out: the client portal role, a duplicate check
	that names the address, and messages an internal user can act on rather than
	"Please set Email Address" or a raw duplicate-entry traceback.

	The portal role is granted only when the Contact is actually linked to a
	Customer. This method also serves supplier and employee contacts, which must
	not pick up a client role as a side effect.
	"""
	contact = frappe.get_doc("Contact", contact)
	contact.check_permission()

	if not contact.email_id:
		frappe.throw(
			_("Cannot invite user: Primary email address is missing on this contact.")
		)

	# Checked up front so the caller gets the address back, rather than the
	# DuplicateEntryError the insert would otherwise raise.
	if frappe.db.exists("User", contact.email_id):
		frappe.throw(
			_("User with email {0} already exists in the system.").format(contact.email_id)
		)

	user = frappe.get_doc(
		{
			"doctype": "User",
			"first_name": contact.first_name,
			"last_name": contact.last_name,
			"email": contact.email_id,
			"user_type": "Website User",
			# Carries the secure password-setup link.
			"send_welcome_email": 1,
		}
	).insert()

	if get_linked_customer(contact) and frappe.db.exists("Role", CUSTOMER_PORTAL_ROLE):
		user.add_roles(CUSTOMER_PORTAL_ROLE)

	frappe.msgprint(_("Invitation email sent successfully"), indicator="green", alert=True)

	# Frappe's Contact form writes this back into the `user` field.
	return user.name
