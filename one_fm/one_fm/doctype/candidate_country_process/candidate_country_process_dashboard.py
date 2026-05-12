from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'candidate_country_process',
        'transactions': [
            {"items": ['PAM Visa', 'Overseas Medical Appointment WAFID']},
            {"items": ['Overseas Remedical', 'PCC Clearance']},
            {"items": ['Visa Stamping', 'Arrival and Deployment']}
        ],
    }
