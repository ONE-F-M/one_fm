# Copyright (c) 2021, omar jaber, Anthony Emmanuel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today
from frappe import _
from frappe.model.document import Document

class ItemReservation(Document):
	def before_insert(self):
		# check for backdating
		if(self.to < today()):
			frappe.throw(_({
				'title':'Date Error',
				'message':'You cannot backdate reservation date.'
			}))
