import frappe
from frappe import _
from frappe.utils import flt, today, getdate, cint
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_checks_for_pl_and_bs_accounts
from erpnext.assets.doctype.asset.depreciation import (
	get_depreciable_assets_data,
	get_credit_debit_accounts_for_asset,
	get_depreciation_cost_center_and_series,
	make_depreciation_entry as erpnext_make_depreciation_entry,
)


def post_depreciation_entries(date=None):
	"""Custom depreciation posting that respects project-linked accounts.

	Frappe v16 migration: adapted from old `get_depreciable_asset_depr_schedules_data`
	to new `get_depreciable_assets_data` which returns (depr_schedule_name, asset_name,
	start_idx, end_idx). Delegates actual JE creation to ERPNext v16's
	make_depreciation_entry but passes custom project-based accounts.
	"""
	if not cint(frappe.db.get_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically")):
		return

	if not date:
		date = today()

	for depr_schedule_name, asset_name, start_idx, end_idx in get_depreciable_assets_data(date):
		asset = frappe.get_doc("Asset", asset_name)
		# Override accounts if asset has a location linked to a project
		if asset.location:
			project = frappe.db.get_value("Location", asset.location, "project")
			if project:
				_set_project_based_accounts(asset, project)
		try:
			erpnext_make_depreciation_entry(depr_schedule_name, date, start_idx, end_idx)
		except Exception:
			frappe.log_error(
				title="Depreciation Entry Failed",
				message=f"Asset: {asset_name}, Schedule: {depr_schedule_name}\n{frappe.get_traceback()}",
			)
		frappe.db.commit()


def _set_project_based_accounts(asset, project):
	"""Temporarily override the Asset Category Account to use project-based
	depreciation expense account.

	The one_fm app stores both direct (project-linked) and indirect (general)
	depreciation expense accounts. When an asset's Location has a project,
	the direct expense account should be used.
	"""
	accounts = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset.asset_category, "company_name": asset.company},
		fieldname=[
			"fixed_asset_account",
			"accumulated_depreciation_account",
			"indirect_depreciation_expense_account",
			"direct_depreciation_expense_account",
		],
		as_dict=1,
	)

	if accounts and accounts.direct_depreciation_expense_account:
		# Temporarily set the depreciation_expense_account to the direct one
		# so ERPNext v16's get_credit_debit_accounts_for_asset picks it up.
		# This is done at the DB level to avoid mutating the cached doc.
		frappe.db.set_value(
			"Asset Category Account",
			{"parent": asset.asset_category, "company_name": asset.company},
			"depreciation_expense_account",
			accounts.direct_depreciation_expense_account,
		)


@frappe.whitelist()
def make_depreciation(asset_name, date=None):
	"""Legacy single-asset depreciation trigger — delegates to v16 API."""
	if not date:
		date = today()

	depr_schedules = frappe.get_all(
		"Asset Depreciation Schedule",
		filters={"asset": asset_name, "docstatus": 1},
		pluck="name",
	)
	for schedule_name in depr_schedules:
		try:
			erpnext_make_depreciation_entry(schedule_name, date)
		except Exception:
			frappe.log_error(
				title="Depreciation Entry Failed",
				message=f"Asset: {asset_name}, Schedule: {schedule_name}\n{frappe.get_traceback()}",
			)
		frappe.db.commit()

	return frappe.get_doc("Asset", asset_name)


def get_depreciation_accounts(asset, project=None):
	"""Legacy helper — kept for backward compat, but v16 now uses
	get_credit_debit_accounts_for_asset internally."""
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None

	accounts = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset.asset_category, "company_name": asset.company},
		fieldname=[
			"fixed_asset_account",
			"accumulated_depreciation_account",
			"indirect_depreciation_expense_account",
			"direct_depreciation_expense_account",
		],
		as_dict=1,
	)

	if accounts:
		fixed_asset_account = accounts.fixed_asset_account
		accumulated_depreciation_account = accounts.accumulated_depreciation_account
		depreciation_expense_account = accounts.indirect_depreciation_expense_account

	if not accumulated_depreciation_account or not depreciation_expense_account:
		acc = frappe.get_cached_value(
			"Company", asset.company, ["accumulated_depreciation_account", "depreciation_expense_account"]
		)
		if not accumulated_depreciation_account:
			accumulated_depreciation_account = acc[0]
		if not depreciation_expense_account:
			depreciation_expense_account = acc[1]

	if asset.location and project:
		if accounts and accounts.direct_depreciation_expense_account:
			depreciation_expense_account = accounts.direct_depreciation_expense_account
		else:
			frappe.throw(
				_("Please set Indirect Depreciation Expense Account in Asset Category {0}.").format(
					asset.asset_category
				)
			)

	if not fixed_asset_account or not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(
			_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}").format(
				asset.asset_category, asset.company
			)
		)

	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account
