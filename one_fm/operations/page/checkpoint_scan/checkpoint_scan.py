import frappe
from frappe.utils import get_datetime, add_to_date, cstr, flt
from one_fm.api.doc_events import haversine

@frappe.whitelist()
def scan_checkpoint(qr_code, latitude, longitude):
	user = frappe.session.user
	employee, employee_name = frappe.get_value("Employee", {"user_id": user}, ["name", "employee_name"]) #Will be None if logged in as Administrator  
	# location = latitude + " " + longitude
	cur_datetime = get_datetime()

	print(employee, cur_datetime)
	# Check if the checkpoint scan is in the checkpoint assignment doctype

	
	newscan = frappe.new_doc('Checkpoint Assignment Scan')
	newscan.scan_datetime = cur_datetime#.strftime("%d-%m-%Y %H:%M:%S")
	newscan.scanned_by = employee
	newscan.scan_location = latitude + "," + longitude


	if frappe.db.exists("Checkpoints Assignment", 
		{ 'start_date_time': ('<=', cur_datetime), 'end_date_time': ('>=', cur_datetime), 'checkpoint_code': qr_code}):
		checkpoint_assignment = frappe.get_doc("Checkpoints Assignment", {
			'start_date_time': ('<=', cur_datetime), 
			'end_date_time': ('>=', cur_datetime), 
			'checkpoint_code': qr_code
		})
		print(checkpoint_assignment.as_dict())
		site_location = frappe.get_value("Operations Site", checkpoint_assignment.site, "site_location")
		site_lat, site_lng, radius = frappe.get_value("Location", site_location, ["latitude","longitude", "geofence_radius"] )
		distance =  flt(haversine(site_lat, site_lng, latitude, longitude), precision=2)
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
		if checkpoint_assignment.employee and checkpoint_assignment.employee == employee:
			newscan.same_assignment = "YES"
		elif checkpoint_assignment.post and checkpoint_assignment.post == employee:
			print("TO BE DONE!!!")
		else:
			newscan.same_assignment = "NO"
			newscan.employee = checkpoint_assignment.employee_name

		print(newscan.as_dict())
	else:
		checkpoint_name, project, site = frappe.get_value("Checkpoints", {"checkpoint_code": qr_code}, ["name", "project_name", "site_name"])
		newscan.checkpoint_name = checkpoint_name
		newscan.project = project
		newscan.site = site
		newscan.has_assignment = "NO"
	newscan.save()
	frappe.db.commit()		
	#Compare the scan time with the nearest start ckeckpoint assignment Start time, select that checkpoint

	# Measue the distance, if the distance is outside the geofence then select NO and point the distance		

	# Compare employee/Post if it is the same then select Yes, if not select NO and place the correct one.


	# The record should be submittable.
	# If any NO then a notification should be sent to the Site Supervisor and the Site Supervisor should comment in the record with a reason. The process can accept or issue a penalty.


	# Create a New Record in Checkpoint Assignment Scan Doctype

	# print(qr_code, user, employee_id, location, get_datetime())