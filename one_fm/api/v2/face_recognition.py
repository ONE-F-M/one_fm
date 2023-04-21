from datetime import timedelta, datetime
import frappe, ast, base64, time, grpc, json, random
from frappe import _
from one_fm.one_fm.page.face_recognition.face_recognition import update_onboarding_employee, check_existing
from one_fm.api.v1.roster import get_current_shift
from one_fm.api.v1.utils import response
from one_fm.api.v2.zenquotes import fetch_quote

from frappe.utils import cstr, getdate,get_datetime,now,get_date_str, now_datetime
from one_fm.proto import facial_recognition_pb2, facial_recognition_pb2_grpc, enroll_pb2, enroll_pb2_grpc
from one_fm.api.doc_events import haversine
from one_fm.utils import get_holiday_today


# setup channel for face recognition
face_recognition_service_url = frappe.local.conf.face_recognition_service_url
channels = [
    grpc.secure_channel(i, grpc.ssl_channel_credentials()) for i in face_recognition_service_url
]

# setup stub for face recognition
stubs = [
    facial_recognition_pb2_grpc.FaceRecognitionServiceStub(i) for i in channels
]


@frappe.whitelist()
def enroll(employee_id: str = None, video: str = None) -> dict:
    """This method enrolls the user face into the system for future face recognition use cases.

    Args:
        employee_id (str): employee_id of user
        video (str): Base64 encoded string of the video captured of user's face.

    Returns:
        response (dict): {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): Enrollment status,
            error (str): Any error handled.
        }
    """
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not video:
        return response("Bad Request", 400, None, "Base64 encoded video content required.")

    if not isinstance(video, str):
        return response("Bad Request", 400, None, "video type must be str.")

    try:
        doc = frappe.get_doc("Employee", {"user_id": frappe.session.user})
        # Setup channel
        face_recognition_enroll_service_url = frappe.local.conf.face_recognition_enroll_service_url
        channel = grpc.secure_channel(face_recognition_enroll_service_url, grpc.ssl_channel_credentials())
        # setup stub
        stub = enroll_pb2_grpc.FaceRecognitionEnrollmentServiceStub(channel)
        # request body
        req = enroll_pb2.EnrollRequest(
            username = frappe.session.user,
            user_encoded_video = video,
        )

        res = stub.FaceRecognitionEnroll(req)
        data = {'employee':doc.name, 'log_type':'Enrollment', 'verification':res.enrollment,
                'message':res.message, 'data':res.data, 'source': 'Enroll'}
        #frappe.enqueue('one_fm.operations.doctype.face_recognition_log.face_recognition_log.create_face_recognition_log',**{'data':data})
        if res.enrollment == "FAILED":
            return response(res.message, 400, None, res.data)

        doc.enrolled = 1
        doc.save(ignore_permissions=True)
        update_onboarding_employee(doc)
        frappe.db.commit()

        return response("Success", 201, "User enrolled successfully.")

    except Exception as error:
        return response("Internal Server Error", 500, None, error)


@frappe.whitelist()
def verify_checkin_checkout(employee_id: str = None, video : str = None, log_type: str = None, 
    shift_assignment: str = None, skip_attendance: str = None, latitude: str = None, longitude: str = None):
    """This method verifies user checking in/checking out.

    Args:
        employee_id (srt): employee_id of user
        video (str, optional): base64 encoded video of user checking in/checking out.
        log_type (str, optional): IN/OUT
        skip_attendance (int, optional): 0/1.
        latitude (float, optional): Latitude od user.
        longitude (float, optional): Longitude od user.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): checkin log created.
            error (str): Any error handled.
        }
    """
    # ensure skip attendance is correctly formated
    try:
        skip_attendance = int(skip_attendance) if skip_attendance else 0
        latitude = float(latitude)
        longitude = float(longitude)
    except:
        return response("Bad Request", 400, None, "skip_attendance must be an integer, latitude and longitude must be float.")

    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not video:
        return response("Bad Request", 400, None, "video required.")

    if not log_type:
        return response("Bad Request", 400, None, "log_type required.")

    if not skip_attendance:
        return response("Bad Request", 400, None, "skip_attendance required.")

    if not latitude:
        return response("Bad Request", 400, None, "latitdue required.")

    if not longitude:
        return response("Bad Request", 400, None, "longitude required.")

    if not isinstance(video, str):
        return response("Bad Request", 400, None, "video must be of type str.")

    if not isinstance(log_type, str):
        return response("Bad Request", 400, None, "log_type must be of type str.")

    if log_type not in ["IN", "OUT"]:
        return response("Bad Request", 400, None, "Invalid log_type. log_type must be IN/OUT.")

    if not isinstance(skip_attendance, int):
        return response("Bad Request", 400, None, "skip_attendance must be of type int.")

    if skip_attendance not in [0, 1]:
        return response("Bad Request", 400, "Invalid skip_attendance. skip_attendance must be 0 or 1.")

    if not isinstance(latitude, float):
        return response("Bad Request", 400, None, "latitude must be of type float.")

    if not isinstance(longitude, float):
        return response("Bad Request", 400, None, "longitude must be of type float.")

    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        right_now = now_datetime() 

        if log_type == "IN":
            shift_type = frappe.db.sql(f""" select shift_type from `tabShift Assignment` where employee = '{employee}' order by creation desc limit 1 """, as_dict=1)[0]
            val_in_shift_type = frappe.db.sql(f""" select begin_check_in_before_shift_start_time, start_time, late_entry_grace_period, working_hours_threshold_for_absent from `tabShift Type` where name = '{shift_type["shift_type"]}' """, as_dict=1)[0]
            time_threshold = datetime.strptime(str(val_in_shift_type["start_time"] - timedelta(minutes=val_in_shift_type["begin_check_in_before_shift_start_time"])), "%H:%M:%S").time()

            if right_now.time() < time_threshold:
                return response("Bad Request", 400, None, f" Oops! You can't check in right now. Your check-in time is {val_in_shift_type['begin_check_in_before_shift_start_time']} minutes before you start your shift." + "\U0001F612")

            existing_perm = frappe.db.sql(f""" select name from `tabShift Permission` where date = '{right_now.date()}' and employee = '{employee}' and permission_type = '{log_type}' and workflow_state = 'Approved' """, as_dict=1)
            if not existing_perm and (right_now.time() >  datetime.strptime(str(val_in_shift_type["start_time"] + + timedelta(hours=int(val_in_shift_type['working_hours_threshold_for_absent']))), "%H:%M:%S").time()):
                return response("Bad Request", 400, None, f"Oops! You are late beyond the  {int(val_in_shift_type['working_hours_threshold_for_absent'])} - hour time mark and you are marked absent !" + "\U0001F612")       
                
        # setup channel
        # face_recognition_service_url = frappe.local.conf.face_recognition_service_url
        # channel = grpc.secure_channel(face_recognition_service_url, grpc.ssl_channel_credentials())
        # setup stub
        # stub = facial_recognition_pb2_grpc.FaceRecognitionServiceStub(channel)
        # request body
        req = facial_recognition_pb2.FaceRecognitionRequest(
            username = frappe.session.user,
            media_type = "video",
            media_content = video
        )
        # Call service stub and get response
        
        res = random.choice(stubs).FaceRecognition(req)

        if res.verification == "FAILED" and 'Invalid media content' in res.data:
            frappe.enqueue('one_fm.operations.doctype.face_recognition_log.face_recognition_log.create_face_recognition_log',
            **{'data':{'employee':employee, 'log_type':log_type, 'verification':res.verification,
                'message':res.message, 'data':res.data, 'source': 'Checkin'}})
            doc = create_checkin_log(employee, log_type, skip_attendance, latitude, longitude, shift_assignment)
            if log_type == "IN":
                check = late_checkin_checker(doc, val_in_shift_type, existing_perm )
                if check:
                    doc.update({"message": "You Checked in, but you were late, try to checkin early next time !" +  "\U0001F612"})
                    return response("Success", 201, doc, None)
            return response("Success", 201, doc, None)
        elif res.verification == "FAILED":
            msg = res.message
            data = res.data
            frappe.enqueue('one_fm.operations.doctype.face_recognition_log.face_recognition_log.create_face_recognition_log',
            **{'data':{'employee':employee, 'log_type':log_type, 'verification':res.verification,
                'message':res.message, 'data':res.data, 'source': 'Checkin'}})
            return response(msg, 400, None, data)
        elif res.verification == "OK":
            doc = create_checkin_log(employee, log_type, skip_attendance, latitude, longitude, shift_assignment)
            if log_type == "IN":
                check = late_checkin_checker(doc, val_in_shift_type, existing_perm )
                if check:
                    doc.update({"message": "You Checked in, but you were late, try to checkin early next time !" +  "\U0001F612"})
                    return response("Success", 201, doc, None)
            quote = fetch_quote(direct_response=True)
            return response("Success", 201, {'doc':doc,'quote':quote}, None)

        else:
            return response("Success", 400, None, "No response from face recognition server")
    except Exception as error:
        return response("Internal Server Error", 500, None, error)


def create_checkin_log(employee: str, log_type: str, skip_attendance: int, latitude: float, longitude: float, shift_assignment: str) -> dict:
    checkin = frappe.new_doc("Employee Checkin")
    checkin.employee = employee
    checkin.log_type = log_type
    checkin.device_id = frappe.utils.cstr(latitude)+","+frappe.utils.cstr(longitude)
    checkin.skip_auto_attendance = 0 #skip_attendance
    checkin.shift_assignment = shift_assignment
    checkin.save()
    frappe.db.commit()
    return checkin.as_dict()

def check_employee_non_shift(employee):
    shift_working, employement_type = frappe.get_value("Employee", employee, ["shift_working","employment_type"])
    if shift_working==0 and employement_type!="Contract":
        return True
    return False

def has_day_off(employee,date):
    """
        Confirm if the employee schedule for that day and employee is set to day off
    """
    is_day_off = False
    existing_schedule = frappe.get_value("Employee Schedule",{'employee':employee,'date':date},['employee_availability'])
    if existing_schedule:
        if existing_schedule == 'Day Off':
            is_day_off = True
    return is_day_off

def has_attendance(employee, date):
    '''
    This method is to check if employee has an attendance marked for the day.
    '''
    attendance_marked = False
    attendance = frappe.db.exists("Attendance", {"employee":employee, "attendance_date":date})
    if attendance:
        attendance_marked = True
    return attendance_marked

def has_checkout_record(employee, shift_type):
    '''
    This method is to check if employee has an check out record for the day.
    '''
    checkout_record = False

    start_time = get_datetime(cstr(getdate()) + " 00:00:00")
    end_time = get_datetime(cstr(getdate()) + " 23:59:59")

    log_exist = frappe.db.exists("Employee Checkin", {"employee": employee, "log_type": "OUT", "time": [ "between", (start_time, end_time)], "skip_auto_attendance": 0 ,"shift_type": shift_type})

    if log_exist:
        checkout_record = True
    return checkout_record

def has_shift_permission(employee, log_type, date):
    """
        Confirm if the employee has shift p[ermission at current time.
    """
    has_shift_permission = False
    
    current_time = datetime.strptime(now_datetime().strftime("%H:%M:%S"), "%H:%M:%S") - datetime(1900, 1, 1)

    permission_type = "Arrive Late" if log_type=="IN" else "Leave Early"
    shift_permission = frappe.get_list("Shift Permission",{'employee':employee,'date':date, "permission_type": permission_type},['*'])
    if shift_permission:
        if permission_type == "Arrive Late" and current_time < shift_permission[0].arrival_time:
            has_shift_permission = True
        if permission_type == "Leave Early" and current_time > shift_permission[0].leaving_time:
            has_shift_permission = True
    return has_shift_permission

@frappe.whitelist()
def get_site_location(employee_id: str = None, latitude: float = None, longitude: float = None) -> dict:
# "{'employee_id': '2105002IN196', 'latitude': 29.3660164, 'longitude':47.9658118}"
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not latitude:
        return response("Bad Request", 400, None, "latitude required.")

    if not longitude:
        return response("Bad Request", 400, None, "longitude required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee must be of type str.")

    try:

        employee_doc = frappe.get_doc("Employee", {"employee_id": employee_id})
        employee = employee_doc.name
        date = cstr(getdate())
        log = check_existing()

        if log == False:
            log_type = "IN"
        else:
            log_type = "OUT"

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        if has_attendance(employee, date):
            return response("Resource Not Found", 404, None, "Your attendance has been marked For the Day")

        shift = get_current_shift(employee)

        site, location, shift_assignment = None, None, None
        if shift:
            if shift.shift_type and has_checkout_record(employee, shift.shift_type):
                return response("Resource Not Found", 404, None, "You have already Checked Out of the your current shift")
            
            if has_shift_permission(employee, log_type, date):
                return response("Resource Not Found", 404, None, "You have currently applied for Shift Permission")


            if frappe.db.exists("Shift Request", {"employee":employee, 'from_date':['<=',date],'to_date':['>=',date]}):
                check_in_site, check_out_site = frappe.get_value("Shift Request", {"employee":employee, 'from_date':['<=',date],'to_date':['>=',date]},["check_in_site","check_out_site"])
                if log_type == "IN":
                    site = check_in_site
                    location = frappe.get_list("Location", {'name':check_in_site}, ["latitude","longitude", "geofence_radius"])
                else:
                    site = check_out_site
                    location = frappe.get_list("Location", {'name':check_out_site}, ["latitude","longitude", "geofence_radius"])

            else:
                if shift.site_location:
                    site = shift.site_location
                    location = frappe.get_list("Location", {'name':shift.site_location}, ["latitude","longitude", "geofence_radius"])
                elif shift.shift:
                    site = frappe.get_value("Operations Shift", shift.shift, "site")
                    location= frappe.db.sql("""
                        SELECT loc.latitude, loc.longitude, loc.geofence_radius
                        FROM `tabLocation` as loc
                        WHERE
                        loc.name IN (SELECT site_location FROM `tabOperations Site` where name="{site}")
                        """.format(site=site), as_dict=1)


        if not site:
            if has_day_off(employee,date):
                employee_name = frappe.get_value("Employee",employee,'employee_name')
                return response("Resource Not Found", 404, None, f"Dear {employee_name}, Today is your day off.  Happy Recharging!.")
            if employee_doc.holiday_list:
                holiday_today = get_holiday_today(str(getdate()))
                if holiday_today.get(employee_doc.holiday_list):
                    return response("Resource Not Found", 404, None, "Today is your holiday, have fun.")
            return response("Resource Not Found", 404, None, "User not assigned to a shift.")

        if not location and site:
            return response("Resource Not Found", 404, None, "No site location set for {site}".format(site=site))

        result=location[0]
        result['user_within_geofence_radius'] = True

        distance = float(haversine(result.latitude, result.longitude, latitude, longitude))
        if distance > float(result.geofence_radius):
            result['user_within_geofence_radius'] = False

        result['site_name'] = site
        result['shift_assignment'] = shift

        # log to checkin radius log
        data = result.copy()
        result = frappe._dict(result)
        data = {
            **data,
            **{'employee':employee_id, 'user_latitude':latitude, 'user_longitude':longitude, 'user_distance':distance, 'diff':distance-result.geofence_radius}
        }
        
        if not result.user_within_geofence_radius:
            frappe.enqueue('one_fm.operations.doctype.checkin_radius_log.checkin_radius_log.create_checkin_radius_log',
                       **{'data':data})
        return response("Success", 200, {**result, **{'shift_assignment':shift}})

    except Exception as error:

        return response("Internal Server Error", 500, None, frappe.get_traceback())


def late_checkin_checker(doc, val_in_shift_type, existing_perm=None):
    if doc.time.time() > datetime.strptime(str(val_in_shift_type["start_time"] + timedelta(minutes=val_in_shift_type["late_entry_grace_period"])), "%H:%M:%S").time():
        if not existing_perm:
            return True