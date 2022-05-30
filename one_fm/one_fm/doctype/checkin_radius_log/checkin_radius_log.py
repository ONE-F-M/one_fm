# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CheckinRadiusLog(Document):

	def validate(self):
		map = '{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[lonvalue,latvalue]}}]}'
		map = map.replace('latvalue', str(self.latitude))
		map = map.replace('lonvalue', str(self.longitude))
		self.map = map


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
		geofence_radius= data['geofence_radius']
	))
	don.insert(ignore_permissions=1)
