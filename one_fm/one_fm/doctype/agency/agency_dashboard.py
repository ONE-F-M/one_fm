from __future__ import unicode_literals
from frappe import _

def get_data():
        return {
                'fieldname': 'agency',
                'non_standard_fieldnames': {
                        'Country Process': 'agency',
                },
                'transactions': [
                        {
                                'items': ['Country Process']
                        },
                ]
        }

