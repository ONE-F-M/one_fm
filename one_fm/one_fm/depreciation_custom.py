from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, today, getdate, cint
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_checks_for_pl_and_bs_accounts
from erpnext.assets.doctype.asset.depreciation import get_depreciable_assets

def post_depreciation_entries(date=None):
	# Return if automatic booking of asset depreciation is disabled
	if not cint(frappe.db.get_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically")):
		return

	if not date:
		date = today()
	for asset in get_depreciable_assets(date):
		make_depreciation(asset, date)
		frappe.db.commit()

@frappe.whitelist()
def make_depreciation(asset_name, date=None):
	frappe.has_permission('Journal Entry', throw=True)

	if not date:
		date = today()

	asset = frappe.get_doc("Asset", asset_name)
	project = frappe.db.get_value('Location', asset.location, 'project')
	fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account = \
		get_depreciation_accounts(asset,project)

	depreciation_cost_center, depreciation_series = frappe.get_cached_value('Company',  asset.company,
		["depreciation_cost_center", "series_for_depreciation_entry"])

	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	for d in asset.get("schedules"):
		if not d.journal_entry and getdate(d.schedule_date) <= getdate(date):
			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Depreciation Entry"
			je.naming_series = depreciation_series
			je.posting_date = d.schedule_date
			je.company = asset.company
			je.finance_book = d.finance_book
			je.remark = "Depreciation Entry against {0} worth {1}".format(asset_name, d.depreciation_amount)

			credit_entry = {
				"account": accumulated_depreciation_account,
				"credit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name
			}

			debit_entry = {
				"account": depreciation_expense_account,
				"debit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name,
				"cost_center": depreciation_cost_center,
				"project": project
			}

			for dimension in accounting_dimensions:
				if (asset.get(dimension['fieldname']) or dimension.get('mandatory_for_bs')):
					credit_entry.update({
						dimension['fieldname']: asset.get(dimension['fieldname']) or dimension.get('default_dimension')
					})

				if (asset.get(dimension['fieldname']) or dimension.get('mandatory_for_pl')):
					debit_entry.update({
						dimension['fieldname']: asset.get(dimension['fieldname']) or dimension.get('default_dimension')
					})

			je.append("accounts", credit_entry)

			je.append("accounts", debit_entry)

			je.flags.ignore_permissions = True
			je.save()
			if not je.meta.get_workflow():
				je.submit()

			d.db_set("journal_entry", je.name)

			idx = cint(d.finance_book_id)
			finance_books = asset.get('finance_books')[idx - 1]
			finance_books.value_after_depreciation -= d.depreciation_amount
			finance_books.db_update()

	asset.set_status()

	return asset

def get_depreciation_accounts(asset,project = None):
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = project_depreciation_expense_account = None

	accounts = frappe.db.get_value("Asset Category Account",
		filters={'parent': asset.asset_category, 'company_name': asset.company},
		fieldname = ['fixed_asset_account', 'accumulated_depreciation_account',
			'indirect_depreciation_expense_account','direct_depreciation_expense_account'], as_dict=1)

	if accounts:
		fixed_asset_account = accounts.fixed_asset_account
		accumulated_depreciation_account = accounts.accumulated_depreciation_account
		depreciation_expense_account = accounts.indirect_depreciation_expense_account
		project_depreciation_expense_account = accounts.direct_depreciation_expense_account


	if not accumulated_depreciation_account or not depreciation_expense_account:
		accounts = frappe.get_cached_value('Company',  asset.company,
			["accumulated_depreciation_account", "depreciation_expense_account"])

		if not accumulated_depreciation_account:
			accumulated_depreciation_account = accounts[0]
		if not depreciation_expense_account:
			depreciation_expense_account = accounts[1]
	#execute if asset have location and location is linked with project
	if asset.location and project:
		if not project_depreciation_expense_account:
			frappe.throw(_("Please set Indirect Depreciation Expense Account in Asset Category {0}.")
			.format(asset.asset_category))
		else:
			depreciation_expense_account = project_depreciation_expense_account

	if not fixed_asset_account or not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}")
			.format(asset.asset_category, asset.company))

	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account
