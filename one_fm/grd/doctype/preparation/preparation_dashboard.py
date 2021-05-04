from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'preparation',
        'transactions': [
            {
                'items': ['Work Permit']
            },
            {
                'items': ['Medical Insurance']
            },
            {
                'items': ['MOI Residency Jawazat']
            },
            {
                'items': ['PACI']
            }
            # {
            #     'items': ['Fingerprint']
            # }
        ],
    }

