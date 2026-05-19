import os

doctypes = [
    "pcc_clearance",
    "overseas_medical_appointment_wafid",
    "overseas_remedical",
    "visa_stamping",
    "arrival_and_deployment",
    "pam_visa"
]

base_path = "/Users/kevinmakora/.gemini/antigravity/scratch/frappe-bench/apps/one_fm/one_fm/one_fm/doctype"

py_content = """from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'candidate_country_process',
        'method': 'one_fm.utils.get_sibling_counts',
        'transactions': [
            {'items': ['Candidate Country Process', 'Overseas Medical Appointment WAFID']},
            {'items': ['Overseas Remedical', 'PCC Clearance']},
            {'items': ['Visa Stamping', 'Arrival and Deployment']}
        ],
    }
"""

for dt in doctypes:
    py_path = os.path.join(base_path, dt, f"{dt}_dashboard.py")
    with open(py_path, 'w') as f:
        f.write(py_content)
        
print("Generated identical dashboard links for all sibling doctypes!")
