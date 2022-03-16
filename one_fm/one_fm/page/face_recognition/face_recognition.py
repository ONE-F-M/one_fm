import base64
import grpc
from one_fm.proto import facial_recognition_pb2_grpc, facial_recognition_pb2
import frappe
from frappe import _
from frappe.utils import now_datetime, cstr, nowdate, cint
from scipy.spatial import distance as dist
from imutils import face_utils, paths
import numpy as np
import face_recognition
import datetime
import time
import cv2, os
import json
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
		setup_directories()
		files = frappe.request.files
		file = files['file']
		content = file.stream.read()
		filename = file.filename
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
def verify():
	try:

		setup_directories()
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
			username = user_name,
			user_encoded_video = video_content,
			user_encoding = user_encoding_json
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


def create_dataset(video):
	OUTPUT_DIRECTORY = frappe.utils.cstr(frappe.local.site)+"/private/files/dataset/"+frappe.session.user+"/"
	count = 0

	cap = cv2.VideoCapture(video)
	success, img = cap.read()
	count = 0
	while success:
		#Resizing the image
		img = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
		#Limiting the number of images for training. %5 gives 10 images %5.8 -> 8 images %6.7 ->7 images
		if count%5 == 0 :
			cv2.imwrite(OUTPUT_DIRECTORY + "{0}.jpg".format(count+1), img)
		count = count + 1
		success, img = cap.read()

	create_encodings(OUTPUT_DIRECTORY)
	doc = frappe.get_doc("Employee", {"user_id": frappe.session.user})
	print(doc.as_dict())
	doc.enrolled = 1
	doc.save(ignore_permissions=True)
	update_onboarding_employee(doc)
	frappe.db.commit()

def update_onboarding_employee(employee):
    onboard_employee_exist = frappe.db.exists('Onboard Employee', {'employee': employee.name})
    if onboard_employee_exist:
        onboard_employee = frappe.get_doc('Onboard Employee', onboard_employee_exist.name)
        onboard_employee.enrolled = True
        onboard_employee.enrolled_on = now_datetime()
        onboard_employee.save(ignore_permissions=True)
        frappe.db.commit()

def create_encodings(directory, detection_method="hog"):# detection_method can be "hog" or "cnn". cnn is more cpu and memory intensive.
	"""
		directory : directory path containing dataset
	"""
	print(directory)
	OUTPUT_ENCODING_PATH_PREFIX = frappe.utils.cstr(frappe.local.site)+"/private/files/facial_recognition/"
	user_id = frappe.session.user
	# grab the paths to the input images in our dataset
	imagePaths = list(paths.list_images(directory))
	print(imagePaths)
	#encodings file output path
	encoding_path = OUTPUT_ENCODING_PATH_PREFIX + user_id +".json"
	# initialize the list of known encodings and known names
	knownEncodings = []
	# knownNames = []

	for (i, imagePath) in enumerate(imagePaths):
		# extract the person name from the image path i.e User Id
		print("[INFO] processing image {}/{}".format(i + 1, len(imagePaths)))
		name = imagePath.split(os.path.sep)[-2]

		# load the input image and convert it from BGR (OpenCV ordering)
		# to dlib ordering (RGB)
		image = cv2.imread(imagePath)
		#BGR to RGB conversion
		rgb =  image[:, :, ::-1]

		# detect the (x, y)-coordinates of the bounding boxes
		# corresponding to each face in the input image
		boxes = face_recognition.face_locations(rgb, model=detection_method)

		# compute the facial embedding for the face
		encodings = face_recognition.face_encodings(rgb, boxes)

		# loop over the encodings
		for encoding in encodings:
			# add each encoding + name to our set of known names and
			# encodings
			knownEncodings.append(encoding)

	# dump the facial encodings + names to disk
	data = {"encodings": knownEncodings}
	print(data)
	if len(knownEncodings) == 0:
		frappe.throw(_("No face found in the video. Please make sure you position your face correctly in front of the camera."))
	data = json.dumps(data, cls=NumpyArrayEncoder)
	with open(encoding_path,"w") as f:
		f.write(data)
		f.close()


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

def recognize_face(image):
	try:
		ENCODINGS_PATH = frappe.utils.cstr(
			frappe.local.site)+"/private/files/facial_recognition/"+frappe.session.user+".json"
		# values should be "hog" or "cnn" . cnn is CPU and memory intensive.
		DETECTION_METHOD = "hog"

		# load the known faces and embeddings
		face_data = json.loads(open(ENCODINGS_PATH, "rb").read())

		# load the input image and convert it from BGR to RGB
		image = cv2.imread(image)
		rgb =  image[:, :, ::-1]

		# detect the (x, y)-coordinates of the bounding boxes corresponding
		# to each face in the input image, then compute the facial embeddings
		# for each face
		boxes = face_recognition.face_locations(rgb,
												model=DETECTION_METHOD)
		encodings = face_recognition.face_encodings(rgb, boxes)

		if not encodings:
			return False
		return match_encodings(encodings, face_data)

	except Exception as e:
		print(frappe.get_traceback())


def match_encodings(encodings, face_data):
	try:
		# loop over the facial embeddings
		for encoding in encodings:
			# attempt to match each face in the input image to our known
			# encodings
			matches = face_recognition.compare_faces(
				face_data["encodings"], encoding)
			# check to see if we have found a match
			if True in matches:
				# find the indexes of all matched faces
				matchedIdxs = [i for (i, b) in enumerate(matches) if b]
				print(matchedIdxs, matches)
				return True if ((len(matchedIdxs) / len(matches)) * 100 > 80) else False
			else:
				return False
		else:
			return False
	except Exception as identifier:
		print(frappe.get_traceback())