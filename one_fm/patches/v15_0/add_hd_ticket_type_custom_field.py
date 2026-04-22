import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.hd_ticket_type import get_hd_ticket_type_custom_fields


def execute():
	"""Add 'Initiate Process Change Request' custom field to HD Ticket Type."""
	create_custom_fields(get_hd_ticket_type_custom_fields())
