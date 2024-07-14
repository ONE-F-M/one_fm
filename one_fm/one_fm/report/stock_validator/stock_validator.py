# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from frappe.utils.nestedset import get_descendants_of

SLE_FIELDS = (
	"name",
	"item_code",
	"warehouse",
	"posting_date",
	"posting_time",
	"creation",
	"voucher_type",
	"voucher_no",
	"actual_qty",
	"qty_after_transaction",
	"stock_queue",
	"batch_no",
	"stock_value",
	"valuation_rate",
)


def update_filters(filters):
	if  not filters.get('from_date'):
		filters['from_date'] = filters['to_date']

def generate_columns(filters):
	if getdate(filters.get('from_date')) > getdate(filters.get('to_date')):
		frappe.throw("From date cannot be after To Date")
	columns = [{
			"label": "Item Code",
			"fieldname": 'item_code',
			"fieldtype": "Data",
			"width": 200,
		},{
			"label": "Item Name ",
			"fieldname": 'item_name',
			"fieldtype": "Data",
			"width": 200,
		},{
			"label": "Stock Ledger Balance Quantity ",
			"fieldname": 'ledger_quantity',
			"fieldtype": "Float",
			"width": 200,
		},
			   {
			"label": "Stock Ledger Valuation Rate ",
			"fieldname": 'ledger_valuation',
			"fieldtype": "Float",
			"width": 200,
		},
			   {
			"label": "Stock Balance Balance Quantity",
			"fieldname": 'balance_quantity',
			"fieldtype": "Float", 
			"width": 200,
		},
			   {
			"label": "Stock Balance Valuation Rate",
			"fieldname": 'balance_valuation',
			"fieldtype": "Float",
			"width": 200,
		}]
	return columns
 

def get_stock_balance(filters):
	from erpnext.stock.report.stock_balance.stock_balance import execute as execute_stock_balance_report
	return execute_stock_balance_report(filters)
	
def get_stock_ledger(filters):
	from erpnext.stock.report.stock_ledger.stock_ledger import execute as execute_stock_ledger_report
	return execute_stock_ledger_report(filters)



def get_stock_ledger_entries(filters):
	fields_str = ", ".join(SLE_FIELDS)
	query = f""" 
		Select {fields_str} from `tabStock Ledger Entry` where is_cancelled = 0
 	"""
	cond = ""
	sle_filters = {"is_cancelled": 0}

	if filters.warehouse:
		children = get_descendants_of("Warehouse", filters.warehouse)
		sle_filters["warehouse"] = ("in", [*children, filters.warehouse])
		children.append(filters.warehouse)
		cond+= f" and warehouse in {tuple(children)} " if len(children) > 1 else f" and warehouse = '{children[0]}'"

	if filters.item_code:
		sle_filters["item_code"] = filters.item_code
		cond+= f" and item_code = '{filters.item_code}'"
  
	elif filters.get("item_group"):
		item_group = filters.get("item_group")
		children = get_descendants_of("Item Group", item_group)
		item_group_filter = {"item_group": ("in", [*children, item_group])}
		all_items = frappe.get_all("Item", filters=item_group_filter, pluck="name", order_by=None)
		if not all_items:
			frappe.throw(f"No Items found for Item Group {filters.get('item_group')}")
		sle_filters["item_code"] = (
			"in",
			frappe.get_all("Item", filters=item_group_filter, pluck="name", order_by=None),
		)
		if len(all_items) >1:
			cond+=f" and item_code = '{all_items[0]}'"
		else:
			cond+= f" and item_code in {tuple(all_items)}"
		

	# if filters.from_date:
	# 	sle_filters["posting_date"] = (">=", filters.from_date)
	# 	cond+=f" and posting_date >= '{filters.from_date}'"
	if filters.to_date:
		sle_filters["posting_date"] = ("<=", filters.to_date)
		cond+=f" and posting_date <= '{filters.to_date}'"
	final_query  = query+cond + " ORDER BY posting_date DESC LIMIT 1"
	result_set = frappe.db.sql(final_query,as_dict=1)
	result_set2 = frappe.get_all(
		"Stock Ledger Entry",
		fields=SLE_FIELDS,
		filters=sle_filters,
		order_by="timestamp(posting_date, posting_time), creation",
	)
	return {'result_set':result_set,'result_set_2':result_set2}

	

def execute(filters=None):
	columns, data = [], []
	update_filters(filters)
	ledger_items = []
	columns= generate_columns(filters)
	ledger_data = get_stock_ledger_entries(filters)
	stock_balance_data = get_stock_balance(filters)
	# if ledger_data:
	# 	data = list(set([{'item_code':i.item_code} for i in  ledger_data])) #Remove Duplicates
		

	return columns, data
