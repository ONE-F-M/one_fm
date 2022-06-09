# Copyright (c) 2022, Anthony Emmanuel and contributors
# For license information, please see license.txt

from datetime import datetime
import frappe, requests
from frappe.utils import today
from frappe.model.document import Document

class ERPNextInstance(Document):
	def before_insert(self):
		# generate hash
		state = True
		while state:
			secret_key = frappe.generate_hash(length=20)
			if(not frappe.db.exists('ERPNext Instance', {'secret_key':secret_key})):
				self.secret_key = secret_key
				state = False

	def validate(self):
		if (datetime.strptime(today(), '%Y-%m-%d').date() > datetime.strptime(self.subscription_end_date, '%Y-%m-%d').date()):
			self.active = 0
		if(datetime.strptime(self.subscription_end_date, '%Y-%m-%d').date() <= datetime.strptime(self.subscription_start_date, '%Y-%m-%d').date()):
			frappe.throw("End Date cannot be before start date.")

	def on_update(self):
		# update_instance(self)
		frappe.enqueue(
			method="convergenix_site_manager.convergenix_site_manager.doctype.erpnext_instance.erpnext_instance.update_instance",
			**{'doc':self})

def update_instance(doc):
	try:
		res = requests.post(f"{doc.url}/api/method/convergenix_app.api.api.update_subscription_status",
        json={'sk':doc.secret_key, 'active':doc.active}, timeout=10)
	except Exception as e:
		frappe.log_error(str(e), 'update subscription')
