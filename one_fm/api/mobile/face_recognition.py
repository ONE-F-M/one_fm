import frappe, ast, base64, time
from frappe import _
from one_fm.one_fm.page.face_recognition.face_recognition import check_in, update_onboarding_employee
from one_fm.api.mobile.roster import get_current_shift
from one_fm.proto import enroll_pb2, enroll_pb2_grpc, facial_recognition_pb2, facial_recognition_pb2_grpc
import json
import grpc
from one_fm.one_fm.page.face_recognition.face_recognition import user_within_site_geofence


@frappe.whitelist()
def enroll(video):
	"""
	Params:
	video: base64 encoded data
	"""
	try:
		# Setup channel
		face_recognition_enroll_service_url = frappe.local.conf.face_recognition_enroll_service_url
		channel = grpc.secure_channel(face_recognition_enroll_service_url, grpc.ssl_channel_credentials())
		# setup stub
		stub = enroll_pb2_grpc.FaceRecognitionEnrollmentServiceStub(channel)
		# request body
		req = enroll_pb2.EnrollRequest(
			username = frappe.session.user,
			user_encoded_video = video,
		)

		res = stub.FaceRecognitionEnroll(req)

		if res.enrollment == "FAILED":
			return (res.message, 400, None, res.data)
			
		doc = frappe.get_doc("Employee", {"user_id": frappe.session.user})
		doc.enrolled = 1
		doc.save(ignore_permissions=True)
		update_onboarding_employee(doc)
		frappe.db.commit()
		return _("Successfully Enrolled!")
	
	except Exception as exc:
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)


@frappe.whitelist()
def verify(video, log_type, skip_attendance, latitude, longitude):
	""" Params:
		video: base64 encoded data
		log_type: IN/OUT
		skip_attendance: 0/1
		latitude: latitude of current location
		longitude: longitude of current location
	"""
	try:

		employee = frappe.db.get_value("Employee", {'user_id': frappe.session.user}, ["name"])

		# if not user_within_site_geofence(employee,log_type, latitude, longitude):
		# 	return ("Please check {log_type} at your site location.".format(log_type=log_type))

		# setup channel
		face_recognition_service_url = frappe.local.conf.face_recognition_service_url
		channel = grpc.secure_channel(face_recognition_service_url, grpc.ssl_channel_credentials())
		# setup stub
		stub = facial_recognition_pb2_grpc.FaceRecognitionServiceStub(channel)

		# request body
		req = facial_recognition_pb2.FaceRecognitionRequest(
			username = frappe.session.user,
			media_type = "video",
			media_content = video
		)
		# Call service stub and get response
		res = stub.FaceRecognition(req)

		if res.verification == "FAILED":
			msg = res.message
			data = res.data

			return ("{msg}. {data}".format(msg=msg, data=data))

		return check_in(log_type, skip_attendance, latitude, longitude)

	except Exception as exc:
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)


@frappe.whitelist()
def get_site_location(employee):
	try:
		shift = get_current_shift(employee)
		if shift and shift.shift:
			site = frappe.get_value("Operations Shift", shift.shift, "site")
			location= frappe.db.sql("""
			SELECT loc.latitude, loc.longitude, loc.geofence_radius
			FROM `tabLocation` as loc
			WHERE
				loc.name in(SELECT site_location FROM `tabOperations Site` where name="{site}")
			""".format(site=site), as_dict=1)
			if location:
				site_n_location=location[0]
				site_n_location['site_name']=site
				return {"message": "Success","data_obj": site_n_location,"status_code" : 200}
			else:
				return {"message": "Site Location is not Set.","data_obj": {},"status_code" : 500}
		else:
			return {"message": "You are not currently assign with a shift.","data_obj": {},"status_code" : 500}	
	except Exception as e:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(e)		