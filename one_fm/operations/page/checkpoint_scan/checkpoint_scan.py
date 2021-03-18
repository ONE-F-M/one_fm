import frappe
from frappe.utils import get_datetime

@frappe.whitelist()
def scan_checkpoint(qr_code, latitude, longitude):
    user = frappe.session.user
    employee_id = frappe.get_value("Employee", {"user_id": user}) #Will be None if logged in as Administrator  
    location = latitude + " " + longitude
    date = get_datetime()


    # Check if the checkpoint scan is in the checkpoint assignment doctype
    checkpointassignment = frappe.get_list('Checkpoints Assignment', filters= {
        'start_date_time': #Today & Yesterday, Issue is midnight checkpoints 
        'checkpoint_code': qr_code
    })
    #Compare the scan time with the nearest start ckeckpoint assignment Start time, select that checkpoint
        
        #no, Take Need to figure this out!!

    # Compare employee/Post if it is the same then select Yes, if not select NO and place the correct one.

    # Measue the distance, if the distance is outside the geofence then select NO and point the distance

    # The record should be submittable.
    # If any NO then a notification should be sent to the Site Supervisor and the Site Supervisor should comment in the record with a reason. The process can accept or issue a penalty.


    # Create a New Record in Checkpoint Assignment Scan Doctype
    # newscan = frappe.new_doc('Checkpoint Assignment Scan')
    # newscan.scan_datetime = get_datetime()
    # newscan.scanned_by = employee_id.name
    # newscan.scan_location = location
    # newscan.checkpoint_name = frappe.get_value("Checkpoints", {"checkpoint_code": qr_code})


    



    # print(qr_code, user, employee_id, location, get_datetime())