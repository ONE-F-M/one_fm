import frappe, ast, base64, time
from frappe import _
from one_fm.one_fm.page.face_recognition.face_recognition import setup_directories, create_dataset, verify_face, recognize_face, check_in

@frappe.whitelist()
def enroll(video):
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
		raise exc

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
				live_end = time.time()
				print("Liveness Detection Time =", live_end-live_start)
				print("Liveness Detection SUccess")
				recog_start=time.time()
				if recognize_face(image):   #calling recognition function 
					recog_end = time.time()
					print("Face Recognition Time = ", recog_end-recog_start)
					print("Face Recognition Success")
					return check_in(log_type, skip_attendance, latitude, longitude)
				else:
					recog_end = time.time()
					print("Face Recognition Time = ", recog_end-recog_start)
					print("Face Recognition Failed")
					frappe.throw(_('Face Recognition Failed. Please try again.'))	
			else:
				live_end = time.time()
				print("Liveness Detection Time = ", live_end - live_start)
				print("Liveness Detection Failed")
				frappe.throw(_('Liveness Detection Failed. Please try again.'))
	except Exception as exc:
		frappe.log_error(frappe.get_traceback())
		raise exc