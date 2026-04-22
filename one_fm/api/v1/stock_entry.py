import frappe
from frappe import _
from one_fm.api.v1.utils import response
from frappe.query_builder import DocType
import json

@frappe.whitelist(methods=["POST"])
def get_stock_entries(stock_entry_type: str = None, from_date: str = None, to_date: str = None):
	"""
	Fetch Stock Entry records with optional filtering.
	"""
	filters = {
		"docstatus": ["!=", 2]  # Exclude cancelled records
	}

	if stock_entry_type and stock_entry_type != "undefined":
		# Handle JSON string or comma-separated string
		if isinstance(stock_entry_type, str):
			if stock_entry_type.startswith("["):
				try:
					stock_entry_type = json.loads(stock_entry_type)
				except Exception:
					pass
			elif "," in stock_entry_type:
				stock_entry_type = stock_entry_type.split(",")

		if isinstance(stock_entry_type, (list, tuple)):
			# Validate all types in list
			valid_types = [t for t in stock_entry_type if t in ["Material Transfer", "Material Issue"]]
			if valid_types:
				filters["stock_entry_type"] = ["in", valid_types]
		else:
			if stock_entry_type not in ["Material Transfer", "Material Issue"]:
				return response(_("Invalid Stock Entry Type: {0}").format(stock_entry_type), 400)
			filters["stock_entry_type"] = stock_entry_type
	else:
		# If no type is provided, still restrict to these two as per requirements
		filters["stock_entry_type"] = ["in", ["Material Transfer", "Material Issue"]]

	if from_date:
		filters["posting_date"] = [">=", from_date]
	
	if to_date:
		if "posting_date" in filters:
			filters["posting_date"] = ["between", [from_date, to_date]]
		else:
			filters["posting_date"] = ["<=", to_date]

	# Use frappe.get_list to automatically apply permission checks
	stock_entries = frappe.get_list(
		"Stock Entry",
		filters=filters,
		fields=["name", "stock_entry_type", "from_warehouse", "to_warehouse", "posting_date", "docstatus"],
		order_by="posting_date desc, name desc",
		limit=300
	)

	return response(_("Successful"), 200, stock_entries)

@frappe.whitelist(methods=["GET"])
def get_stock_entry_detail(name: str):
	"""
	Fetch a detailed Stock Entry record including site supervisor name and items.
	"""
	try:
		doc = frappe.get_doc("Stock Entry", name)
		doc.check_permission("read")
	except frappe.DoesNotExistError:
		return response(_("Stock Entry {0} does not exist").format(name), 404)
	except frappe.PermissionError:
		return response(_("Insufficient Permission for Stock Entry {0}").format(name), 403)
	except Exception as e:
		return response(str(e), 500)
	
	# Fetch site supervisor name if custom_site_supervisor is set
	site_supervisor_name = ""
	if doc.get("custom_site_supervisor_name"):
		site_supervisor_name =doc.get("custom_site_supervisor_name")
	else:
		site_supervisor_name = frappe.db.get_value("User", doc.owner, "full_name")
	# Convert items to list of dicts for the frontend
	items = []
	for d in doc.items:
		items.append({
			"item_code": d.item_code,
			"item_name": d.item_name,
			"stock_uom": d.stock_uom,
			"uom": d.uom,
			"qty": d.qty,
			"s_warehouse": d.s_warehouse,
			"t_warehouse": d.t_warehouse,
			"name": d.name
		})

	return response(_("Successful"), 200, {
		"name": doc.name,
		"stock_entry_type": doc.stock_entry_type,
		"from_warehouse": doc.from_warehouse,
		"to_warehouse": doc.to_warehouse,
		"posting_date": doc.posting_date,
		"docstatus": doc.docstatus,
		"custom_site_supervisor_name": site_supervisor_name,
		"items": items
	})

@frappe.whitelist(methods=["POST"])
def get_warehouse_stock_balances(items: list | str, warehouses: list | str, posting_date: str = None):
	"""
	Fetch stock balances for a list of items and warehouses.
	Returns a map: { warehouse: { item_code: balance } }
	"""
	import json
	
	# Ensure we have lists
	if isinstance(items, str):
		try:
			items = json.loads(items)
		except Exception:
			items = [items]
	elif not isinstance(items, list):
		items = [items] if items else []

	if isinstance(warehouses, str):
		try:
			warehouses = json.loads(warehouses)
		except Exception:
			warehouses = [warehouses]
	elif not isinstance(warehouses, list):
		warehouses = [warehouses] if warehouses else []

	# Support comma separated if still needed (fallback)
	if items and isinstance(items[0], str) and "," in items[0] and len(items) == 1:
		items = [i.strip() for i in items[0].split(",")]
	if warehouses and isinstance(warehouses[0], str) and "," in warehouses[0] and len(warehouses) == 1:
		warehouses = [w.strip() for w in warehouses[0].split(",")]

	if not items or not warehouses:
		return response(_("Missing items or warehouses"), 400, {})

	# Log for debugging (temporary)
	# frappe.log_error(message=f"Items: {items}, Warehouses: {warehouses}", title="Debug Balances")

	Bin = DocType("Bin")
	query = (
		frappe.qb.from_(Bin)
		.select(Bin.warehouse, Bin.item_code, Bin.actual_qty)
		.where(Bin.item_code.isin(items))
		.where(Bin.warehouse.isin(warehouses))
	)
	
	results = query.run(as_dict=True)
	
	balance_map = {}
	for res in results:
		wh = res["warehouse"]
		it = res["item_code"]
		qty = res["actual_qty"]
		
		if wh not in balance_map:
			balance_map[wh] = {}
		
		balance_map[wh][it] = float(qty)
	
	return response(_("Successful"), 200, balance_map)

@frappe.whitelist(methods=["GET", "POST"])
def get_stock_items(warehouse: str = None):
	"""
	Fetch all items that are not disabled, not variants, and maintain stock.
	If warehouse is provided, returns only items with actual_qty > 0 in that warehouse.
	"""
	if warehouse:
		Bin = DocType("Bin")
		Item = DocType("Item")
		query = (
			frappe.qb.from_(Item)
			.join(Bin).on(Item.name == Bin.item_code)
			.select(Item.name, Item.item_code, Item.item_name, Item.stock_uom, Bin.actual_qty.as_("available_qty"))
			.where(Bin.warehouse == warehouse)
			.where(Bin.actual_qty > 0)
			.where(Item.disabled == 0)
			.where(Item.has_variants == 0)
			.where(Item.is_stock_item == 1)
		)
		items = query.run(as_dict=True)
	else:
		items = frappe.get_list("Item",
			filters={
				"disabled": 0,
				"has_variants": 0,
				"is_stock_item": 1
			},
			fields=["name", "item_code", "item_name", "stock_uom"]
		)
	return response(_("Successful"), 200, items)

@frappe.whitelist(methods=["GET"])
def get_warehouses():
	"""
	Fetch all warehouses that are not disabled and associated with the current company.
	"""
	warehouses = frappe.get_list("Warehouse",
		filters={"disabled": 0},
		fields=["name", "warehouse_name", "is_group", "parent_warehouse"]
	)
	return response(_("Successful"), 200, warehouses)

@frappe.whitelist(methods=["GET"])
def get_uoms():
	"""
	Fetch all UOMs.
	"""
	uoms = frappe.get_list("UOM",
		fields=["name", "uom_name"]
	)
	return response(_("Successful"), 200, uoms)

