import base64
import grpc
from one_fm.proto import facial_recognition_pb2_grpc, facial_recognition_pb2, enroll_pb2, enroll_pb2_grpc
import frappe
from frappe import _
from frappe.utils import now_datetime, cstr, nowdate, cint
import numpy as np
import datetime
from json import JSONEncoder

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
		username = file.filename
		
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
		req = enroll_pb2.Request(
			username = username,
			user_encoded_video = video_content,
		)

		res = stub.FaceRecognitionEnroll(req)

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
	try:

		log_type = frappe.local.form_dict['log_type']
		skip_attendance = frappe.local.form_dict['skip_attendance']
		latitude = frappe.local.form_dict['latitude']
		longitude = frappe.local.form_dict['longitude']
		# timestamp = frappe.local.form_dict['timestamp']
		files = frappe.request.files
		file = files['file']
		user_name = file.filename
		
		# Get user video
		content_bytes = file.stream.read()
		content_base64_bytes = base64.b64encode(content_bytes)
		video_content = content_base64_bytes.decode('ascii')

		# setup channel
		face_recognition_service_url = frappe.local.conf.face_recognition_service_url
		channel = grpc.secure_channel(face_recognition_service_url, grpc.ssl_channel_credentials())
		# setup stub
		stub = facial_recognition_pb2_grpc.FaceRecognitionServiceStub(channel)

		# request body
		req = facial_recognition_pb2.Request(
			username = user_name,
			user_encoded_video = video_content,
		)
		# Call service stub and get response
		res = stub.FaceRecognition(req)
		
		if res.verification == "FAILED":
			msg = res.message
			data = res.data
			frappe.throw(_("{msg}: {data}".format(msg=msg, data=data)))

		return check_in(log_type, skip_attendance, latitude, longitude)
	except Exception as exc:
		frappe.log_error(frappe.get_traceback())
		raise exc


def check_in(log_type, skip_attendance, latitude, longitude):
	employee = frappe.get_value("Employee", {"user_id": frappe.session.user})
	checkin = frappe.new_doc("Employee Checkin")
	checkin.employee = employee
	checkin.log_type = log_type
	checkin.device_id = cstr(latitude)+","+cstr(longitude)
	checkin.skip_auto_attendance = cint(skip_attendance)
	# checkin.time = now_datetime()
	# checkin.actual_time = now_datetime()
	checkin.save()
	frappe.db.commit()
	return _('Check {log_type} successful! {docname}'.format(log_type=log_type.lower(), docname=checkin.name))

@frappe.whitelist()
def forced_checkin(employee, log_type, time):
	checkin = frappe.new_doc("Employee Checkin")
	checkin.employee = employee
	checkin.log_type = log_type
	checkin.device_id = cstr('0')+","+cstr('0')
	checkin.skip_auto_attendance = cint('0')
	checkin.time = time
	checkin.actual_time = time
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

@frappe.whitelist()
def check_existing():
	"""API to determine the applicable Log type. 
	The api checks employee's last lcheckin log type. and determine what next log type needs to be

	Returns:
		True: The log in was "IN", so his next Log Type should be "OUT".
		False: either no log type or last log type is "OUT", so his next Ltg Type should be "IN".
	"""	
	employee = frappe.get_value("Employee", {"user_id": frappe.session.user})
	
	# get current and previous day date.
	todate = nowdate()
	prev_date = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime ('%Y-%m-%d')

	if not employee:
		frappe.throw(_("Please link an employee to the logged in user to proceed further."))

	#get checkin log previous days and current date.
	logs = frappe.db.sql("""
			select log_type from `tabEmployee Checkin` where date(time) BETWEEN '{date1}' and '{date2}' and skip_auto_attendance=0 and employee="{employee}"
			""".format(date1=prev_date, date2=todate, employee=employee), as_dict=1)

	val = [log.log_type for log in logs]

	#For Check IN
	if not val or (val and val[-1] == "OUT"):
		return False
	#For Check OUT
	else:
		return True
