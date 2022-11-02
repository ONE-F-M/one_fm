# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FaceRecognitionLog(Document):
	pass


def create_face_recognition_log(data):
	"""
		Create checkin radious log from mobile api
	"""
	doc = frappe.get_doc(dict(
		doctype='Face Recognition Log',
		employee = data['employee'],
		verification= data['verification'],
		log_type= data['log_type'],
		message= data['message'],
		data= data['data'],
		source=data['source'],
	))
	doc.insert(ignore_permissions=1)
