import frappe

def run():
    applicant = frappe.get_all("Job Applicant", filters={"applicant_name": "Test Candidate Flow 3"}, fields=["name", "one_fm_applicant_is_overseas_or_local", "one_fm_hiring_method"])
    if applicant:
        print(f"Applicant: {applicant[0]}")
    else:
        print("Applicant not found")
