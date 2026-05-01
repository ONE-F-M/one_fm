import frappe
from frappe import _
from frappe.utils import get_last_day, flt, getdate

MONTH_MAP = {
	"January": 1, "February": 2, "March": 3, "April": 4,
	"May": 5, "June": 6, "July": 7, "August": 8,
	"September": 9, "October": 10, "November": 11, "December": 12,
}

@frappe.whitelist()
def get_active_contracts_for_customer(customer):
    """Return active contracts for a customer."""
    contracts = frappe.get_all("Contracts", filters={
        "client": customer,
        "workflow_state": "Active"
    }, fields=["name", "project", "currency_"])
    return contracts


@frappe.whitelist()
def get_contract_invoice_items(contract, month, year):
    """
    Core function for 'Get Items From -> Contracts' in Sales Invoice.
    Returns:
       { "items": [...], "project": "...", "site": "...", "currency": "..." }
    """
    contract_doc = frappe.get_doc("Contracts", contract)
    
    month_num = MONTH_MAP.get(month)
    if not month_num:
        frappe.throw(_("Invalid month selected"))
        
    start_date = getdate(f"{year}-{month_num:02d}-01")
    end_date = get_last_day(start_date)

    # 1. Check for Approved Attendance Amendment
    amendments = frappe.get_all("Attendance Amendment", filters={
        "contract": contract, 
        "month": month, 
        "year": year,
        "workflow_state": "Approved"
    }, pluck="name")

    # sale_item -> site -> { actual_days, total_hours }
    item_data = {} 
    
    if amendments:
        amend_doc = frappe.get_doc("Attendance Amendment", amendments[0])
        
        emp_names = list({row.employee for row in (amend_doc.get("attendance_details", []) + amend_doc.get("overtime_details", [])) if row.employee})
        employee_sites = {}
        if emp_names:
            rows = frappe.get_all("Employee", filters={"name": ["in", emp_names]}, fields=["name", "site"])
            employee_sites = {r.name: r.site for r in rows}

        def _accumulate(rows, use_hours=False):
            for row in rows:
                if not row.sale_item: continue
                site = getattr(row, "site", None) or employee_sites.get(row.employee) or amend_doc.site or ""
                item_data.setdefault(row.sale_item, {}).setdefault(site, {"actual_days": 0.0, "total_hours": 0.0})
                item_data[row.sale_item][site]["actual_days"] += flt(row.working_days)
                if use_hours:
                    total_hrs = sum(flt(row.get(f"day_{i}_hour")) for i in range(1, 32))
                    item_data[row.sale_item][site]["total_hours"] += total_hrs

        _accumulate(amend_doc.get("attendance_details", []), use_hours=True)
        _accumulate(amend_doc.get("overtime_details", []), use_hours=True)

    else:
        # Fallback to Frappe HR Attendance
        c_items = [i for i in contract_doc.get("items") if i.item_type == "Service"]
        sale_items = [i.item_code for i in c_items]
        
        if sale_items:
            ops_roles = frappe.get_all("Operations Role", filters={"sale_item": ["in", sale_items]}, fields=["name", "sale_item"])
            role_to_sale_item = {r.name: r.sale_item for r in ops_roles}
            
            if role_to_sale_item:
                # Find employees allocated to these roles
                employees = frappe.get_all("Employee", filters={
                    "custom_operations_role_allocation": ["in", list(role_to_sale_item.keys())]
                }, fields=["name", "custom_operations_role_allocation", "site"])
                
                emp_to_role = {e.name: e.custom_operations_role_allocation for e in employees}
                emp_to_site = {e.name: e.site for e in employees}
                
                if emp_to_role:
                    attendances = frappe.get_all("Attendance", filters={
                        "employee": ["in", list(emp_to_role.keys())],
                        "attendance_date": ["between", [start_date, end_date]],
                        "status": "Present",
                        "docstatus": 1
                    }, fields=["employee", "attendance_date", "working_hours"])
                    
                    for att in attendances:
                        role = emp_to_role.get(att.employee)
                        if role:
                            sale_item = role_to_sale_item[role]
                            site = emp_to_site.get(att.employee) or ""
                            
                            item_data.setdefault(sale_item, {}).setdefault(site, {"actual_days": 0.0, "total_hours": 0.0})
                            item_data[sale_item][site]["actual_days"] += 1.0
                            item_data[sale_item][site]["total_hours"] += flt(att.working_hours)


    # 2. Calculate quantities and build items list
    si_items = []
    for c_item in contract_doc.get("items"):
        if c_item.item_type != "Service":
            continue

        item_code = c_item.item_code
        ops_roles = frappe.get_all("Operations Role", filters={"project": contract_doc.project, "sale_item": item_code, "status": "Active"}, pluck="name")
        if not ops_roles:
            continue

        # Get operation post names only
        operation_post_names = frappe.get_all(
            "Operations Post",
            filters={
                "project": contract_doc.project,
                "post_template": ["in", ops_roles],
                "status": "Active"
            },
            pluck="name"
        )

        if not operation_post_names:
            continue

        site_map = item_data.get(item_code, {})
        mode = contract_doc.create_sales_invoice_as or "Single Invoice"

        def _add_item_for_site(site_filter_val, actual_days, total_hours):
            ps_filters = {
                "project": contract_doc.project,
                "post": ["in", operation_post_names],
                "date": ["between", [start_date, end_date]],
                "post_status": "Planned",
            }
            if site_filter_val:
                ps_filters["site"] = site_filter_val

            post_schedules = frappe.get_all("Post Schedule", filters=ps_filters)
            required_days = len(post_schedules)

            rate_type = c_item.rate_type
            qty = 0.0

            if rate_type == "Monthly":
                if required_days == 0:
                    frappe.throw(_("Post Schedule missing for Operations Role associated with Contract Item {0}.").format(item_code))
                qty = (actual_days / required_days) * flt(c_item.count)
                if qty > flt(c_item.count):
                    frappe.throw(
                        _("Calculated Qty ({0}) for Item {1} exceeds the Contract Item Count ({2}).").format(
                            round(qty, 4), item_code, c_item.count
                        ), title=_("Quantity Exceeded")
                    )

            elif rate_type == "Daily":
                qty = actual_days

            elif rate_type == "Hourly":
                qty = total_hours

            if qty > 0:
                company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
                
                item_defaults = frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, 
                    ["income_account", "expense_account"], as_dict=True)
                
                if not item_defaults:
                    item_group = frappe.db.get_value("Item", item_code, "item_group")
                    item_defaults = frappe.db.get_value("Item Default", {"parent": item_group, "company": company}, 
                        ["income_account", "expense_account"], as_dict=True) or {}
                
                income_account = item_defaults.get("income_account") or frappe.db.get_value("Company", company, "default_income_account")
                cost_center = frappe.db.get_value("Company", company, "cost_center")
                expense_account = item_defaults.get("expense_account") or frappe.db.get_value("Company", company, "default_expense_account")

                si_items.append({
                    "item_code": item_code,
                    "item_name": item_code,
                    "description": c_item.item_description or c_item.item_name or item_code,
                    "qty": qty,
                    "uom": c_item.uom,
                    "rate": c_item.rate or c_item.item_price,
                    "amount": qty * flt(c_item.rate or c_item.item_price),
                    "custom_contract": contract,
                    "custom_contract_item": c_item.name,
                    "income_account": income_account,
                    "cost_center": cost_center,
                    "expense_account": expense_account,
                    "site": site_filter_val or ""
                })

        if mode in ["Separate Invoice for Each Site", "Separate Item Line for Each Site"]:
            for site, v in site_map.items():
                if site:
                    _add_item_for_site(site, v["actual_days"], v["total_hours"])
        else:
            total_actual = sum(v["actual_days"] for v in site_map.values())
            total_hrs = sum(v["total_hours"] for v in site_map.values())
            _add_item_for_site(None, total_actual, total_hrs)

    # Site handling logic
    mode = contract_doc.create_sales_invoice_as or "Single Invoice"
    site_to_return = ""
    
    if mode == "Single Invoice":
        project_sites = frappe.get_all("Operations Site", filters={"project": contract_doc.project}, pluck="name")
        if len(project_sites) == 1:
            site_to_return = project_sites[0]
            
        for d in si_items:
            d["site"] = site_to_return # Assign site to item rows as well

    # Since Get Items From is for pulling into a single invoice, "Separate Invoice for Each Site" is 
    # challenging to handle via frontend pull. We will pull all items, but site assignment might be sparse.
    # The user can manage sites manually.
    if mode == "Separate Invoice for Each Site":
        pass # Returning all aggregate site items without specific header site
            
    return {
        "items": si_items,
        "project": contract_doc.project,
        "site": site_to_return,
        "currency": contract_doc.currency_ or "KWD"
    }
