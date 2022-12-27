import frappe
from frappe import _
from erpnext.accounts.doctype.budget.budget import (
	get_item_details, get_accumulated_monthly_budget, compare_expense_with_budget, get_ordered_amount,
	get_actual_expense
)
from frappe.utils import flt, get_last_day

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions
)
from erpnext.accounts.utils import get_fiscal_year

def validate_budget(doc, method):
	if doc.docstatus == 1:
		for data in doc.get("items"):
			args = data.as_dict()
			args.update(
				{
					"doctype": doc.doctype,
					"company": doc.company,
					"posting_date": doc.posting_date
				}
			)

			validate_expense_against_budget(args)

def validate_expense_against_budget(args):
	args = frappe._dict(args)

	if args.get("company") and not args.fiscal_year:
		args.fiscal_year = get_fiscal_year(args.get("posting_date"), company=args.get("company"))[0]
		frappe.flags.exception_approver_role = frappe.get_cached_value(
			"Company", args.get("company"), "exception_budget_approver_role"
		)

	if not args.account:
		args.account = args.get("expense_account")

	if not (args.get("account") and args.get("cost_center")) and args.item_code:
		args.cost_center, args.account = get_item_details(args)

	if not args.account:
		return

	for budget_against in ["project", "cost_center"] + get_accounting_dimensions():
		if (
			args.get(budget_against)
			and args.account
			and frappe.db.get_value("Account", {"name": args.account, "root_type": "Expense"})
		):

			doctype = frappe.unscrub(budget_against)

			if frappe.get_cached_value("DocType", doctype, "is_tree"):
				lft, rgt = frappe.db.get_value(doctype, args.get(budget_against), ["lft", "rgt"])
				condition = """and exists(select name from `tab%s`
					where lft<=%s and rgt>=%s and name=b.%s)""" % (
					doctype,
					lft,
					rgt,
					budget_against,
				)  # nosec
				args.is_tree = True
			else:
				condition = "and b.%s=%s" % (budget_against, frappe.db.escape(args.get(budget_against)))
				args.is_tree = False

			args.budget_against_field = budget_against
			args.budget_against_doctype = doctype

			budget_records = frappe.db.sql(
				"""
				select
					b.{budget_against_field} as budget_against, ba.budget_amount, b.monthly_distribution,
					ifnull(b.applicable_on_stock_entry, 0) as for_stock_entry,
					b.action_if_annual_budget_exceeded_on_se, b.action_if_accumulated_monthly_budget_exceeded_on_se
				from
					`tabBudget` b, `tabBudget Account` ba
				where
					b.name=ba.parent and b.fiscal_year=%s
					and ba.account=%s and b.docstatus=1
					{condition}
			""".format(
					condition=condition, budget_against_field=budget_against
				),
				(args.fiscal_year, args.account),
				as_dict=True,
			)  # nosec

			if budget_records:
				validate_budget_records(args, budget_records)

def validate_budget_records(args, budget_records):
	for budget in budget_records:
		if flt(budget.budget_amount):
			amount = get_amount(args, budget)
			yearly_action = budget.action_if_annual_budget_exceeded_on_se
			monthly_action = budget.action_if_accumulated_monthly_budget_exceeded_on_se

			if monthly_action in ["Stop", "Warn"]:
				budget_amount = get_accumulated_monthly_budget(
					budget.monthly_distribution, args.posting_date, args.fiscal_year, budget.budget_amount
				)

				args["month_end_date"] = get_last_day(args.posting_date)

				compare_expense_with_budget(
					args, budget_amount, _("Accumulated Monthly"), monthly_action, budget.budget_against, amount
				)

			if (
				yearly_action in ("Stop", "Warn")
				and monthly_action != "Stop"
				and yearly_action != monthly_action
			):
				compare_expense_with_budget(
					args, flt(budget.budget_amount), _("Annual"), yearly_action, budget.budget_against, amount
				)

def get_amount(args, budget):
	amount = 0

	if budget.for_stock_entry:
		amount = (
			get_requested_amount(args, budget) + get_ordered_amount(args, budget) + get_actual_expense(args)
		)

	return amount

def get_requested_amount(args, budget):
	item_code = args.get("item_code")
	condition = get_other_condition(args, budget, "Stock Entry")

	data = frappe.db.sql(
		""" select ifnull((sum(child.amount)), 0) as amount
		from `tabStock Entry Detail` child, `tabStock Entry` parent where parent.name = child.parent and
		child.item_code = %s and parent.docstatus = 1 and {0} and
		parent.stock_entry_type = 'Material Issue'""".format(
			condition
		),
		item_code,
		as_list=1,
	)

	return data[0][0] if data else 0

def get_other_condition(args, budget, for_doc):
	condition = "expense_account = '%s'" % (args.expense_account)
	budget_against_field = args.get("budget_against_field")

	if budget_against_field and args.get(budget_against_field):
		condition += " and child.%s = '%s'" % (budget_against_field, args.get(budget_against_field))

	if args.get("fiscal_year"):
		start_date, end_date = frappe.db.get_value(
			"Fiscal Year", args.get("fiscal_year"), ["year_start_date", "year_end_date"]
		)

		condition += """ and parent.%s
			between '%s' and '%s' """ % (
			"posting_date",
			start_date,
			end_date,
		)

	return condition
