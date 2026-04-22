import frappe
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
def override_stock_balance() -> None:
	"""
	Monkey-patch StockBalanceReport.get_closing_balance to support Group Warehouses.
	The standard implementation uses a direct `isin` filter on the warehouse field,
	which only matches exact warehouse names. By replacing it with `apply_warehouse_filter`,
	we leverage ERPNext's nested-set (lft/rgt) logic to automatically include all child
	warehouses when a Group Warehouse is selected.
	"""
	try:
		from erpnext.stock.report.stock_balance.stock_balance import StockBalanceReport
	except ImportError:
		return
	def custom_get_closing_balance(self) -> list:
		"""
		Override get_closing_balance to resolve child warehouses via nested-set boundaries
		when a Group Warehouse is selected, instead of filtering by exact warehouse name.
		"""
		if self.filters.get("ignore_closing_balance"):
			return []
		from frappe.query_builder import Order
		table = frappe.qb.DocType("Closing Stock Balance")
		query = (
			frappe.qb.from_(table)
			.select(table.name, table.to_date)
			.where(
				(table.docstatus == 1)
				& (table.company == self.filters.company)
				& (table.to_date <= self.from_date)
				& (table.status == "Completed")
			)
			.orderby(table.to_date, order=Order.desc)
			.limit(1)
		)
		for fieldname in ["item_code", "item_group", "warehouse_type"]:
			if value := self.filters.get(fieldname):
				if isinstance(value, (list, tuple)):
					query = query.where(table[fieldname].isin(value))
				else:
					query = query.where(table[fieldname] == value)
		if self.filters.get("warehouse"):
			query = apply_warehouse_filter(query, table, self.filters)
		return query.run(as_dict=True)
	StockBalanceReport.get_closing_balance = custom_get_closing_balance
# Injected JS that overrides the Warehouse filter's get_data in the Stock Balance report
# to allow Group Warehouses (is_group=1) to appear in the MultiSelectList dropdown.
# This is appended to the standard Stock Balance JS via the override_whitelisted_methods hook
# registered in hooks.py, which is the correct Frappe-native way to override a whitelisted API.
_STOCK_BALANCE_JS_PATCH = """
frappe.after_ajax(function() {
	if (!frappe.query_reports["Stock Balance"]) return;
	var warehouseFilter = frappe.query_reports["Stock Balance"].filters.find(
		function(f) { return f.fieldname === "warehouse"; }
	);
	if (!warehouseFilter) return;
	warehouseFilter.get_data = function(txt) {
		var warehouse_type = frappe.query_report.get_filter_value("warehouse_type");
		var company = frappe.query_report.get_filter_value("company");
		var filters = {};
		if (warehouse_type) filters.warehouse_type = warehouse_type;
		if (company) filters.company = company;
		return frappe.db.get_link_options("Warehouse", txt, filters);
	};
});
"""
@frappe.whitelist()
def custom_get_script(report_name: str) -> dict:
	"""
	Override for frappe.desk.query_report.get_script.
	Registered via override_whitelisted_methods in hooks.py.
	Appends custom JS to the Stock Balance report script to allow Group Warehouses
	to appear in the Warehouse filter dropdown.
	"""
	from frappe.desk.query_report import get_script as _original_get_script
	res = _original_get_script(report_name)
	if report_name == "Stock Balance":
		res["script"] = (res.get("script") or "") + _STOCK_BALANCE_JS_PATCH
	return res