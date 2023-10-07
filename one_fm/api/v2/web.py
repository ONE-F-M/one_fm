import base64
import grpc
from one_fm.proto import facial_recognition_pb2, facial_recognition_pb2_grpc, enroll_pb2, enroll_pb2_grpc
import frappe
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
from one_fm.api.utils import _check_existing, _get_current_shift

# setup channel for face recognition
face_recognition_service_url = frappe.local.conf.face_recognition_service_url
channels = [
    grpc.secure_channel(i, grpc.ssl_channel_credentials()) for i in face_recognition_service_url
]

# setup stub for face recognition
stubs = [
    facial_recognition_pb2_grpc.FaceRecognitionServiceStub(i) for i in channels
]

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)

def setup_directories():
	"""
		Use this function to create directories needed for the face recognition system: dataset directory and facial embeddings
	"""
	from pathlib import Path
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/user/").mkdir(parents=True, exist_ok=True)
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/dataset/").mkdir(parents=True, exist_ok=True)
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/facial_recognition/").mkdir(parents=True, exist_ok=True)
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/face_rec_temp/").mkdir(parents=True, exist_ok=True)
	Path(frappe.utils.cstr(frappe.local.site)+"/private/files/dataset/"+frappe.session.user+"/").mkdir(parents=True, exist_ok=True)

@frappe.whitelist()
def enroll():
	try:
		files = frappe.request.files
		file = files['file']
		
		# Get user video
		content_bytes = file.stream.read()
		content_base64_bytes = base64.b64encode(content_bytes)
		video_content = content_base64_bytes.decode('ascii')

		# Setup channel
		face_recognition_enroll_service_url = frappe.local.conf.face_recognition_enroll_service_url
		channel = grpc.secure_channel(face_recognition_enroll_service_url, grpc.ssl_channel_credentials())
		# setup stub
		stub = enroll_pb2_grpc.FaceRecognitionEnrollmentServiceStub(channel)
			# request body
		req = enroll_pb2.EnrollRequest(
			username = frappe.session.user,
			user_encoded_video = video_content,
		)

		res = random.choice(stubs).FaceRecognition(req)
		
		if res.enrollment == "FAILED":
			msg = res.message
			data = res.data
			frappe.throw(_("{msg}: {data}".format(msg=msg, data=data)))
		
		doc = frappe.get_doc("Employee", {"user_id": frappe.session.user})
		doc.enrolled = 1
		doc.save(ignore_permissions=True)
		update_onboarding_employee(doc)
		frappe.db.commit()
		return _("Successfully Enrolled!")

	except Exception as exc:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		raise exc


@frappe.whitelist()
def verify():
	# print(frappe.local.request.files)
	try:
		log_type = frappe.local.form_dict.log_type
		skip_attendance = frappe.local.form_dict.skip_attendance
		latitude = frappe.local.form_dict.latitude
		longitude = frappe.local.form_dict.longitude
		# timestamp = frappe.local.form_dict.timestamp
		files = frappe.request.files
		file = files['file']

		employee = frappe.db.get_value("Employee", {'user_id': frappe.session.user}, ["name"])

		# if not user_within_site_geofence(employee, log_type, latitude, longitude):
		# 	frappe.throw("Please check {log_type} at your site location.".format(log_type=log_type))

		# Get user video
		content_bytes = file.stream.read()
		content_base64_bytes = base64.b64encode(content_bytes)
		video_content = content_base64_bytes.decode('ascii')

		print(video_content)
		# request body
		req = facial_recognition_pb2.FaceRecognitionRequest(
			username = frappe.session.user,
			media_type = "video",
			media_content = video_content,
		)
		# Call service stub and get response
		res = random.choice(stubs).FaceRecognition(req)
		if res.verification == "FAILED":
			msg = res.message
			data = res.data
            #response("Bad Request", 400, None, _("{msg}: {data}".format(msg=msg, data=data)))
		# create_checkin_log()
		response("Success", 200, check_in(log_type, skip_attendance, latitude, longitude, "Mobile Web"))        
	except Exception as exc:
		frappe.log_error(frappe.get_traceback() + '\n\n\n' + str(frappe.form_dict))
		response("Error", 500, None, frappe.get_traceback())  

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
		frappe.log_error(frappe.get_traceback(), 'Mobile Web Checkin')

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

	shift = _get_current_shift(employee)
	if shift:
		log_type = _check_existing(shift)
		if log_type=='IN':
			return True
		else:
			return False
	return frappe.throw("Shift not found.")


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
