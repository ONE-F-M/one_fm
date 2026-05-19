import frappe

def run():
    ccps = frappe.get_all("Candidate Country Process", limit=6, order_by="creation desc")
    for ccp in ccps:
        doc = frappe.get_doc("Candidate Country Process", ccp.name)
        if doc.agency_process_details:
            first_step = doc.agency_process_details[0]
            if first_step.process_name and "Job offer" in first_step.process_name:
                first_step.actual_date = doc.start_date
                first_step.status = "Approved"
                
                # Move current process to the next step
                for step in doc.agency_process_details[1:]:
                    if step.reference_type:
                        doc.current_process_id = step.name
                        break
                
                doc.save(ignore_permissions=True)
                print(f"Updated {doc.name}")
    frappe.db.commit()
