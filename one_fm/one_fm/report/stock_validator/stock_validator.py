# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,get_datetime
from frappe.utils.nestedset import get_descendants_of

SLE_FIELDS = (
	"name",
	"item_code",
	"warehouse",
	"posting_date",
	"posting_time",
	"posting_datetime",
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
			"fieldtype": "Link",
			"options": "Item",
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
		},
   		{
			"label": "Is Quantity Aligned",
			"fieldname": 'is_qty_aligned',
			"fieldtype": "Data",
			"width": 100,
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
	if filters.to_date:
		sle_filters["posting_date"] = ("<=", filters.to_date)
		cond+=f" and posting_date <= '{filters.to_date}'"
	
	
	result_set = frappe.get_all(
		"Stock Ledger Entry",
		fields=SLE_FIELDS,
		filters=sle_filters,
		order_by="timestamp(posting_date, posting_time), creation",
	)
	return result_set

def get_last_ledger_entry(ledger_data,item,date_value):
	"""
	Return the most recent stock data available for an item

	Args:
		ledger_data (list): Stock Ledger Data
		item (string): Item
	"""
	date_dict = {}
	date_str = frappe.utils.get_date_str(date_value)
	date = get_datetime(date_str+' 23:59:59')
	for each in ledger_data:
		if each.item_code == item:
			row_date = get_datetime(each.posting_datetime)
			if date > row_date:
				diff_in_seconds = abs((date-row_date).total_seconds())
				date_dict[diff_in_seconds] = ledger_data.index(each)
			
    
	lowest_diff = min(date_dict.keys())
	lowest_index = date_dict[lowest_diff]
	return ledger_data[lowest_index]
	

def execute(filters=None):
	columns, data = [], []
	update_filters(filters)
	stock_balance_dict = {}
	ledger_items = []
	columns= generate_columns(filters)
	ledger_data = get_stock_ledger_entries(filters)
	stock_balance_data = get_stock_balance(filters)[1]
	for each in stock_balance_data:
		stock_balance_dict[each.item_code] = each
	if ledger_data:
		unique_items = list(set([i.item_code for i in ledger_data]))
		unique_names = frappe.get_all("Item",{"name":['in',unique_items]},['item_name','name'])
		item_dict = [{}]
		for each in unique_names:
			last_ledger_balance = get_last_ledger_entry(ledger_data,each.name,filters.to_date)
			if stock_balance_dict.get(each.name):
				aligned_qty = "Yes" if float(last_ledger_balance.qty_after_transaction) == float(stock_balance_dict[each.name].bal_qty) else "No"
				aligned_val =  "Yes" if float(last_ledger_balance.valuation_rate) == float(stock_balance_dict[each.name].bal_val) else "No"
				data.append({
        			'item_code':each.name,
           			'item_name':stock_balance_dict[each.name].get("item_name"),
					'ledger_quantity':last_ledger_balance.qty_after_transaction,
					'ledger_valuation':last_ledger_balance.valuation_rate,
					'balance_quantity':stock_balance_dict[each.name].bal_qty,
					'balance_valuation':stock_balance_dict[each.name].bal_val,
					'is_qty_aligned':aligned_qty,
					
           		})
			else:
				data.append({
        			'item_code':each.name,
           			'item_name':each.item_name,
					'ledger_quantity':0,
					'ledger_valuation':0,
					'balance_quantity':0,
					'balance_valuation':0,
					'is_qty_aligned':'Yes',
     				
           			})
	return columns, data
