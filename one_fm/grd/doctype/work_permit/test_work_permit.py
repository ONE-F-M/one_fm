# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and Contributors
# See license.txt
from __future__ import unicode_literals

# import frappe
import unittest
import frappe
from frappe.model.document import Document
from frappe.utils import today, add_days, get_url

class TestWorkPermit(unittest.TestCase):
	def on_submit(self):
		pass
	


def create_work_permit_renewal():
	date_after_14_days = add_days(today(), 14)
	# Get employee list
	query = """
		select
			*
		from
			tabEmployee
		where
			active=1 and one_fm_work_permit is NOT NUL and
			(one_fm_renewal_date is NOT NULL and one_fm_work_permit_renewal_date = %(date_after_14_days)))
	"""
	employee_list = frappe.db.sql(query.format(), {'date_after_14_days': date_after_14_days}, as_dict=True)
	print(employee_list)

    # for employee in employee_list:
    #     create_work_permit(employee)