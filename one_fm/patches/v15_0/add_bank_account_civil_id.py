import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull

from one_fm.custom.custom_field.bank_account import get_bank_account_custom_fields


def execute():
	"""Add Bank Account.civil_id and backfill it from the Employee."""
	create_custom_fields(get_bank_account_custom_fields(), update=True)

	bank_account = DocType("Bank Account")
	employee = DocType("Employee")
	(
		frappe.qb.update(bank_account)
		.join(employee)
		.on(bank_account.party == employee.name)
		.set(bank_account.civil_id, employee.one_fm_civil_id)
		.where(bank_account.party_type == "Employee")
		.where(IfNull(bank_account.civil_id, "") == "")
		.where(IfNull(employee.one_fm_civil_id, "") != "")
		.run()
	)
