from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'candidate_country_process',
        'method': 'one_fm.utils.get_sibling_counts',
        'transactions': [
            {'items': ['Candidate Country Process', 'Overseas Medical Appointment WAFID']},
            {'items': ['Overseas Remedical', 'PCC Clearance']},
            {'items': ['Arrival and Deployment']}
        ],
    }
