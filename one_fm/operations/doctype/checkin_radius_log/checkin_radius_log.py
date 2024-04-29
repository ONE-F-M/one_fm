# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, now
from frappe.model.document import Document

class CheckinRadiusLog(Document):
	def before_insert(self):
		_date = str(now()).split(' ')
		self.date = _date[0]
		self.time = _date[1]

	def validate(self):
		self.set_employee()
		map = '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[lonvalue,latvalue]}}]}'
		map = map.replace('latvalue', str(self.latitude))
		map = map.replace('lonvalue', str(self.longitude))
		self.map = map

	def set_employee(self):
		try:
			self.employee = frappe.db.get_value("Employee", {'name':self.employee}, ['name'])
		except Exception as e:
			frappe.log_error(str(e), 'Log checkin radius')

	@staticmethod
	def clear_old_logs(days=30):
		from frappe.query_builder import Interval
		from frappe.query_builder.functions import Now

		table = frappe.qb.DocType("Checkin Radius Log")
		frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))

def create_checkin_radius_log(data):
	"""
		Create checkin radious log from mobile api
	"""
	doc = frappe.get_doc(dict(
		doctype='Checkin Radius Log',
		latitude = data['latitude'],
		longitude = data['longitude'],
		employee = data['employee'],
		user_within_geofence_radius= data['user_within_geofence_radius'],
		geofence_radius= data['geofence_radius'],
		site=data['site_name'],
		user_latitude= data['user_latitude'],
		user_longitude= data['user_longitude'],
		user_distance_from_site_location= data['user_distance'],
		distance= data['user_distance'],
		difference= data['diff']
	))
	doc.insert(ignore_permissions=1)
