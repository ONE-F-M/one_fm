import frappe

def run():
    applicants = frappe.get_all("Job Applicant", filters=[["applicant_name", "like", "%test%6%"]], fields=["name", "applicant_name", "candidate_country_process"])
    print("Applicants:", applicants)
    
    arrivals = frappe.get_all("Arrival and Deployment", filters=[["candidate_name", "like", "%test%6%"]], fields=["name", "candidate_name", "candidate_country_process"])
    print("Arrivals:", arrivals)
