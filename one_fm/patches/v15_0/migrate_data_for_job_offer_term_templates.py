import frappe

def migrate_data():
    # Truncate the destination table first
    frappe.db.sql("TRUNCATE TABLE `tabJob Offer Term Template`")
    frappe.db.sql("TRUNCATE TABLE `tabJob Offer Term`")

    job_offer_templates = frappe.get_all("Job Offer Templates", fields=['name1'])

    for template in job_offer_templates:
        job_offer_term_template = frappe.new_doc("Job Offer Term Template")
        job_offer_term_template.title = template.name1
        offer_terms = frappe.get_all("Offer Terms Table Template", filters={"parent": template.name1}, fields=['offer_terms', 'valuedescription'])
        for offer_term in offer_terms:
            job_offer_term_template.append("offer_terms", {
                "offer_term": offer_term.offer_terms,
                "value": offer_term.valuedescription,
            })
        job_offer_term_template.insert()

def update_previous_records():
    job_offers = frappe.get_all("Job Offer", fields=['name','offer_term_templates'])

    for offer in job_offers:
        frappe.db.set_value("Job Offer", offer.name, "job_offer_term_template", offer.offer_term_templates)

def execute():
    # Migrate data for core field
    migrate_data()

    # Copy data from "Offer Term Templates" (Custom Field) to "Job Offer Term Template" (Core Field)
    update_previous_records()
    
    frappe.db.commit()
