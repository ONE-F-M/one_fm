from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		#'fieldname': 'request_for_material',
		'non_standard_fieldnames': {
            'Delivery Note': 'request_for_material'
		},
		'transactions': [
			{
				'label': _('Reference'),
				'items': ['Sales Invoice', 'Delivery Note']
			}
		]
	}