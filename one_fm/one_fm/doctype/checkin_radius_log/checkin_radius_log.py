# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CheckinRadiusLog(Document):

	def validate(self):
		self.set_employee()
		map = '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[lonvalue,latvalue]}}]}'
		map = map.replace('latvalue', str(self.latitude))
		map = map.replace('lonvalue', str(self.longitude))
		self.map = map

	def set_employee(self):
		try:
			self.employee = frappe.db.get_value("Employee", {'employee_id':self.employee_id}, ['name'])
		except Exception as e:
			frappe.log_error(str(e), 'Log checkin raius')


def create_checkin_radius_log(data):
	"""
		Create checkin radious log from mobile api
	"""
	doc = frappe.get_doc(dict(
		doctype='Checkin Radius Log',
		latitude = data['latitude'],
		longitude = data['longitude'],
		employee_id = data['employee'],
		user_within_geofence_radius= data['user_within_geofence_radius'],
		geofence_radius= data['geofence_radius'],
		site=data['site_name'],
		user_latitude= data['user_latitude'],
		user_longitude= data['user_longitude'],
		user_geofence_radius= data['user_distance'],
		distance= data['user_distance'],
		difference= data['diff']
	))
	doc.insert(ignore_permissions=1)
