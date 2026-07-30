# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for inviting a Contact to the portal (WI-001785)."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.contact import (
	CUSTOMER_PORTAL_ROLE,
	get_linked_customer,
	invite_user,
)

CUSTOMER_EMAIL = "_test_portal_client@example.com"


def _get_or_create_customer():
	name = "_Test Invite Customer"
	if frappe.db.exists("Customer", name):
		return name
	return frappe.get_doc({"doctype": "Customer", "customer_name": name}).insert(
		ignore_permissions=True
	).name


def _make_contact(email=None, customer=None):
	# Contact autonames from the person's name, so runs collide. Child rows outlive a
	# parent delete, and a leftover primary email makes the next insert fail with
	# "Only one Email ID can be set as primary".
	for name in frappe.get_all("Contact", filters={"first_name": "_TestInvite"}, pluck="name"):
		frappe.db.delete("Contact Email", {"parent": name})
		frappe.db.delete("Contact Phone", {"parent": name})
		frappe.db.delete("Dynamic Link", {"parent": name})
		frappe.db.delete("Contact", {"name": name})

	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": "_TestInvite",
			"last_name": "Client",
		}
	)
	if email:
		contact.append("email_ids", {"email_id": email, "is_primary": 1})
	if customer:
		contact.append("links", {"link_doctype": "Customer", "link_name": customer})
	contact.insert(ignore_permissions=True)
	return contact


class TestLinkedCustomer(FrappeTestCase):
	def test_a_customer_link_is_found(self):
		customer = _get_or_create_customer()
		contact = _make_contact(email=CUSTOMER_EMAIL, customer=customer)
		self.assertEqual(get_linked_customer(contact), customer)

	def test_a_contact_with_no_links_has_no_customer(self):
		contact = _make_contact(email=CUSTOMER_EMAIL)
		self.assertIsNone(get_linked_customer(contact))

	def test_a_non_customer_link_is_ignored(self):
		# The same button serves supplier and employee contacts, which must not be
		# mistaken for clients.
		contact = _make_contact(email=CUSTOMER_EMAIL)
		contact.append("links", {"link_doctype": "Supplier", "link_name": "_Test Supplier"})
		self.assertIsNone(get_linked_customer(contact))


class TestInviteUserGuards(FrappeTestCase):
	"""The two blocking scenarios, neither of which may create a User."""

	def test_a_contact_without_an_email_is_refused(self):
		contact = _make_contact()
		with self.assertRaises(frappe.ValidationError) as cm:
			invite_user(contact.name)
		self.assertIn(
			"Cannot invite user: Primary email address is missing on this contact.",
			str(cm.exception),
		)

	def test_an_existing_user_is_refused_and_names_the_address(self):
		existing = frappe.db.get_value("User", {"enabled": 1}, "name")
		contact = _make_contact(email=existing)
		before = frappe.db.count("User")

		with self.assertRaises(frappe.ValidationError) as cm:
			invite_user(contact.name)

		self.assertIn(f"User with email {existing} already exists in the system.", str(cm.exception))
		self.assertEqual(frappe.db.count("User"), before)


class TestInviteUserCreatesPortalAccount(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("User", {"email": CUSTOMER_EMAIL})
		self.customer = _get_or_create_customer()
		# Frappe sends the welcome mail from User.after_insert. Muting is not enough:
		# the queue entry is *built* before the mute check, and building it resolves a
		# sender from the site's default Email Account, which is unconfigured here.
		# Sending is Frappe's concern; the invitation is what is under test.
		patcher = patch("frappe.sendmail")
		self.sendmail = patcher.start()
		self.addCleanup(patcher.stop)

	def test_a_website_user_is_created_with_the_portal_role(self):
		contact = _make_contact(email=CUSTOMER_EMAIL, customer=self.customer)

		user_name = invite_user(contact.name)

		self.assertEqual(user_name, CUSTOMER_EMAIL)
		user = frappe.get_doc("User", user_name)
		self.assertEqual(user.user_type, "Website User")
		self.assertIn(CUSTOMER_PORTAL_ROLE, [r.role for r in user.roles])

	def test_the_welcome_email_is_requested_and_sent(self):
		contact = _make_contact(email=CUSTOMER_EMAIL, customer=self.customer)
		invite_user(contact.name)
		# send_welcome_email is what carries the secure password-setup link, so both
		# the flag and the resulting send matter.
		self.assertTrue(frappe.db.get_value("User", CUSTOMER_EMAIL, "send_welcome_email"))
		self.assertTrue(self.sendmail.called)

	def test_a_contact_with_no_customer_gets_no_portal_role(self):
		contact = _make_contact(email=CUSTOMER_EMAIL)

		user_name = invite_user(contact.name)

		user = frappe.get_doc("User", user_name)
		self.assertNotIn(CUSTOMER_PORTAL_ROLE, [r.role for r in user.roles])


class TestOverrideIsWired(FrappeTestCase):
	def test_the_framework_method_is_overridden(self):
		self.assertEqual(
			frappe.get_hooks("override_whitelisted_methods").get(
				"frappe.contacts.doctype.contact.contact.invite_user"
			),
			["one_fm.overrides.contact.invite_user"],
		)

	def test_the_portal_role_exists_and_is_website_only(self):
		self.assertTrue(frappe.db.exists("Role", CUSTOMER_PORTAL_ROLE))
		self.assertEqual(
			frappe.db.get_value("Role", CUSTOMER_PORTAL_ROLE, "desk_access"), 0
		)
