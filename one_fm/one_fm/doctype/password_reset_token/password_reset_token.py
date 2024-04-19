# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import (
	now_datetime, datetime
)


class PasswordResetToken(Document):
	
	def before_insert(self):
		self.expiration_time = now_datetime() + datetime.timedelta(minutes=7)

	def validate(self):
		current_time = now_datetime()
		if not self.expiration_time:
			self.expiration_time = current_time + datetime.timedelta(minutes=7)

		if self.expiration_time < current_time:
			self.status = "Revoked"


def revoke_password_tokens():
	"""
	Revoke all password tokens where expiration_time is less than NOW
	"""
	frappe.db.sql("""
		UPDATE `tabPassword Reset Token` 
		SET status='Revoked', modified=NOW()
		WHERE 
		expiration_time>NOW();
	""")