import frappe

def run():
    doc = frappe.get_doc("DocType", "Arrival and Deployment")
    
    # Make candidate_country_process not mandatory
    for df in doc.fields:
        if df.fieldname == "candidate_country_process":
            df.reqd = 0
        if df.fieldname == "candidate_name":
            df.fetch_from = ""
            df.read_only = 0
        if df.fieldname == "passport_number":
            df.fetch_from = ""
            df.read_only = 0
            
    # Add Job Applicant and Job Offer fields if not exist
    has_applicant = False
    has_offer = False
    for df in doc.fields:
        if df.fieldname == "job_applicant": has_applicant = True
        if df.fieldname == "job_offer": has_offer = True
        
    if not has_applicant:
        doc.append("fields", {
            "fieldname": "job_applicant",
            "fieldtype": "Link",
            "options": "Job Applicant",
            "label": "Job Applicant",
            "insert_after": "candidate_country_process"
        })
    if not has_offer:
        doc.append("fields", {
            "fieldname": "job_offer",
            "fieldtype": "Link",
            "options": "Job Offer",
            "label": "Job Offer",
            "insert_after": "job_applicant"
        })
        
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    print("Arrival and Deployment DocType patched.")
