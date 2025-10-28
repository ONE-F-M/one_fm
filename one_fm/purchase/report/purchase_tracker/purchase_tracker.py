# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

import frappe

def get_data(filters):
    filters = filters or {}
    conditions = ["rfp.docstatus = 1"] # only submitted RFP
    params = {}

    # Date range on creation
    if filters.get("from_date"):
        conditions.append("DATE(rfp.creation) >= %(from_date)s")
        params["from_date"] = filters.get("from_date")
    if filters.get("to_date"):
        conditions.append("DATE(rfp.creation) <= %(to_date)s")
        params["to_date"] = filters.get("to_date")

    if filters.get("rfp_no"):
        conditions.append("rfp.name = %(rfp_no)s")
        params["rfp_no"] = filters.get("rfp_no")
    if filters.get("rfp_type"):
        conditions.append("rfp.type = %(rfp_type)s")
        params["rfp_type"] = filters.get("rfp_type")
    if filters.get("project"):
        conditions.append("rfp.project = %(project)s")
        params["project"] = filters.get("project")
    if filters.get("site"):
        conditions.append("rfm.site = %(site)s")
        params["site"] = filters.get("site")
    if filters.get("employee_id"):
        conditions.append("rfp.employee = %(employee_id)s")
        params["employee_id"] = filters.get("employee_id")
    if filters.get("department"):
        conditions.append("rfp.department = %(department)s")
        params["department"] = filters.get("department")
    if filters.get("erf_no"):
        conditions.append("rfm.erf = %(erf_no)s")
        params["erf_no"] = filters.get("erf_no")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    rows = frappe.db.sql(
        f"""
        SELECT
            rfp.name AS rfp_no,
            DATE(rfp.creation) AS rfp_date,
            rfp.type AS type,
            rfp.currency,
            rfp.employee AS employee_id,
            rfp.employee_name AS employee_name,
            rfp.department AS department,
            rfp.project AS project,
            rfm.site AS operation_site,
            rfm.erf AS erf_no,
            item.item_code AS item_code,
            item.qty AS qty,
            item.uom AS uom,
            item.supplier AS supplier,
            (item.rate * item.qty) AS rfp_amount,
            item.base_amount AS rfp_amount_company_currency
        FROM `tabRequest for Purchase` rfp
        INNER JOIN `tabRequest for Purchase Quotation Item` item ON item.parent = rfp.name
        LEFT JOIN `tabRequest for Material` rfm ON rfm.name = rfp.request_for_material
        WHERE {where_clause}
          AND item.item_code IS NOT NULL
        ORDER BY rfp.creation ASC
        """,
        params,
        as_dict=True,
    )

    # Collect RFP/item pairs for Purchase Orders mapping
    if not rows:
        return []

    # Build mapping: (rfp_no, item_code) -> set of PO names
    rfp_nos = {r["rfp_no"] for r in rows}
    # Fetch all relevant PO names and items in one query
    po_rows = frappe.db.sql(
        """
        SELECT po.name AS po_name, poi.item_code, po.one_fm_request_for_purchase AS rfp_no
        FROM `tabPurchase Order` po
        INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
        WHERE po.docstatus IN (0,1)
          AND po.one_fm_request_for_purchase IN (%s)
        """ % (",".join(["%s"] * len(rfp_nos))),
        tuple(rfp_nos),
        as_dict=True,
    )
    po_map = {}
    for pr in po_rows:
        if not pr.get("item_code"):
            continue
        key = (pr["rfp_no"], pr["item_code"])
        po_map.setdefault(key, set()).add(pr["po_name"])

    for r in rows:
        key = (r["rfp_no"], r["item_code"])
        r["purchase_order"] = ", ".join(sorted(po_map.get(key, []))) if po_map.get(key) else ""

    return rows

def get_columns(filters=None):
    filters = filters or {}
    rfp_type = (filters.get('rfp_type') or '').strip()

    columns = [
        {"label": "RFP No", "fieldname": "rfp_no", "fieldtype": "Link", "options": "Request for Purchase", "width": 120},
        {"label": "RFP Date", "fieldname": "rfp_date", "fieldtype": "Date", "width": 100},
        {"label": "Type", "fieldname": "type", "fieldtype": "Data", "width": 80},
    ]

    # Conditional Columns
    employee_columns = [
        {"label": "Employee ID", "fieldname": "employee_id", "fieldtype": "Link", "options": "Employee", "width": 110},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 140},
        {"label": "Department", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
    ]

    project_columns = [
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 120},
        {"label": "Operation Site", "fieldname": "operation_site", "fieldtype": "Link", "options": "Operations Site", "width": 140},
    ]

    erf_column = [
        {"label": "ERF No", "fieldname": "erf_no", "fieldtype": "Link", "options": "ERF", "width": 110},
    ]

    if not rfp_type:
        # Show all conditional columns
        columns.extend(employee_columns)
        columns.extend(project_columns)
        columns.extend(erf_column)
    elif rfp_type == 'Project':
        columns.extend(project_columns)
    elif rfp_type in ['Individual', 'Department']:
        columns.extend(employee_columns)
    elif rfp_type == 'Onboarding':
        columns.extend(erf_column)
    # If rfp_type is 'Stock', no extra columns are added.

    tail_columns = [
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 90},
        {"label": "UoM", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 70},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": "RFP Amount", "fieldname": "rfp_amount", "fieldtype": "Currency", "options": "currency", "width": 110},
        {"label": "RFP Amount (Company Currency)", "fieldname": "rfp_amount_company_currency", "fieldtype": "Currency", "width": 110},
        {"label": "Purchase Order", "fieldname": "purchase_order", "fieldtype": "Data", "width": 160},
        # NOTE: This hidden 'currency' column is required because the 'options' attribute of the 'RFP Amount' column depends on the presence of the 'currency' field.
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "hidden": 1},
    ]

    columns.extend(tail_columns)
    return columns

def execute(filters=None):
    columns = get_columns(filters or {})
    data = get_data(filters or {})
    return columns, data
