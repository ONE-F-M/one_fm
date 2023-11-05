from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'recruitment_trip_request',
		 'non_standard_fieldnames': {
		 	'Employee Advance': 'recruitment_trip_request',
		 },
		'transactions': [
            {
                'label': _('Expense'),
				'items': ['Employee Advance']
			},
		]
	}