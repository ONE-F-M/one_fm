import base64, grpc, frappe, requests
from one_fm.proto import facial_recognition_pb2, facial_recognition_pb2_grpc, enroll_pb2, enroll_pb2_grpc
from frappe import _
from frappe.utils import (
	now_datetime, cstr, nowdate, cint , getdate, get_first_day, get_last_day
)
import numpy as np
import datetime, random
from json import JSONEncoder
# import cv2, os
# import face_recognition
import json
# from imutils import face_utils, paths
from one_fm.api.doc_events import haversine
from one_fm.api.v2.roster import get_current_shift
from one_fm.api.v2.utils import response
from one_fm.api.v2.face_recognition import create_checkin_log
from one_fm.api.utils import set_up_face_recognition_server_credentials

# setup channel for face recognition
face_recognition_service_url = frappe.local.conf.face_recognition_service_url
# channels = [
#     grpc.secure_channel(i, grpc.ssl_channel_credentials()) for i in face_recognition_service_url
# ]

# setup stub for face recognition
# stubs = [
#     facial_recognition_pb2_grpc.FaceRecognitionServiceStub(i) for i in channels
# ]

stubs = list()
channel = frappe.local.conf.face_recognition_channel.get('url')
bucketpath = frappe.local.conf.face_recognition_channel.get('bucket')

@frappe.whitelist()
def enroll():
	try:
		error = False
		message = ""
		files = frappe.request.files
		file = files['file']
		# Get user video
		content_bytes = file.stream.read()
		content_base64_bytes = base64.b64encode(content_bytes)
		video_content = content_base64_bytes.decode('ascii')
		# setup api endpoint
		setup_credentials = set_up_face_recognition_server_credentials()
		if setup_credentials.get('error'): #if error
			return setup_credentials
		
		r = requests.post(channel+"/enroll", json={
			'username': frappe.session.user, 
			'video':video_content,
			'filename':file.filename,
			'filetype':file.content_type,
			'bucketpath':bucketpath,
		}, timeout=180)
		# RESPONSE {'error': False|True, 'message': 'success|error message'}
		res_data = frappe._dict(r.json())
		if res_data.error:
			# process error
			frappe.log_error('Face Enrollment v3', res_data.message)
			error = True
			message = res_data.message
		else:
			doc = frappe.get_doc("Employee", {"user_id": frappe.session.user})
			doc.enrolled = 1
			doc.save(ignore_permissions=True)
			update_onboarding_employee(doc)
			frappe.db.commit()
		return {'error':False, 'message':'Enrollment successfull.'}
	except Exception as exc:
		frappe.log_error('Face Enrollment v3', frappe.get_traceback())
		frappe.db.commit()
		return {'error':True, 'message':'Your enrollment could not be completed, please contact your supervisor.'}


@frappe.whitelist()
def verify():
	try:
		log_type = frappe.local.form_dict.log_type
		skip_attendance = frappe.local.form_dict.skip_attendance
		latitude = frappe.local.form_dict.latitude
		longitude = frappe.local.form_dict.longitude
		# timestamp = frappe.local.form_dict.timestamp
		files = frappe.request.files
		file = files['file']

		employee = frappe.db.get_value("Employee", {'user_id': frappe.session.user}, ["name"])

		# Get user video
		content_bytes = file.stream.read()
		content_base64_bytes = base64.b64encode(content_bytes)
		video_content = content_base64_bytes.decode('ascii')

		# setup api endpoint
		setup_credentials = set_up_face_recognition_server_credentials()
		if setup_credentials.get('error'): #if error
			return setup_credentials
		
		r = requests.post(channel+"/verify", json={
			'username': frappe.session.user, 
			'video':video_content,
			'filename':file.filename,
			'filetype':file.content_type,
			'bucketpath':bucketpath,
		}, timeout=180)
		# RESPONSE {'error': False|True, 'message': 'success|error message'}
		res_data = frappe._dict(r.json())
		if res_data.error:
			if not res_data.text:
				frappe.log_error('Face Verify v3', res_data.message)
			return res_data
		# create_checkin_log()
		frappe.enqueue(check_in, log_type=log_type, skip_attendance=skip_attendance, 
			latitude=latitude, longitude=longitude, source="Mobile Web")
		# check_in(log_type=log_type, skip_attendance=skip_attendance, 
		# 	latitude=latitude, longitude=longitude, source="Mobile Web")
		# frappe.db.commit()
		return {'error':False, 'message':f'Check {log_type} Successful'}  
	except Exception as exc:
		frappe.log_error("Face Verify v3", frappe.get_traceback() + '\n\n\n' + str(frappe.form_dict))
		return {'error':True, 'message':'Checkin failed, please contact your supervisor.'} 

@frappe.whitelist()
def user_within_site_geofence(employee, log_type, user_latitude, user_longitude):
	""" This method checks if user's given coordinates fall within the geofence radius of the user's assigned site in Shift Assigment. """
	shift = get_current_shift(employee)
	date = cstr(getdate())
	if shift:
		if frappe.db.exists("Shift Request", {"employee":employee, 'from_date':['<=',date],'to_date':['>=',date]}):
			check_in_site, check_out_site = frappe.get_value("Shift Request", {"employee":employee, 'from_date':['<=',date],'to_date':['>=',date]},["check_in_site","check_out_site"])
			if log_type == "IN":
				location = frappe.get_list("Location", {'name':check_in_site}, ["latitude","longitude", "geofence_radius"])
			else:
				location = frappe.get_list("Location", {'name':check_out_site}, ["latitude","longitude", "geofence_radius"])			
		
		else:
			if shift.site_location:
				location = frappe.get_list("Location", {'name':shift.site_location}, ["latitude","longitude", "geofence_radius"])
			elif shift.shift:
				site = frappe.get_value("Operations Shift", shift.shift, "site")
				location= frappe.db.sql("""
					SELECT loc.latitude, loc.longitude, loc.geofence_radius
					FROM `tabLocation` as loc
					WHERE
					loc.name IN (SELECT site_location FROM `tabOperations Site` where name="{site}")
					""".format(site=site), as_dict=1)

		if location:
			location_details = location[0]
			distance = float(haversine(location_details.latitude, location_details.longitude, user_latitude, user_longitude))
			if distance <= float(location_details.geofence_radius):
				return True
	return False

def check_in(log_type, skip_attendance, latitude, longitude, source):
	try:
		employee = frappe.get_value("Employee", {"user_id": frappe.session.user})
		checkin = frappe.new_doc("Employee Checkin")
		checkin.employee = employee
		checkin.log_type = log_type
		checkin.device_id = cstr(latitude)+","+cstr(longitude)
		checkin.skip_auto_attendance = cint(skip_attendance)
		checkin.source = source
		# checkin.shift_assignment = get_current_shift(employee)
		# checkin.time = now_datetime()
		# checkin.actual_time = now_datetime()
		checkin.save()
		frappe.db.commit()
		return _('Check {log_type} successful! {docname}'.format(log_type=log_type.lower(), docname=checkin.name))
	except:
		frappe.log_error('Mobile Web Checkin', frappe.get_traceback())

@frappe.whitelist()
def forced_checkin(employee, log_type, time):
	checkin = frappe.new_doc("Employee Checkin")
	checkin.employee = employee
	checkin.log_type = log_type
	checkin.device_id = cstr('0')+","+cstr('0')
	checkin.skip_auto_attendance = cint('0')
	checkin.time = time
	checkin.actual_time = time
	# checkin.shift_assignment = get_current_shift(employee)
	checkin.save()
	frappe.db.commit()
	return _('Check {log_type} successful! {docname}'.format(log_type=log_type.lower(), docname=checkin.name))

def update_onboarding_employee(employee):
    onboard_employee_exist = frappe.db.exists('Onboard Employee', {'employee': employee.name})
    if onboard_employee_exist:
        onboard_employee = frappe.get_doc('Onboard Employee', onboard_employee_exist.name)
        onboard_employee.enrolled = True
        onboard_employee.enrolled_on = now_datetime()
        onboard_employee.save(ignore_permissions=True)
        frappe.db.commit()


def update_onboarding_employee(employee):
    onboard_employee_exist = frappe.db.exists('Onboard Employee', {'employee': employee.name})
    if onboard_employee_exist:
        onboard_employee = frappe.get_doc('Onboard Employee', onboard_employee_exist)
        onboard_employee.enrolled = True
        onboard_employee.enrolled_on = now_datetime()
        onboard_employee.save(ignore_permissions=True)
        frappe.db.commit()

@frappe.whitelist()
def check_existing():
	"""API to determine the applicable Log type.
	The api checks employee's last lcheckin log type. and determine what next log type needs to be
	Returns:
		True: The log in was "IN", so his next Log Type should be "OUT".
		False: either no log type or last log type is "OUT", so his next Ltg Type should be "IN".
	"""
	employee = frappe.get_value("Employee", {"user_id": frappe.session.user})

	# define logs
	logs = []
	
	# get current and previous day date.
	today = nowdate()
	prev_date = ((datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")).split(" ")[0]

	#get Employee Schedule
	last_shift = frappe.get_list("Shift Assignment",fields=["*"],filters={"employee":employee},order_by='creation desc',limit_page_length=1)

	if not employee:
		frappe.throw(_("Please link an employee to the logged in user to proceed further."))

	shift = get_current_shift(employee)
	#if employee schedule is linked with the previous Checkin doc

	if shift and last_shift:
		start_date = (shift.start_date).strftime("%Y-%m-%d")
		if start_date == today or start_date == prev_date:
			logs = frappe.db.sql("""
				select log_type from `tabEmployee Checkin` where skip_auto_attendance=0 and employee="{employee}" and shift_assignment="{shift_assignment}"
				""".format(employee=employee, shift_assignment=last_shift[0].name), as_dict=1)
	else:
		#get checkin log of today.
		logs = frappe.db.sql("""
			select log_type from `tabEmployee Checkin` where date(time)=date("{date}") and skip_auto_attendance=0 and employee="{employee}"
			""".format(date=today, employee=employee), as_dict=1)
	val = [log.log_type for log in logs]

	#For Check IN
	if not val or (val and val[-1] == "OUT"):
		return False
	#For Check OUT
	else:
		return True


@frappe.whitelist()
def get_checkin_history(employee):

	"""
		RETRIEVE CHECKIN LOGS
	"""
	start = str(get_first_day(getdate()))
	end = str(get_last_day(getdate()))
	logs = frappe.db.sql(f"""
		SELECT name, log_type, time FROM `tabEmployee Checkin`
		WHERE employee="{employee}" AND date BETWEEN '{start}' AND '{end}'
		ORDER BY time DESC
	""", as_dict=1)
	response ("success", 200, {'logs':logs, 'start':start, 'end':end})
