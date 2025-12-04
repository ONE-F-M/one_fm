import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist(methods=["GET"])
def get_monthly_sales_summary(customer_id: str, year: int):
	frappe.only_for("Sales User")

	if not frappe.db.exists("Customer", customer_id):
		frappe.throw(_("Customer not found"))

	sales = frappe.db.sql(
		"""
		SELECT
			MONTH(posting_date) as month,
			SUM(grand_total) as total
		FROM `tabSales Invoice`
		WHERE
			customer = %s AND
			YEAR(posting_date) = %s AND
			docstatus = 1
		GROUP BY MONTH(posting_date)
		""",
		(customer_id, year),
		as_dict=True,
	)

	sales_dict = {s.month: s.total for s in sales}

	summary = [{"month": month, "total": flt(sales_dict.get(month, 0.0))} for month in range(1, 13)]
