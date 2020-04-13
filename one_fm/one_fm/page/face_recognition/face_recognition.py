import frappe
from scipy.spatial import distance as dist
from imutils.video import FileVideoStream
from imutils.video import VideoStream
import matplotlib.pyplot as plt 
from imutils import face_utils
import numpy as np
import argparse
import imutils
import time
import dlib
import cv2, base64



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

@frappe.whitelist()
def verify_face(video_path=None):
	video_path = frappe.utils.cstr(frappe.local.site)+"/private/files/kartik2.mp4"
	shape_predictor = frappe.utils.cstr(frappe.local.site)+"/private/files/shape_predictor_68_face_landmarks.dat"
	# define two constants, one for the eye aspect ratio to indicate
	# blink and then a second constant for the number of consecutive
	# frames the eye must be below the threshold
	EYE_AR_THRESH = 0.30
	EYE_AR_CONSEC_FRAMES = 2
	# initialize the frame counters and the total number of blinks
	COUNTER = 0
	TOTAL = 0

	# initialize dlib's face detector (HOG-based) and then create
	# the facial landmark predictor
	print("[INFO] loading facial landmark predictor...")
	detector = dlib.get_frontal_face_detector()
	predictor = dlib.shape_predictor(shape_predictor)

	# grab the indexes of the facial landmarks for the left and
	# right eye, respectively
	(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
	(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

	# start the video stream thread
	print("[INFO] starting video stream thread...")
	vs = FileVideoStream(video_path).start()
	fileStream = True
	vs = VideoStream(src=0).start()
	# vs = VideoStream(usePiCamera=True).start()
	fileStream = False
	time.sleep(1.0)
	print(vs.read())	
	# loop over frames from the video stream
	while True:
		# if this is a file video stream, then we need to check if
		# there any more frames left in the buffer to process
		if fileStream and not vs.more():
			break
		
		if not isinstance(vs.read(), np.ndarray):
			break
		# grab the frame from the threaded video file stream, resize
		# it, and convert it to grayscale
		# channels)
		frame = vs.read()
		frame = imutils.resize(frame, width=450)
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

		# detect faces in the grayscale frame
		rects = detector(gray, 0)
		# print("RECTS",len(rects))

		# loop over the face detections
		for rect in rects:
			# determine the facial landmarks for the face region, then
			# convert the facial landmark (x, y)-coordinates to a NumPy
			# array
			# print("[RECT]", rect)
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

			# compute the convex hull for the left and right eye, then
			# visualize each of the eyes
			leftEyeHull = cv2.convexHull(leftEye)
			rightEyeHull = cv2.convexHull(rightEye)
			cv2.drawContours(frame, [leftEyeHull], -1, (0, 255, 0), 1)
			cv2.drawContours(frame, [rightEyeHull], -1, (0, 255, 0), 1)

			# print(TOTAL)
			# print(COUNTER)

			# check to see if the eye aspect ratio is below the blink
			# threshold, and if so, increment the blink frame counter
			if ear < EYE_AR_THRESH:
				COUNTER += 1

			# otherwise, the eye aspect ratio is not below the blink
			# threshold
			else:
				# if the eyes were closed for a sufficient number of
				# then increment the total number of blinks
				if COUNTER >= EYE_AR_CONSEC_FRAMES:
					TOTAL += 1

				# reset the eye frame counter
				COUNTER = 0
			# print(TOTAL)
			print( "Blinks: {}".format(TOTAL), "EAR: {:.2f}".format(ear))
			# draw the total number of blinks on the frame along with
			# the computed eye aspect ratio for the frame

			# cv2.putText(frame, "Blinks: {}".format(TOTAL), (10, 30),
			# 	cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
			# cv2.putText(frame, "EAR: {:.2f}".format(ear), (300, 30),
			# 	cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
	
		# show the frame
		# cv2.imshow("Frame", frame)
		# img = cv2.rectangle(frame, (5, 5), (200, 200), (255, 200, 0), 2) 
		# plt.imshow(img, cmap='gray') 
		# plt.show()

		# key = 0xFF
		# key = cv2.waitKey(1) & 0xFF
		# cv2.imshow('Faces', frame) 

		# if the `q` key was pressed, break from the loop
		# if key == ord("q"):
		# 	break
	print("[TOTAL]", TOTAL)
	print("[COUNT]", COUNTER)
	
	# do a bit of cleanup
	# cv2.destroyAllWindows()
	vs.stop()

@frappe.whitelist()
def upload_image(file):
	print(file)
	# OUTPUT_IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/private/files/user/"+frappe.session.user+".png"
	# try:
	# 	with open(OUTPUT_IMAGE_PATH, "wb") as fh:
	# 			fh.write(base64.standard_b64decode(base64image.encode()))
	# 			return (OUTPUT_IMAGE_PATH)
	# except Exception as exc:
	# 	frappe.log_error(frappe.get_traceback())
	# 	raise exc