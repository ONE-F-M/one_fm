import frappe
from frappe import _
from frappe.utils import now_datetime, cstr, nowdate, cint
from scipy.spatial import distance as dist
from imutils import face_utils, paths
import numpy as np
import face_recognition
import datetime
from one_fm.api.mobile.roster import get_current_shift
import time
import dlib
import cv2, os
import json
from json import JSONEncoder

#loading facial landmark predictor
shape_predictor = frappe.utils.cstr(frappe.local.site)+"/private/files/shape_predictor_68_face_landmarks.dat"
print("[INFO] loading facial landmark predictor...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(shape_predictor)
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

class NumpyArrayEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return JSONEncoder.default(self, obj)

def eye_aspect_ratio(eye):
	# compute the euclidean distances between the two sets of
	# vertical eye landmarks (x, y)-coordinates
	A = dist.euclidean(eye[1], eye[5])
	B = dist.euclidean(eye[2], eye[4])
	# compute the euclidean distance between the horizontal
	# eye landmark (x, y)-coordinates
	C = dist.euclidean(eye[0], eye[3])
	# compute the eye aspect ratio
	ear = (A + B) / (2.0 * C)
	# return the eye aspect ratio
	return ear


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
		content = file.stream.read()
		filename = file.filename	
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





def verify_face(video_path=None):
	# video_path = frappe.utils.cstr(frappe.local.site)+"/private/files/kartik2.mp4"
	#shape_predictor = frappe.utils.cstr(frappe.local.site)+"/private/files/shape_predictor_68_face_landmarks.dat"
	# define two constants, one for the eye aspect ratio to indicate
	# blink and then a second constant for the number of consecutive
	# frames the eye must be below the threshold
	
	EYE_AR_frame = 0    #ear value of each frame
	EYE_AR_THRESH = 0    #threshold ear value
	EYE_AR_CONSEC_FRAMES = 1     #number of frames required for detecting a blink
	# initialize the frame counters and the total number of blinks
	COUNTER = 0
	TOTAL = 0

	# start the video stream thread
	print("[INFO] starting video stream thread...")
	#Calculating the threshold parameter
	vs = cv2.VideoCapture(video_path)
	fileStream = True
	framecount =0
	EYE_AR = 0        #total ear value for all frame
	IMAGE_PATH = ""
	sucess, frame = vs.read()
	while sucess:
		
		#BGR to Grayscale conversion
		try :
			gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		except :
			break

		# detect faces in the grayscale frame
		rects = detector(gray, 0)

		# loop over the face detections
		for rect in rects:
			# determine the facial landmarks for the face region, then
			# convert the facial landmark (x, y)-coordinates to a NumPy
			# array
			shape = predictor(gray, rect)
			shape = face_utils.shape_to_np(shape)

			# extract the left and right eye coordinates, then use the
			# coordinates to compute the eye aspect ratio for both eyes
			leftEye = shape[lStart:lEnd]
			rightEye = shape[rStart:rEnd]
			leftEAR = eye_aspect_ratio(leftEye)
			rightEAR = eye_aspect_ratio(rightEye)

			# average the eye aspect ratio together for both eyes
			EYE_AR_frame = (leftEAR + rightEAR) / 2.0       #ear calculation for each frame
			EYE_AR = EYE_AR_frame + EYE_AR                  #total ear value for all frame
			framecount = framecount + 1
			print("EYE AR VALUE = ", EYE_AR_frame)
			print("Calculating EYE AR VALUE")
		sucess, frame = vs.read()

	
	if EYE_AR == 0:
		return TOTAL, IMAGE_PATH

	EYE_AR = EYE_AR/framecount         #average calculation
	EYE_AR_THRESH = np.round(EYE_AR*0.9, 2)        # Threshold calculation
	print("EYE THRESHOLD CALCULATED")
	print("EYE THRESHOLD VALUE = ", EYE_AR_THRESH)
	
	# loop over frames from the video stream
	vs = cv2.VideoCapture(video_path)    #Starting to Detect Blinks
	fileStream = True
	succes, img = vs.read() 

	while succes:

		frame = cv2.resize(img, (0, 0), fx=0.85, fy=0.85)
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)     # BGR to Grayscale conversion

		# detect faces in the grayscale frame
		rects = detector(gray, 0)

		# loop over the face detections
		for rect in rects:
			# determine the facial landmarks for the face region, then
			# convert the facial landmark (x, y)-coordinates to a NumPy
			# array
			shape = predictor(gray, rect)
			shape = face_utils.shape_to_np(shape)

			# extract the left and right eye coordinates, then use the
			# coordinates to compute the eye aspect ratio for both eyes
			leftEye = shape[lStart:lEnd]
			rightEye = shape[rStart:rEnd]
			leftEAR = eye_aspect_ratio(leftEye)
			rightEAR = eye_aspect_ratio(rightEye)

			# average the eye aspect ratio together for both eyes
			ear = (leftEAR + rightEAR) / 2.0

			# check to see if the eye aspect ratio is below the blink
			# threshold, and if so, increment the blink frame counter
			ear = np.round(ear, 2)
			print(ear, EYE_AR_THRESH)
			if ear < EYE_AR_THRESH:
				COUNTER += 1
				print("[TOTAL COUNTER]", COUNTER)

			# otherwise, the eye aspect ratio is not below the blink
			# threshold
			else:
				# if the eyes were closed for a sufficient number of
				# then increment the total number of blinks
				if COUNTER >= EYE_AR_CONSEC_FRAMES:
					IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/private/files/"+frappe.session.user+".png"
					TOTAL += 1
					print("[TOTAL TOTAL]", TOTAL)
					cv2.imwrite(IMAGE_PATH,frame)
					return TOTAL, IMAGE_PATH

				# reset the eye frame counter
				COUNTER = 0
	
			print( "Blinks: {}".format(TOTAL), "EAR: {:.2f}".format(ear))
		succes, img = vs.read() 

	print("[TOTAL]", TOTAL)
	print("[COUNT]", COUNTER)
	return TOTAL, IMAGE_PATH


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

@frappe.whitelist()
def check_existing():
	employee = frappe.get_value("Employee", {"user_id": frappe.session.user})
	todate = nowdate()
	prev_date = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime ('%Y-%m-%d')
	if not employee:
		frappe.throw(_("Please link an employee to the logged in user to proceed further."))
	shift_assignment=get_current_shift(employee)

	#check if employee is been assigned with Shift. If not, take default date.
	if len(shift_assignment) != 0:
		shift_type = frappe.get_value("Shift Type", shift_assignment.shift_type, ["shift_type"])
		#if shift type is a night shift, It should check previous days check-in log.
		if shift_type == 'Night':
			logs = frappe.db.sql("""
			select name, log_type from `tabEmployee Checkin` where date(time)=date("{date}") and skip_auto_attendance=0 and employee="{employee}" 
			""".format(date=prev_date, employee=employee), as_dict=1)
		else:
			logs = frappe.db.sql("""
			select name, log_type from `tabEmployee Checkin` where date(time)=date("{date}") and skip_auto_attendance=0 and employee="{employee}" 
			""".format(date=todate, employee=employee), as_dict=1)
	else:
		logs = frappe.db.sql("""
			select name, log_type from `tabEmployee Checkin` where date(time)=date("{date}") and skip_auto_attendance=0 and employee="{employee}" 
			""".format(date=todate, employee=employee), as_dict=1)

	val = [log.log_type for log in logs]
	print(logs, val)
	if not val or (val and val[-1] == "OUT"):
		return False	
	else:
		return True