from __future__ import unicode_literals
from frappe import _

def get_data():
        return {
                'fieldname': 'job_applicant',
                'non_standard_fieldnames': {
                        'Interview Result': 'job_applicant',
                },
                'transactions': [
                        {
                                'items': ['Interview Result']
                        },
                ]
        }
