from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'request_for_purchase',
		'non_standard_fieldnames': {
			'Purchase Order': 'one_fm_request_for_purchase'
		},
		'transactions': [
			# {
			# 	'label': _('Related'),
			# 	'items': ['Purchase Receipt', 'Purchase Invoice']
			# },
			# {
			# 	'label': _('Payment'),
			# 	'items': ['Payment Entry', 'Journal Entry']
			# },
			{
				'label': _('Reference'),
				'items': ['Quotation From Supplier', 'Quotation Comparison Sheet', 'Request for Supplier Quotation', 'Purchase Order']
			}
		]
	}
