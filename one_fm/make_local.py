import frappe

def run():
    arrivals = frappe.get_all("Arrival and Deployment", filters=[["candidate_name", "like", "%Test Candidate Flow 6%"]], fields=["name", "candidate_name", "candidate_country_process"])
    print("Arrivals:", arrivals)
    
    for a in arrivals:
        frappe.db.set_value("Arrival and Deployment", a.name, "candidate_country_process", "")
        print(f"Cleared candidate_country_process for {a.name}")
        
    frappe.db.commit()
