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
                'items': ['Residency']
            },
            {
                'items': ['PACI']
            },
            {
                'items': ['Fingerprint Appointment']
            },
            # {
            #     'items': ['Payment Request']
            # }
        ],
    }

