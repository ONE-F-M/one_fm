import frappe, ast, base64, time
from frappe import _
from one_fm.one_fm.page.face_recognition.face_recognition import setup_directories, create_dataset, check_in
from one_fm.api.mobile.roster import get_current_shift
from one_fm.proto import facial_recognition_pb2, facial_recognition_pb2_grpc
import json
import grpc


@frappe.whitelist()
def enroll(video):
	"""
	Params:
	video: base64 encoded data
	"""
	try:
		setup_directories()
		content = base64.b64decode(video)
		filename = frappe.session.user+".mp4"	
		OUTPUT_VIDEO_PATH = frappe.utils.cstr(frappe.local.site)+"/private/files/user/"+filename
		with open(OUTPUT_VIDEO_PATH, "wb") as fh:
				fh.write(content)
				start_enroll = time.time()
				create_dataset(OUTPUT_VIDEO_PATH)
				end_enroll = time.time()
				print("Ënroll Time Taken = ", end_enroll-start_enroll)
				print("Enrolling Success")
		return _("Successfully Enrolled!")
	except Exception as exc:
		print(frappe.get_traceback())
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
		setup_directories()
		# Get user encoding file
		encoding_file_path = frappe.utils.cstr(frappe.local.site)+"/private/files/facial_recognition/"+frappe.session.user+".json"
		encoding_content_json = json.loads(open(encoding_file_path, "rb").read()) # dict
		encoding_content_str = json.dumps(encoding_content_json) # str
		encoding_content_bytes = encoding_content_str.encode('ascii')
		encoding_content_base64_bytes = base64.b64encode(encoding_content_bytes)
		user_encoding_json = encoding_content_base64_bytes.decode('ascii')

		# setup channel
		face_recognition_service_url = frappe.local.conf.face_recognition_service_url
		channel = grpc.secure_channel(face_recognition_service_url, grpc.ssl_channel_credentials())
		# setup stub
		stub = facial_recognition_pb2_grpc.FaceRecognitionServiceStub(channel)

		# request body
		req = facial_recognition_pb2.Request(
			username = frappe.session.user,
			user_encoded_video = video,
			user_encoding = user_encoding_json
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
		if shift:
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