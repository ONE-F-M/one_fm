# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import cv2
import base64
from frappe import _
import pickle, face_recognition
from frappe.utils import cint, getdate, add_to_date, get_link_to_form, now_datetime

class Penalty(Document):
	def after_insert(self):
		self.notify_employee()

	def notify_employee(self):
		link = get_link_to_form(self.doctype, self.name)
		subject = _("Penalty Issued by {issuer_name}.".format(issuer_name=self.issuer_name))
		message = _("""
			You have been issued a penalty.<br>
			Please take necessary action within 48 hours.<br>
			<b>Note: Penalty will be automatically rejected after 48 hours and commence a legal investigation into the matter.</b><br>
			Link: {link}""".format(link=link))
		frappe.sendmail([self.recipient_user], subject=subject, message=message, reference_doctype=self.doctype, reference_name=self.name)

	def on_update(self):
		doc_before_update = self.get_doc_before_save()
		print(self.as_dict())
		if (doc_before_update and doc_before_update.workflow_state != "Penalty Accepted") and self.workflow_state == "Penalty Accepted":
			self.update_penalty_deductions()

		if (doc_before_update and doc_before_update.workflow_state != "Penalty Rejected") and self.workflow_state == "Penalty Rejected":
			self.create_legal_investigation()
	def validate(self):
		self.validate_self_issuance()
	
	def validate_self_issuance(self):
		if self.recipient_employee==self.issuer_employee:
			frappe.throw(_("Penalty recepient and issuer cannot be the same Employee.")) 
	
	def update_penalty_deductions(self):
		pass
		# penalty = frappe.get_doc("Penalty", self.name)
		# penalty.append("penalty_details", {
		# 	"deduction": 1
		# })
		# penalty.save(ignore_permissions=True)
		# frappe.db.commit()

	def create_legal_investigation(self):
		if frappe.db.exists("Legal Investigation",{"reference_doctype": self.doctype, "reference_name": self.name}):
			frappe.throw(_("Legal Investigaton already created."))
		legal_inv = frappe.new_doc("Legal Investigation")
		legal_inv.penalty_code = self.name
		legal_inv.investigation_lead = None
		legal_inv.append("legal_investigation_employees", {
			"employee_id": self.issuer_employee,
			"employee_name": self.issuer_name,
			"designation": self.issuer_designation,
			"party": "Plaintiff"
		})	
		legal_inv.append("legal_investigation_employees", {
			"employee_id": self.recipient_employee,
			"employee_name": self.recipient_name,
			"designation": self.recipient_designation,
			"party": "Defendant"
		})	
		legal_inv.start_date = add_to_date(getdate(), days=2)
		legal_inv.save(ignore_permissions=True)

		self.db_set("legal_investigation_code", legal_inv.name)		
		frappe.db.commit()

@frappe.whitelist()
def accept_penalty(file, retries, docname):
	print(retries)
	retries_left = cint(retries) - 1
	OUTPUT_IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/private/files/"+frappe.session.user+".png"
	penalty = frappe.get_doc("Penalty", docname)
	if recognize_face(file, OUTPUT_IMAGE_PATH, retries_left) or retries_left == 0:
		if retries_left == 0:
			penalty.verified = 0
			send_email_to_legal(penalty)
		else:
			penalty.verified = 1		
		penalty.workflow_state = "Penalty Accepted"
		penalty.save(ignore_permissions=True)
		
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_url": "/private/files/"+frappe.session.user+".png",
			"file_name": frappe.session.user+".png",
			"attached_to_doctype": "Penalty",
			"attached_to_name": docname,
			"folder": "Home/Attachments",
			"is_private": 1
		})
		print(file_doc.as_dict())
		file_doc.flags.ignore_permissions = True
		file_doc.insert()

		frappe.db.commit()

		return {
			'message': 'success'
		}
	else:
		penalty.db_set("retries", retries_left)
		return {
			'message': 'error',
			'retries': retries_left
		}

@frappe.whitelist()
def reject_penalty(rejection_reason, docname):
	penalty = frappe.get_doc("Penalty", docname)
	penalty.reason_for_rejection = rejection_reason
	penalty.workflow_state = "Penalty Rejected"
	penalty.save(ignore_permissions=True)
	frappe.db.commit()

def send_email_to_legal(penalty, message=None):
	legal = frappe.get_value("Legal Settings", "Legal Settings", "legal_department_email")
	link = get_link_to_form(penalty.doctype, penalty.name)
	subject = _("Review Penalty: {penalty}".format(penalty=penalty.name))
	message = _("Face verification did not match while accepting the penalty.<br> Please review and take necessary action.<br> Link: {link}".format(link=link)) if not message else message
	frappe.sendmail([legal], subject=subject, message=message, reference_doctype=penalty.doctype, reference_name=penalty.name)



def recognize_face(base64image, OUTPUT_IMAGE_PATH, retries_left):
	try:
		ENCODINGS_PATH = frappe.utils.cstr(
			frappe.local.site)+"/private/files/facial_recognition/"+frappe.session.user+".pickle"
		# values should be "hog" or "cnn" . cnn is CPU and memory intensive.
		DETECTION_METHOD = "hog"

		image = upload_image(base64image, OUTPUT_IMAGE_PATH)
		# load the known faces and embeddings
		face_data = pickle.loads(open(ENCODINGS_PATH, "rb").read())

		# load the input image and convert it from BGR to RGB
		image = cv2.imread(image)
		rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

		# detect the (x, y)-coordinates of the bounding boxes corresponding
		# to each face in the input image, then compute the facial embeddings
		# for each face
		boxes = face_recognition.face_locations(rgb,
												model=DETECTION_METHOD)
		encodings = face_recognition.face_encodings(rgb, boxes)
		print(encodings)
		if not encodings:
			frappe.throw(_("No face detected. Please make sure you are in the camera frame."))
		return match_encodings(encodings, face_data)

	except Exception as e:
		print(frappe.get_traceback())


def upload_image(base64image, OUTPUT_IMAGE_PATH):
	try:
		with open(OUTPUT_IMAGE_PATH, "wb") as fh:
			fh.write(base64.standard_b64decode(base64image.encode()))
			return (OUTPUT_IMAGE_PATH)
	except Exception as exc:
		frappe.log_error(frappe.get_traceback())
		raise exc

def match_encodings(encodings, face_data):
	try:
		# loop over the facial embeddings
		for encoding in encodings:
			# attempt to match each face in the input image to our known
			# encodings
			matches = face_recognition.compare_faces(
				face_data["encodings"], encoding)
			print(matches)
			# check to see if we have found a match
			if True in matches:
				# find the indexes of all matched faces
				matchedIdxs = [i for (i, b) in enumerate(matches) if b]
				print(matchedIdxs)
				return True if ((len(matchedIdxs) / len(matches)) * 100 > 80) else False
			else:
				return False
		else:
			return False
	except Exception as e:
		print(frappe.get_traceback())

@frappe.whitelist()
def create_legal_inv(doctype, docname):
	doc = frappe.get_doc(doctype, docname)
	doc.create_legal_investigation()

def notify_employee_autoreject(doc):
	link = get_link_to_form(doc.doctype, doc.name)
	subject = _("Penalty Issued by {issuer_name}.".format(issuer_name=doc.issuer_name))
	message = _("""
		Automatic Rejection.<br>
		Penalty has been rejected automatically after 48 hours of no action.<br>
		<b>Note: A legal investigation will now commence looking into the matter.</b><br>
		Link: {link}""".format(link=link))
	frappe.sendmail([doc.recipient_user], subject=subject, message=message, reference_doctype=doc.doctype, reference_name=doc.name)

def automatic_reject():
	time = add_to_date(now_datetime(), hours=-48, as_datetime=True).strftime("%Y-%m-%d %H:%M")
	time_range = add_to_date(now_datetime(), hours=-47, as_datetime=True).strftime("%Y-%m-%d %H:%M")
	docs = frappe.get_all("Penalty", {"penalty_issuance_time": ["between", [time, time_range]], "workflow_state": "Penalty Issued"})
    #"2021-05-11 11:07:09"
	for doc in docs:
		penalty = frappe.get_doc("Penalty", doc.name)
		penalty.verified = 0
		penalty.reason_for_rejection = "Penalty was rejected after 48 hours automatically."
		penalty.workflow_state = "Penalty Rejected"
		penalty.save(ignore_permissions=True)
		notify_employee_autoreject(penalty)
		send_email_to_legal(penalty, _("Penalty was rejected after 48 hours automatically. Please review."))
	
	frappe.db.commit()
