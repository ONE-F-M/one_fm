import frappe

OLD = "m.ali@one-fm.com"
PARK = "m.ali-0@one-fm.com"
LEFT_EMPLOYEE = "HR-EMP-00974"
STALE_CONTACT = "Mohammad Ali-4"


def execute():
	"""Free m.ali@one-fm.com so it can be issued to HR-EMP-04585 (Muhammad Usman Ali).

	The address is held by the 2021 account of Mohamed Mohmoud Ali (HR-EMP-00974, Left,
	disabled, last login 2021-04-14). It owns exactly three Link references in the whole
	schema - Employee.user_id, Contact.user, DocShare.user - and no owner/modified_by
	rows at all, so rename_doc moves everything that matters and carries the password.

	What rename_doc cannot move are Data fields: email_id on the Contact and on its
	Contact Email child row, and prefered_email on the Employee. Left behind, core
	create_contact() matches a new user to a Contact by email, finds the departed
	employee's Contact and overwrites its name fields while leaving contact.user on the
	parked account. So they are released here, before any new user exists.

	Issuing the freed address is deliberately left to HR in the desk, so the welcome
	mail and password flow stay interactive.

	Production-specific record names; a no-op on every other site.
	"""
	rename_user()
	release_contact_email()
	release_employee_prefered_email()


def rename_user():
	# Both present means someone already started this by hand - leave it for a human.
	if not frappe.db.exists("User", OLD) or frappe.db.exists("User", PARK):
		return

	# after_rename rewrites owner/modified_by across every table in the schema. This
	# user has none, but the scan is unavoidable and the columns are unindexed, so the
	# statement count is why this belongs in a maintenance window.
	frappe.rename_doc("User", OLD, PARK, force=True, show_alert=False)
	frappe.db.commit()


def release_contact_email():
	if not frappe.db.exists("Contact", STALE_CONTACT):
		return

	if frappe.db.get_value("Contact", STALE_CONTACT, "email_id") == OLD:
		frappe.db.set_value("Contact", STALE_CONTACT, "email_id", PARK)

	# get_contact_name() matches on the child row, so this is the one that actually
	# decides whether the next user to use the address inherits this Contact.
	ContactEmail = frappe.qb.DocType("Contact Email")
	(
		frappe.qb.update(ContactEmail)
		.set(ContactEmail.email_id, PARK)
		.where(ContactEmail.parent == STALE_CONTACT)
		.where(ContactEmail.parenttype == "Contact")
		.where(ContactEmail.email_id == OLD)
	).run()

	frappe.db.commit()


def release_employee_prefered_email():
	if not frappe.db.exists("Employee", LEFT_EMPLOYEE):
		return

	if frappe.db.get_value("Employee", LEFT_EMPLOYEE, "prefered_email") != OLD:
		return

	# prefered_contact_email on this Employee is "User ID", so this only realigns the
	# mirror with the user_id rename_doc has already moved.
	frappe.db.set_value("Employee", LEFT_EMPLOYEE, "prefered_email", PARK)
	frappe.db.commit()
