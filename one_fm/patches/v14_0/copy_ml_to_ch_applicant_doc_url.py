import frappe

def execute():
    frappe.reload_doctype('Job Applicant')
    query = '''
        Update
            `tabJob Applicant`
        Set
            career_history_ml_url = Case when (career_history_ml_url is NULL or career_history_ml_url='') and magic_link like '%career_history%' then magic_link else career_history_ml_url end,
            applicant_doc_ml_url = Case when (applicant_doc_ml_url is NULL or applicant_doc_ml_url='') and magic_link like '%applicant_doc%' then magic_link else applicant_doc_ml_url end
        Where
            magic_link is not NULL
    '''
    frappe.db.sql(query)
