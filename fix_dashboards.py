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
        
    link_items = [l["link_doctype"] for l in links]
    
    # Remove from JSON!
    data["links"] = []
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=1)
        
    # Generate dashboard.py
    chunks = [link_items[i:i + 2] for i in range(0, len(link_items), 2)]
    transactions_str = ",\n".join([f"            {{'items': {chunk}}}" for chunk in chunks])
    
    py_content = f"""from __future__ import unicode_literals
from frappe import _

def get_data():
    return {{
        'fieldname': 'candidate_country_process',
        'method': 'one_fm.utils.get_sibling_counts',
        'transactions': [
{transactions_str}
        ],
    }}
"""
    py_path = os.path.join(base_path, dt, f"{dt}_dashboard.py")
    with open(py_path, 'w') as f:
        f.write(py_content)
        
print("Fixed dashboards and added custom method!")
