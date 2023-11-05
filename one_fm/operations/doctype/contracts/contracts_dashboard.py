from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'contracts',
		'non_standard_fieldnames': {
			'Sales Invoice': 'contracts',
			'Delivery Note': 'contracts',
			'Additional Deployment': 'contracts'
		},
		'transactions': [
			{
				'items': ['Sales Invoice', 'Delivery Note','Additional Deployment']
			},
		]
	}