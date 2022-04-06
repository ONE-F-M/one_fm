# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.tx

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import datetime
from datetime import timedelta
import calendar
import frappe.utils.data as utils 

# bench execute one_fm.operations.doctype.checkpoints_route_assignment.checkpoints_route_assignment.assign_checkpoints

class CheckpointsRouteAssignment(Document):
    pass

@frappe.whitelist()
def assign_checkpoints():

	weekday = calendar.day_name[datetime.date.today().weekday()]

	assign_daily = frappe.db.sql("""
		SELECT *
		FROM `tabCheckpoints Route Assignment` 
		WHERE route_status = 'Active' AND (end_date >= CURDATE() OR never_ending = '1') AND daily_repeat = '1'
		""", as_dict=1)
	
	assign_weekly = frappe.db.sql("""
		SELECT *
		FROM `tabCheckpoints Route Assignment` 
		WHERE route_status = 'Active' AND (end_date >= CURDATE() OR never_ending = '1') AND weekly_repeat = '1' AND {0}= '1'
		""".format(weekday), as_dict=1)


	# Assign checkpoints for all Routes
	for each_route in assign_daily:
		# Assign the check point if it is a loose schedule
		if each_route.loose_schedule == 1:
			
			# Assign chekcpoint if Hourly Repeat
			if each_route.hourly_repeat == 1:
				# Assign the checkpoint using the hourly repeat time
				route = frappe.get_doc('Checkpoints Route Assignment', each_route.name)
				for each_checkpoint in route.checkpoints_route_assignment_loose_schedule_table:
					
					# if the repeat end time is greater than the  will result in the next day
					if route.start_time > route.repeat_end_time:
						repeatenddate = datetime.date.today()+ timedelta(days=1)
						repeatenddatetimestrg = repeatenddate.strftime("%Y-%m-%d") + " " + str(route.repeat_end_time)
						repeatenddatetime = utils.get_datetime(repeatenddatetimestrg)
					else:
						# Making start time to string and adding to it todays date then make into datetime
						repeatenddatetimestrg = datetime.date.today().strftime("%Y-%m-%d") + " " + str(route.repeat_end_time)
						repeatenddatetime = utils.get_datetime(repeatenddatetimestrg)

					# Making start time to string and adding to it todays date then make into datetime
					startdatetimestrg = datetime.date.today().strftime("%Y-%m-%d") + " " + str(route.start_time)
					startdatetime = utils.get_datetime(startdatetimestrg)
					
					# end time
					enddatetime = startdatetime + route.repeat_duration
					

					while enddatetime <= repeatenddatetime:
						assignment = frappe.new_doc('Checkpoints Assignment')
						assignment.checkpoint_name = each_checkpoint.checkpoint_name
						assignment.route_name = route.route_name
						assignment.employee = route.employee
						assignment.post = route.post
						assignment.start_date_time = startdatetime
						assignment.end_date_time = enddatetime
						# assignment.checkpoint_form_template = (Need to develop)
						assignment.insert()
						startdatetime = startdatetime + route.repeat_duration
						enddatetime = enddatetime + route.repeat_duration
						

			else:
				# Assign using the loose Time with Daily Repeat
				route = frappe.get_doc('Checkpoints Route Assignment', each_route.name)
				for each_checkpoint in route.checkpoints_route_assignment_loose_schedule_table:
					
					# if the end time is greater than the  will result in the next day
					if route.start_time > route.end_time:
						# Making start time to string and adding to it todays date then make into datetime
						startdatetimestrg = datetime.date.today().strftime("%Y-%m-%d") + " " + str(route.start_time)
						startdatetime = utils.get_datetime(startdatetimestrg)
						
						# Making end time to string and adding to it todays date then make into datetime
						enddate = datetime.date.today()+ timedelta(days=1)
						enddatetimestrg = enddate.strftime("%Y-%m-%d") + " " + str(route.end_time)
						enddatetime = utils.get_datetime(enddatetimestrg)

						# Assigning the Checkpoint
						assignment = frappe.new_doc('Checkpoints Assignment')
						assignment.checkpoint_name = each_checkpoint.checkpoint_name
						assignment.route_name = route.route_name
						assignment.employee = route.employee
						assignment.post = route.post
						assignment.start_date_time = startdatetime
						assignment.end_date_time = enddatetime
						# assignment.checkpoint_form_template = (Need to develop)
						assignment.insert()
						
					else:
						# Making start time to string and adding to it todays date then make into datetime
						startdatetimestrg = datetime.date.today().strftime("%Y-%m-%d") + " " + str(route.start_time)
						startdatetime = utils.get_datetime(startdatetimestrg)

						
						# Making end time to string and adding to it todays date then make into datetime
						enddatetimestrg = datetime.date.today().strftime("%Y-%m-%d") + " " + str(route.end_time)
						enddatetime = utils.get_datetime(enddatetimestrg)
						
						# Assigning the Checkpoint
						assignment = frappe.new_doc('Checkpoints Assignment')
						assignment.checkpoint_name = each_checkpoint.checkpoint_name
						assignment.route_name = route.route_name
						assignment.employee = route.employee
						assignment.post = route.post
						assignment.start_date_time = startdatetime
						assignment.end_date_time = enddatetime
						# assignment.checkpoint_form_template = (Need to develop)
						assignment.insert()
			# This is for the 
		elif each_route.loose_schedule == 0:
			# Assign the schedule 
			if each_route.hourly_repeat == 1:
				
				route = frappe.get_doc('Checkpoints Route Assignment', each_route.name)
				print(route.route_name)
				for each_checkpoint in route.checkpoints_route_table:
					print(each_checkpoint.checkpoint_name)
					
					# if the repeat end time is greater than the  will result in the next day
					if each_checkpoint.time > route.repeat_end_time:
						repeatenddate = datetime.date.today()+ timedelta(days=1)
						repeatenddatetimestrg = repeatenddate.strftime("%Y-%m-%d") + " " + str(route.repeat_end_time)
						repeatenddatetime = utils.get_datetime(repeatenddatetimestrg)
						print(each_checkpoint.time, repeatenddatetime)
					else:
						# Making start time to string and adding to it todays date then make into datetime
						repeatenddatetimestrg = datetime.date.today().strftime("%Y-%m-%d") + " " + str(route.repeat_end_time)
						repeatenddatetime = utils.get_datetime(repeatenddatetimestrg)
						print(each_checkpoint.time, repeatenddatetime)

					# Making start time to string and adding to it todays date then make into datetime
					startdatetimestrg = datetime.date.today().strftime("%Y-%m-%d") + " " + str(each_checkpoint.time)
					startdatetime = utils.get_datetime(startdatetimestrg)
					
					# end time
					enddatetime = startdatetime + each_checkpoint.tolerance
					

					while enddatetime <= repeatenddatetime:
						print(startdatetime, enddatetime)
						assignment = frappe.new_doc('Checkpoints Assignment')
						assignment.checkpoint_name = each_checkpoint.checkpoint_name
						assignment.route_name = route.route_name
						assignment.employee = route.employee
						assignment.post = route.post
						assignment.start_date_time = startdatetime
						assignment.end_date_time = enddatetime
						# assignment.checkpoint_form_template = (Need to develop)
						assignment.insert()
						startdatetime = startdatetime + route.repeat_duration
						enddatetime = enddatetime + route.repeat_duration

			else:
				# Assign using the scheduled with Daily Repeat
				route = frappe.get_doc('Checkpoints Route Assignment', each_route.name)
				past_checkpoint_time = datetime.datetime.min.time()
				for each_checkpoint in route.checkpoints_route_table:
					# dt = datetime.date.today() + timedelta(days=1)
					# next_day= datetime.datetime.combine(dt, datetime.datetime.min.time()))
					# if the end time is greater than the  will result in the next day
					print((datetime.datetime.min + each_checkpoint.time).time())
					print(past_checkpoint_time)
					if (datetime.datetime.min + each_checkpoint.time).time() < past_checkpoint_time:
						# Making start time to string and adding to it todays date then make into datetime
						startdate = datetime.date.today() + timedelta(days=1)
						startdatetimestrg = startdate.strftime("%Y-%m-%d") + " " + str(each_checkpoint.time)
						startdatetime = utils.get_datetime(startdatetimestrg)
						
						# Making end time to string and adding to it todays date then make into datetime
						enddate = datetime.date.today()+ timedelta(days=1)
						enddatetimestrg = enddate.strftime("%Y-%m-%d") + " " + str(each_checkpoint.tolerance)
						enddatetime = utils.get_datetime(enddatetimestrg)

						# Assigning the Checkpoint
						assignment = frappe.new_doc('Checkpoints Assignment')
						assignment.checkpoint_name = each_checkpoint.checkpoint_name
						assignment.route_name = route.route_name
						assignment.employee = route.employee
						assignment.post = route.post
						assignment.start_date_time = startdatetime
						assignment.end_date_time = enddatetime
						# assignment.checkpoint_form_template = (Need to develop)
						assignment.insert()
						past_checkpoint_time = (datetime.datetime.min + each_checkpoint.time).time()
						
					else:
						# Making start time to string and adding to it todays date then make into datetime
						startdatetimestrg = datetime.date.today().strftime("%Y-%m-%d") + " " + str(each_checkpoint.time)
						startdatetime = utils.get_datetime(startdatetimestrg)

						
						# Making end time to string and adding to it todays date then make into datetime
						enddatetime = startdatetime + each_checkpoint.tolerance
						 
						
						# Assigning the Checkpoint
						assignment = frappe.new_doc('Checkpoints Assignment')
						assignment.checkpoint_name = each_checkpoint.checkpoint_name
						assignment.route_name = route.route_name
						assignment.employee = route.employee
						assignment.post = route.post
						assignment.start_date_time = startdatetime
						assignment.end_date_time = enddatetime
						# assignment.checkpoint_form_template = (Need to develop)
						assignment.insert()
						past_checkpoint_time = (datetime.datetime.min + each_checkpoint.time).time()

		else:
			pass 