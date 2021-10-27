import frappe
from frappe.utils import get_datetime, add_to_date, cstr, flt
from one_fm.api.doc_events import haversine
from frappe import _

@frappe.whitelist()
def scan_checkpoint(qr_code, latitude, longitude):
	""" Creates a Checkpoint Assignment Scan document provided the user email, a QR code and the location coordinates

	Args:
		user: email ID of user scanning the QR code
		qr_code: alphanumeric string of the corresponding QR code obtained upon scanning.
		latitude, longitude: live coordinates of the user fetched during scanning.
	"""

	user = frappe.session.user
	# get employee details from user email
	employee, employee_name = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_name"]) 

	cur_datetime = get_datetime()
	

	newscan = frappe.new_doc('Checkpoint Assignment Scan')
	newscan.scan_datetime = cur_datetime#.strftime("%d-%m-%Y %H:%M:%S")
	newscan.scanned_by = employee
	newscan.scan_location = latitude + "," + longitude

	if frappe.db.exists("Checkpoints Assignment", { 'start_date_time': ('<=', cur_datetime), 'end_date_time': ('>=', cur_datetime), 'checkpoint_code': qr_code}):
		# If the checkpoint scan exists in the checkpoint assignment, fetch and check assignment criteria - distance & same assignment
		checkpoint_assignment = frappe.get_doc("Checkpoints Assignment", {
			'start_date_time': ('<=', cur_datetime), 
			'end_date_time': ('>=', cur_datetime), 
			'checkpoint_code': qr_code
		})

		site_location = frappe.get_value("Operations Site", checkpoint_assignment.site, "site_location")
		site_lat, site_lng, radius = frappe.get_value("Location", site_location, ["latitude","longitude", "geofence_radius"] )
		
		# compute distance between site and user
		distance =  flt(haversine(site_lat, site_lng, latitude, longitude), precision=2)

		# check distance of user from checkpoint site
		if distance <= radius:
			newscan.within_distance = "YES"
		else:
			newscan.within_distance = "NO"
			newscan.distance_off = distance - radius

		newscan.has_assignment = "YES"
		
		newscan.route_name = checkpoint_assignment.route_name
		newscan.checkpoint_name = checkpoint_assignment.checkpoint_name
		newscan.project = checkpoint_assignment.project
		newscan.site = checkpoint_assignment.site
		
		# Check same assignment match for post/employee
		if checkpoint_assignment.employee and checkpoint_assignment.employee == employee:
			newscan.same_assignment = "YES"
		
		elif checkpoint_assignment.post and checkpoint_assignment.post == employee:
			# TODO: Integrate once post allocation is Done
			print("TO BE DONE!!!")
		
		else:
			newscan.same_assignment = "NO"
			newscan.employee = checkpoint_assignment.employee_name

	elif frappe.db.exists("Checkpoints", {"checkpoint_code": qr_code}, ["name", "project_name", "site_name"]):
		# Set assignment to NO if no assignment is found but a checkpoint exists for the provided qr code
		checkpoint_name, project, site = frappe.get_value("Checkpoints", {"checkpoint_code": qr_code}, ["name", "project_name", "site_name"])
		newscan.checkpoint_name = checkpoint_name
		newscan.project = project
		newscan.site = site
		newscan.has_assignment = "NO"
	
	else:
		# If no checkpoint is found for the qr code provided
		frappe.throw(_("Checkpoint not found in the system. Please check again."))
	
	newscan.save()
	frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def scan_checkpoint_mobile(user, qr_code, latitude, longitude):
	""" Creates a Checkpoint Assignment Scan document provided the user email, a QR code and the location coordinates.

	Args:
		user: email ID of user scanning the QR code
		qr_code: alphanumeric string of the corresponding QR code obtained upon scanning.
		latitude, longitude: live coordinates of the user fetched during scanning.

	Returns:
		Success, 201 : Successful creation of checkpoint scan document
		Bad request, 400: invalid params
		server error, 500: Failed to create checkpoint scan document	
	"""
	try:
		# get employee details from user email
		employee = frappe.get_value("Employee", {"user_id": user}, ["name"]) 

		if not employee:
			return response('No employee found for user {user}'.format(user=user), 400)

		cur_datetime = get_datetime()
	
		newscan = frappe.new_doc('Checkpoint Assignment Scan')
		newscan.scan_datetime = cur_datetime#.strftime("%d-%m-%Y %H:%M:%S")
		newscan.scanned_by = employee
		newscan.scan_location = latitude + "," + longitude

		if frappe.db.exists("Checkpoints Assignment", { 'start_date_time': ('<=', cur_datetime), 'end_date_time': ('>=', cur_datetime), 'checkpoint_code': qr_code}):
			# If the checkpoint scan exists in the checkpoint assignment, fetch and check assignment criteria - distance & same assignment
			checkpoint_assignment = frappe.get_doc("Checkpoints Assignment", {
				'start_date_time': ('<=', cur_datetime), 
				'end_date_time': ('>=', cur_datetime), 
				'checkpoint_code': qr_code
			})

			site_location = frappe.get_value("Operations Site", checkpoint_assignment.site, "site_location")

			if not site_location:
				return response('No site found in the checkpoint assignment.', 400)

			site_lat, site_lng, radius = frappe.get_value("Location", site_location, ["latitude","longitude", "geofence_radius"] )

			if not site_lat or not site_lng or not radius:
				return response('Coordinates not found for site {site}.'.format(site=site_location), 400)
			
			# compute distance between site and user
			distance =  flt(haversine(site_lat, site_lng, latitude, longitude), precision=2)

			# check distance of user from checkpoint site
			if distance <= radius:
				newscan.within_distance = "YES"
			else:
				newscan.within_distance = "NO"
				newscan.distance_off = distance - radius

			newscan.has_assignment = "YES"
			
			newscan.route_name = checkpoint_assignment.route_name
			newscan.checkpoint_name = checkpoint_assignment.checkpoint_name
			newscan.project = checkpoint_assignment.project
			newscan.site = checkpoint_assignment.site
			
			# Check same assignment match for post/employee
			if checkpoint_assignment.employee and checkpoint_assignment.employee == employee:
				newscan.same_assignment = "YES"
			
			elif checkpoint_assignment.post and checkpoint_assignment.post == employee:
				# TODO: Integrate once post allocation is Done
				print("TO BE DONE!!!")
			
			else:
				newscan.same_assignment = "NO"
				newscan.employee = checkpoint_assignment.employee_name

		elif frappe.db.exists("Checkpoints", {"checkpoint_code": qr_code}, ["name", "project_name", "site_name"]):
			# Set assignment to NO if no assignment is found but a checkpoint exists for the provided qr code
			
			# Get checkpoint details
			checkpoint_name, project, site = frappe.get_value("Checkpoints", {"checkpoint_code": qr_code}, ["name", "project_name", "site_name"])
			newscan.checkpoint_name = checkpoint_name
			newscan.project = project
			newscan.site = site
			newscan.has_assignment = "NO"
		
		else:
			# If no checkpoint is found for the qr code provided
			return response('Checkpoint not found in the system. Please check again.', 400)
		
		newscan.save(ignore_permissions=True)
		frappe.db.commit()

		return response("Checkpoint Assignment Scan successfully created!", 201)
	
	except Exception as e:
		return response(e, 500)


def response(message, status_code):
	frappe.local.response["message"] = message
	frappe.local.response["http_status_code"] = status_code
	return