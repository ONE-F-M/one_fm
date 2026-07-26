import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.hd_ticket import get_hd_ticket_custom_fields


def execute():
    """Introduce the "Ticket Category" custom field on HD Ticket, migrate the
    legacy "Is Doctype Related" data onto it, and remove the obsolete field."""

    # 1. Create/update the HD Ticket custom fields (adds custom_ticket_category and
    #    updates custom_reference_doctype/custom_process dependencies).
    create_custom_fields(get_hd_ticket_custom_fields())

    # 2. Migrate existing data: tickets flagged as doctype related map to "Doctype Issue".
    if frappe.db.has_column("HD Ticket", "custom_is_doctype_related"):
        frappe.db.set_value(
            "HD Ticket",
            {"custom_is_doctype_related": "Yes"},
            "custom_ticket_category",
            "Doctype Issue",
            update_modified=False,
        )

    # 3. Remove the obsolete "Is Doctype Related" custom field.
    if frappe.db.exists("Custom Field", "HD Ticket-custom_is_doctype_related"):
        frappe.delete_doc("Custom Field", "HD Ticket-custom_is_doctype_related")
