# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""HD-1892786: the Helpdesk reminder recipients become a table of addresses.

``HR Settings.helpdesk_email`` held a single address, so the two Helpdesk reminder jobs
could only ever reach one mailbox - which is why the night-shift operators never saw
them. It is replaced by ``helpdesk_notification_emails``, a table of Helpdesk
Notification Email rows.

The whole HR Settings set is re-run rather than the one new field alone.
create_custom_fields updates a field that already exists instead of duplicating it, so
re-running is idempotent, and it repairs the insert_after chain in the same pass - the
new field takes the retired one's anchor after Sender.

The address that was configured is carried into the first row so whoever is already
receiving the reminders keeps receiving them, and only then is the old field retired -
two sources of truth for "who is told" is the bug returning.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields

SETTINGS = "HR Settings"
RECIPIENTS_FIELD = "helpdesk_notification_emails"
RECIPIENT_DOCTYPE = "Helpdesk Notification Email"
OLD_FIELD = "helpdesk_email"


def execute():
	frappe.reload_doc("one_fm", "doctype", "helpdesk_notification_email")
	create_custom_fields(get_hr_settings_custom_fields())

	if _table_is_empty():
		email = frappe.db.get_single_value(SETTINGS, OLD_FIELD)
		if email:
			_add_recipient(email)

	_retire_old_field()
	frappe.clear_cache(doctype=SETTINGS)


def _table_is_empty():
	return not frappe.db.exists(
		RECIPIENT_DOCTYPE, {"parenttype": SETTINGS, "parentfield": RECIPIENTS_FIELD}
	)


def _add_recipient(email):
	"""Written row-wise rather than through the parent: HR Settings is a Single and
	saving it would drag in every other setting on it."""
	row = frappe.new_doc(RECIPIENT_DOCTYPE)
	row.parent = SETTINGS
	row.parenttype = SETTINGS
	row.parentfield = RECIPIENTS_FIELD
	row.idx = 1
	row.email_id = email
	row.db_insert()


def _retire_old_field():
	frappe.db.delete("Custom Field", {"dt": SETTINGS, "fieldname": OLD_FIELD})
	frappe.db.delete("Singles", {"doctype": SETTINGS, "field": OLD_FIELD})
