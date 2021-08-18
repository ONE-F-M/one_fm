import frappe, ast, base64, time
from frappe import _
from one_fm.one_fm.page.face_recognition.face_recognition import setup_directories, create_dataset, verify_face, recognize_face, check_in
from one_fm.api.mobile.roster import get_current_shift


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
		content = base64.b64decode(video)
		filename = frappe.session.user+".mp4"	
		OUTPUT_IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/private/files/user/"+filename

		with open(OUTPUT_IMAGE_PATH, "wb") as fh:
			fh.write(content)
			live_start = time.time()
			blinks, image = verify_face(OUTPUT_IMAGE_PATH)     #calling verification function for face
			if blinks > 0:
				if recognize_face(image):   #calling recognition function 
					return check_in(log_type, skip_attendance, latitude, longitude)
				else:
					return ('Face Recognition Failed. Please try again.')
			else:
				return ('Liveness Detection Failed. Please try again.')
	except Exception as exc:
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(exc)


@frappe.whitelist()
def get_site_location(employee):
	try:
		shift = get_current_shift(employee)
		if shift and len(shift) != 0:
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
				return site_n_location
			else:
				return ('Site Location is not Set.')
		else:
			return {'message': _('You Are Not currently Assigned with a Shift.')}			
	except Exception as e:
		print(frappe.get_traceback())
		frappe.log_error(frappe.get_traceback())
		return frappe.utils.response.report_error(e)