import json
import os

doctypes = [
    "pcc_clearance",
    "overseas_medical_appointment_wafid",
    "overseas_remedical",
    "visa_stamping",
    "arrival_and_deployment",
    "pam_visa"
]

base_path = "one_fm/one_fm/doctype"

for dt in doctypes:
    json_path = os.path.join(base_path, dt, f"{dt}.json")
    if not os.path.exists(json_path):
        continue
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    links = data.get("links", [])
    if not links:
        continue
        
    for link in links:
        if "group" in link:
            # Setting it to empty string or deleting it might make them group default
            del link["group"]
            
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=1)
        
print("Removed groups from links!")
