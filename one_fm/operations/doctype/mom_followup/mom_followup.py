# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.desk.form.assign_to import add as add_assignment
from one_fm.api.notification import create_notification_log
from frappe import _
from one_fm.api.tasks import issue_penalty
from frappe.utils.data import nowdate
from datetime import datetime

# bench execute one_fm.operations.doctype.mom_followup.mom_followup.mom_project_followup
# bench execute one_fm.operations.doctype.mom_followup.mom_followup.mom_followup_reminder
# bench execute one_fm.operations.doctype.mom_followup.mom_followup.mom_sites_followup
# bench execute one_fm.operations.doctype.mom_followup.mom_followup.on_update
# bench execute one_fm.operations.doctype.mom_followup.mom_followup.test_function

class MOMFollowup(Document):
	def on_update(self):
		
		if self.workflow_state == 'Approved By Projects Manager':
			create_notification_log("NO ACTION Required - Missed MOM Reason Approved for site {0}".format(self.site), "Your Reason for Missed MOM has been Approved", [frappe.db.get_value('Employee',self.site_supervisor, 'user_id')],self)

		# elif self.workflow_state == 'Issue Penalty':
		# 	create_notification_log("PENALTY Issued - Missed MOM Reason NOT Approved for site {0}".format(self.site), "Your Reason for Missed MOM has been Approved", [frappe.db.get_value('Employee',self.site_supervisor, 'user_id')],self)
			
		# 	if self.penalty_type:
		# 		issue_penalty(self.site_supervisor, nowdate(),self.penalty_code,frappe.get_value('Shift Assignment',{'employee':self.site_supervisor},'shift'), self.project_manager,"Head Office")
		# else:
		# 	pass
	def on_update_after_submit(self):
		if self.penalty_type:
				issue_penalty(self.site_supervisor, nowdate(),self.penalty_code,frappe.get_value('Shift Assignment',{'employee':self.site_supervisor,'date':nowdate()},'shift'), self.project_manager,"Head Office")


	# def on_update(self):
	# 	if self.workflow_state == 'Review by Projects Manager':
	# 		count = 0
	# 		for assigned in self.assign:
	# 			project_manager = frappe.db.get_value('Employee',self.project_manager, 'user_id')
	# 			if assigned == project_manager:
	# 				count = count + 1
	# 		if count == 0:
	# 			add_assignment({
	# 				'doctype': 'MOM Followup',
	# 				'name': self.name,
	# 				'assign_to': frappe.db.get_value('Employee',self.project_manager, 'user_id'),
	# 				'description': _("ACTION - Missed MOM - {0}, Missed the MOM for Site {1} and a reason has been inputted".format(self.site_supervisor_name,self.site))
	# 			})

@frappe.whitelist()
def mom_sites_followup():
	moms = frappe.db.sql("""
		SELECT *
		FROM `tabMOM` 
		WHERE `date` BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 1 WEEK) AND CURRENT_DATE()
		""", as_dict=1)
	
	

##################################
	# Make a list of all POC's in the MOM based on the SQL Query 
	
	moms_poc = []

	for m in moms:

		moms_poc_list = frappe.get_doc('MOM', m.name) 
		for each_moms_poc_list in moms_poc_list.attendees:
			moms_poc.append(each_moms_poc_list)

##################################

	sites = frappe.db.sql("""
		SELECT *
		FROM `tabOperations Site`
		""", as_dict=1)
	
	

	for s in sites:
		sites_poc_list = frappe.get_doc('Operations Site', s.name) 

		count = 0

		for s_poc in sites_poc_list.poc:
			for m_poc in moms_poc:
				if m_poc.poc_name == s_poc.poc:
					count = count +1
	
		if count == 0:
			site = frappe.get_doc('Operations Site', s.name)
			followup = frappe.new_doc('MOM Followup')
			followup.poc = site.poc
			followup.project = site.project 
			followup.site = site.name 
			followup.site_supervisor = site.account_supervisor
			followup.insert()
			add_assignment({
					'doctype': 'MOM Followup',
					'name': followup.name,
					'assign_to': frappe.db.get_value('Employee',site.account_supervisor, 'user_id'),
					'description': _('Please explain your reason of missing the MOM for this site/POC within 48 hours')
				})
def mom_followup_reminder():
	
	reminder = frappe.db.sql("""
	SELECT * 
	FROM `tabMOM Followup` 
	WHERE (creation < DATE_SUB(NOW(), INTERVAL 48 HOUR)) AND (workflow_state = 'Assign to Site Supervisor')
	""", as_dict=1)
	for re in reminder:
		re.workflow_state = 'Review by Projects Manager'
		re.save()
		add_assignment({
					'doctype': 'MOM Followup',
					'name': re.name,
					'assign_to': frappe.db.get_value('Employee',re.project_manager, 'user_id'),
					'description': _('Please take Action')
		})

def test_function():
	test = datetime.now()
	
	print(test)

# WHERE creation < DATE_SUB(NOW(), INTERVAL 48 HOUR) AND (workflow_state = 'Assign to Site Supervisor')	
# 			
# def mom_project_followup():
# 	moms = frappe.db.sql("""
# 		SELECT *
# 		FROM `tabMOM` 
# 		WHERE `date` BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 1 WEEK) AND CURRENT_DATE()
# 		""", as_dict=1)
	
# 	projects = frappe.db.sql("""
# 		SELECT *
# 		FROM `tabProject` 
# 		WHERE project_type = 'External'
# 		""", as_dict=1)
# 	for p in projects:
# 		if p.status =='Open':
# 			count = 0
# 			for m in moms:
# 				if m.project == p.name:
# 					count = count +1
# 			if count == 0:
# 				print(p.name)

	




