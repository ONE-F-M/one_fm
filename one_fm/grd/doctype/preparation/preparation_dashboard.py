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
            # WI-002107: the two overseas sub-documents WI-002095 opens. Without a badge
            # each, the only way to reach them from the Preparation that created them was
            # to search their own lists.
            {
                'items': ['Medical Appointment']
            },
            {
                'items': ['PCC Attestation']
            },
            # {
            #     'items': ['Payment Request']
            # }
        ],
    }

