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
    # First delete the _dashboard.py if it exists
    py_path = os.path.join(base_path, dt, f"{dt}_dashboard.py")
    if os.path.exists(py_path):
        os.remove(py_path)
        
    json_path = os.path.join(base_path, dt, f"{dt}.json")
    if not os.path.exists(json_path):
        continue
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    # Let's add them back as links but without 'group'
    # Wait, the previous script cleared them. I need to get them from git!
