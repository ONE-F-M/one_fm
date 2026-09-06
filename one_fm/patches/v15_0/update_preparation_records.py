import frappe

def execute():
    update_grd_settings()
    renewal_costs = get_renewal_costs()
    update_preparation_records(renewal_costs)

def update_grd_settings():
    doc = frappe.get_doc("HR Settings", "HR Settings")
    
    rows_to_remove = []
    for idx, row in enumerate(doc.renewal_extension_cost):
        if row.renewal_or_extend == "Renewal":
            rows_to_remove.append(idx)
    
    for idx in reversed(rows_to_remove):
        doc.renewal_extension_cost.pop(idx)
    
    doc.append("renewal_extension_cost", {
        "renewal_or_extend": "Renewal (Kuwaiti)",
        "no_of_years": "1 Year",
        "work_permit_amount": 10.0,
        "medical_insurance_amount": 0.0,
        "residency_stamp_amount": 0.0,
        "civil_id_amount": 0.0,
        "total_amount": 10.0
    })
    
    doc.append("renewal_extension_cost", {
        "renewal_or_extend": "Renewal Expat",
        "no_of_years": "1 Year",
        "work_permit_amount": 10.0,
        "medical_insurance_amount": 50.0,
        "residency_stamp_amount": 10.0,
        "civil_id_amount": 5.0,
        "total_amount": 75.0
    })
    
    doc.flags.ignore_mandatory = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    print(f"HR Settings: Removed {len(rows_to_remove)} 'Renewal' row(s)")
    print("HR Settings: Added 'Renewal (Kuwaiti)' and 'Renewal Expat'")

def get_renewal_costs():
    doc = frappe.get_doc("HR Settings", "HR Settings")
    
    costs = {}
    for row in doc.renewal_extension_cost:
        if row.renewal_or_extend in ["Renewal (Kuwaiti)", "Renewal Expat"]:
            costs[row.renewal_or_extend] = {
                "work_permit_amount": row.work_permit_amount,
                "medical_insurance_amount": row.medical_insurance_amount,
                "residency_stamp_amount": row.residency_stamp_amount,
                "civil_id_amount": row.civil_id_amount,
                "total_amount": row.total_amount
            }
    
    return costs

def update_preparation_records(renewal_costs):
    preparation_records = frappe.db.sql("""
        SELECT pr.name, pr.parent, pr.employee, e.one_fm_nationality
        FROM `tabPreparation Record` pr
        INNER JOIN `tabEmployee` e ON pr.employee = e.name
        WHERE pr.renewal_or_extend = 'Renewal'
    """, as_dict=1)
    
    if not preparation_records:
        print("No Preparation Records found to update")
        return
    
    kuwaiti_count = 0
    non_kuwaiti_count = 0
    
    for record in preparation_records:
        is_kuwaiti = record.one_fm_nationality == "Kuwaiti"
        renewal_type = "Renewal (Kuwaiti)" if is_kuwaiti else "Renewal Expat"
        
        costs = renewal_costs.get(renewal_type)
        if not costs:
            print(f"Warning: No costs found for {renewal_type}")
            continue
        
        frappe.db.set_value("Preparation Record", record.name, {
            "renewal_or_extend": renewal_type,
            "work_permit_amount": costs["work_permit_amount"],
            "medical_insurance_amount": costs["medical_insurance_amount"],
            "residency_stamp_amount": costs["residency_stamp_amount"],
            "civil_id_amount": costs["civil_id_amount"],
            "total_amount": costs["total_amount"]
        }, update_modified=False)
        
        if is_kuwaiti:
            kuwaiti_count += 1
        else:
            non_kuwaiti_count += 1
    
    frappe.db.commit()
    
    print(f"Preparation Records: Updated {kuwaiti_count} Kuwaiti records")
    print(f"Preparation Records: Updated {non_kuwaiti_count} Non-Kuwaiti records")
    print(f"Total Preparation Records updated: {len(preparation_records)}")