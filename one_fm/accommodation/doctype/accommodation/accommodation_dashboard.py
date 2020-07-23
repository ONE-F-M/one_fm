from __future__ import unicode_literals
from frappe import _

def get_data():
     return {
        'fieldname': 'accommodation',
        'transactions': [
            {
                'items': ['Accommodation Unit', 'Bed']
            },
            {
                'items': ['Accommodation Space']
            }
        ],
    }
