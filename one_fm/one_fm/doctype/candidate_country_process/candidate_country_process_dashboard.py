from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'candidate_country_process',
        'transactions': [
            {
                'label': _('Tracking Processes'),
                'items': ['PAM Visa', 'Overseas Medical Appointment WAFID', 'Overseas Remedical', 'PCC Clearance', 'Visa Stamping', 'Arrival and Deployment']
            }
        ],
    }
