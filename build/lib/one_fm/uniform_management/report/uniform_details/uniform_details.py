# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, today
from erpnext.stock.utils import update_included_uom_in_report

def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters['warehouse'] = frappe.db.get_value('Uniform Management Settings', None, "new_uniform_warehouse")
	include_uom = filters.get("include_uom")
	columns = get_columns()
	bin_list = get_bin_list(filters)
	item_map = get_item_map(filters.get("item_code"), include_uom)

	warehouse_company = {}
	data = []
	conversion_factors = []
	for bin in bin_list:
		item = item_map.get(bin.item_code)

		if not item:
			# likely an item that has reached its end of life
			continue

		# item = item_map.setdefault(bin.item_code, get_item(bin.item_code))
		company = warehouse_company.setdefault(bin.warehouse,
			frappe.db.get_value("Warehouse", bin.warehouse, "company"))

		if filters.brand and filters.brand != item.brand:
			continue

		elif filters.item_group and filters.item_group != item.item_group:
			continue

		elif filters.company and filters.company != company:
			continue

		re_order_level = re_order_qty = 0

		for d in item.get("reorder_levels"):
			if d.warehouse == bin.warehouse:
				re_order_level = d.warehouse_reorder_level
				re_order_qty = d.warehouse_reorder_qty

		shortage_qty = 0
		if (re_order_level or re_order_qty) and re_order_level > bin.projected_qty:
			shortage_qty = re_order_level - flt(bin.projected_qty)
		distributed = 0
		query = """
			select
				ui.quantity, ui.returned
			from
				`tabEmployee Uniform Item` ui, `tabEmployee Uniform` u
			where
				ui.parent=u.name and u.docstatus=1 and u.type='Issue' and ui.quantity > ui.returned and item = '{0}'
		"""
		distribution_list = frappe.db.sql(query.format(item.name), as_dict=True)
		for distribution in distribution_list:
			distributed += distribution.quantity - distribution.returned
		data.append([item.name, item.description, item.item_group,
			item.stock_uom, bin.actual_qty+distributed, distributed, bin.actual_qty, bin.used_warehouse_qty])

		if include_uom:
			conversion_factors.append(item.conversion_factor)

	update_included_uom_in_report(columns, data, include_uom, conversion_factors)
	return columns, data

def get_columns():
	return [
		{"label": _("Item Code"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Description"), "fieldname": "description", "width": 400},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100},
		{"label": _("UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 70},
		{"label": _("Received"), "fieldname": "received", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Distributed"), "fieldname": "distributed", "fieldtype": "Float", "width": 90, "convertible": "qty"},
		{"label": _("New Uniform"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Used Uniform"), "fieldname": "planned_qty", "fieldtype": "Float", "width": 110, "convertible": "qty"}
	]

def get_bin_list(filters):
	conditions = []

	if filters.item_code:
		conditions.append("item_code = '%s' "%filters.item_code)

	if filters.warehouse:
		warehouse_details = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"], as_dict=1)

		if warehouse_details:
			conditions.append(" exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and bin.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt))

	bin_list = frappe.db.sql("""select item_code, warehouse, actual_qty, planned_qty, indented_qty,
		ordered_qty, reserved_qty, reserved_qty_for_production, reserved_qty_for_sub_contract, projected_qty
		from tabBin bin {conditions} order by item_code, warehouse
		""".format(conditions=" where " + " and ".join(conditions) if conditions else ""), as_dict=1)
	used_warehouse_bin_list = get_used_uniform_qty()
	for bin in bin_list:
		if used_warehouse_bin_list:
			for used_bin in used_warehouse_bin_list:
				if used_bin.item_code == bin.item_code:
					bin['used_warehouse_qty'] = used_bin.actual_qty
	return bin_list

def get_used_uniform_qty(item_code=None):
	warehouse = frappe.db.get_value('Uniform Management Settings', None, "used_uniform_warehouse")
	if warehouse:
		conditions = []
		warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
		if warehouse_details:
			conditions.append(" exists (select name from `tabWarehouse` wh \
				where wh.lft >= %s and wh.rgt <= %s and bin.warehouse = wh.name)"%(warehouse_details.lft,
				warehouse_details.rgt))

		bin_list = frappe.db.sql("""select item_code, warehouse, actual_qty
			from tabBin bin {conditions} order by item_code, warehouse
			""".format(conditions=" where " + " and ".join(conditions) if conditions else ""), as_dict=1)
		return bin_list
	else:
		return False

def get_item_map(item_code, include_uom):
	"""Optimization: get only the item doc and re_order_levels table"""

	condition = ""
	if item_code:
		condition = 'and item_code = {0}'.format(frappe.db.escape(item_code, percent=False))

	cf_field = cf_join = ""
	if include_uom:
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%(include_uom)s"

	items = frappe.db.sql("""
		select item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom{cf_field}
		from `tabItem` item
		{cf_join}
		where item.is_stock_item = 1
		and item.disabled=0
		{condition}
		and (item.end_of_life > %(today)s or item.end_of_life is null or item.end_of_life='0000-00-00')
		and exists (select name from `tabBin` bin where bin.item_code=item.name)"""\
		.format(cf_field=cf_field, cf_join=cf_join, condition=condition),
		{"today": today(), "include_uom": include_uom}, as_dict=True)

	condition = ""
	if item_code:
		condition = 'where parent={0}'.format(frappe.db.escape(item_code, percent=False))

	reorder_levels = frappe._dict()
	for ir in frappe.db.sql("""select * from `tabItem Reorder` {condition}""".format(condition=condition), as_dict=1):
		if ir.parent not in reorder_levels:
			reorder_levels[ir.parent] = []

		reorder_levels[ir.parent].append(ir)

	item_map = frappe._dict()
	for item in items:
		item["reorder_levels"] = reorder_levels.get(item.name) or []
		item_map[item.name] = item

	return item_map
