import frappe, ast, base64, time, grpc, json, random
from frappe import _
from one_fm.one_fm.page.face_recognition.face_recognition import update_onboarding_employee, check_existing
from one_fm.utils import get_current_shift
from one_fm.api.v1.utils import response
from frappe.utils import cstr, getdate,now_datetime
from one_fm.proto import facial_recognition_pb2, facial_recognition_pb2_grpc, enroll_pb2, enroll_pb2_grpc
from one_fm.api.doc_events import haversine



# setup channel for face recognition
face_recognition_service_url = frappe.local.conf.face_recognition_service_url
options = [('grpc.max_message_length', 100 * 1024 * 1024* 10)]
channels = [
    grpc.secure_channel(i, grpc.ssl_channel_credentials(), options=options) for i in face_recognition_service_url
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

    # if not video:
    #     return response("Bad Request", 400, None, "Base64 encoded video content required.")

    # if not isinstance(video, str):
    #     return response("Bad Request", 400, None, "video type must be str.")

    try:
        doc = frappe.get_doc("Employee", {"user_id": frappe.session.user})
        # Setup channel
        # face_recognition_enroll_service_url = frappe.local.conf.face_recognition_enroll_service_url
        # channel = grpc.secure_channel(face_recognition_enroll_service_url, grpc.ssl_channel_credentials(), options=[('grpc.max_message_length', 100 * 1024 * 1024* 10)])
        # # setup stub
        # stub = enroll_pb2_grpc.FaceRecognitionEnrollmentServiceStub(channel)
        # # request body
        # req = enroll_pb2.EnrollRequest(
        #     username = frappe.session.user,
        #     user_encoded_video = video,
        # )

        # res = stub.FaceRecognitionEnroll(req)
        # data = {'employee':doc.name, 'log_type':'Enrollment', 'verification':res.enrollment,
        #         'message':res.message, 'data':res.data, 'source': 'Enroll'}
        # #frappe.enqueue('one_fm.operations.doctype.face_recognition_log.face_recognition_log.create_face_recognition_log',**{'data':data})
        # if res.enrollment == "FAILED":
        #     return response(res.message, 400, None, res.data)

        doc.enrolled = 1
        doc.save(ignore_permissions=True)
        update_onboarding_employee(doc)
        frappe.db.commit()

        return response("Success", 201, "User enrolled successfully.<br>Please wait for 10sec, you will be redirected to checkin.")

    except Exception as error:
        frappe.log_error(message=error, title="Enrollment")
        return response("Internal Server Error", 500, None, error)


@frappe.whitelist()
def verify_checkin_checkout(employee_id: str = None, video : str = None, log_type: str = None,
        skip_attendance: str = None, latitude: str = None, longitude: str = None):
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
    try:
        # ensure skip attendance is correctly formated
        try:
            skip_attendance = int(skip_attendance) if skip_attendance else 0
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            return response("Bad Request", 400, None, "skip_attendance must be an integer, latitude and longitude must be float.")

        if not employee_id:
            return response("Bad Request", 400, None, "employee_id required.")

        # if not video:
        #     return response("Bad Request", 400, None, "video required.")

        if not log_type:
            return response("Bad Request", 400, None, "log_type required.")

        if not skip_attendance:
            return response("Bad Request", 400, None, "skip_attendance required.")

        if not latitude:
            return response("Bad Request", 400, None, "latitdue required.")

        if not longitude:
            return response("Bad Request", 400, None, "longitude required.")

        # if not isinstance(video, str):
        #     return response("Bad Request", 400, None, "video must be of type str.")

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

        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        # setup channel
        # face_recognition_service_url = frappe.local.conf.face_recognition_service_url
        # channel = grpc.secure_channel(face_recognition_service_url, grpc.ssl_channel_credentials())
        # setup stub
        # stub = facial_recognition_pb2_grpc.FaceRecognitionServiceStub(channel)
        # request body
        # req = facial_recognition_pb2.FaceRecognitionRequest(
        #     username = frappe.session.user,
        #     media_type = "video",
        #     media_content = video
        # )
        # Call service stub and get response
        # res = random.choice(stubs).FaceRecognition(req)
        # data = {'employee':employee, 'log_type':log_type, 'verification':res.verification,
        #     'message':res.message, 'data':res.data, 'source': 'Checkin'}
        # if res.verification == "FAILED" and 'Invalid media content' in res.data:
        #     frappe.enqueue('one_fm.operations.doctype.face_recognition_log.face_recognition_log.create_face_recognition_log',
        #     **{'data':{'employee':employee, 'log_type':log_type, 'verification':res.verification,
        #         'message':res.message, 'data':res.data, 'source': 'Checkin'}})
                
        #     doc = create_checkin_log(employee, log_type, skip_attendance, latitude, longitude, "Mobile App")
        #     return response("Success", 201, doc, None)
        
        # if res.verification == "FAILED":
        #     msg = res.message
        #     if not res.verification == "OK":
        #         frappe.enqueue('one_fm.operations.doctype.face_recognition_log.face_recognition_log.create_face_recognition_log',**{'data':data})
        #     return response(msg, 400, None, data)
        # elif res.verification == "OK":
        doc = create_checkin_log(employee, log_type, skip_attendance, latitude, longitude, "Mobile App")
        return response("Success", 201, doc, None)
    except Exception as error:
        frappe.log_error(frappe.get_traceback(), 'Verify Checkin')
        return response("Internal Server Error", 500, None, error)


def create_checkin_log(employee: str, log_type: str, skip_attendance: int, latitude: float, longitude: float, source: str) -> dict:
    checkin = frappe.new_doc("Employee Checkin")
    checkin.employee = employee
    checkin.log_type = log_type
    checkin.device_id = frappe.utils.cstr(latitude)+","+frappe.utils.cstr(longitude)
    checkin.skip_auto_attendance = 0 #skip_attendance
    checkin.source = source
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

@frappe.whitelist()
def get_site_location(employee_id: str = None, latitude: float = None, longitude: float = None) -> dict:

    try:
        if not employee_id:
            return response("Bad Request", 400, None, "employee_id required.")

        if not latitude:
            return response("Bad Request", 400, None, "latitude required.")

        if not longitude:
            return response("Bad Request", 400, None, "longitude required.")

        if not isinstance(employee_id, str):
            return response("Bad Request", 400, None, "employee must be of type str.")
        
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})
        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        shift = get_current_shift(employee)
        date = cstr(getdate())
        
        site, location = None, None
        if shift:
            if not shift.can_checkin_out:
                # check if user can checkin with the correct time
                return response("Resource Not Found", 404, None, "Your are outside shift hours")
            
            log_type = shift.check_existing_checking()
            if log_type=='IN':
                if shift.after_4hrs():
                    # check if hrs has passed since shift start. Here we can also allow those who checked out tp checkin by checkin if OUT exist for same shift
                    return response("Resource Not Found", 404, None, "You are 4 or more hours late, you cannot checkin at this time.")

            if frappe.db.exists("Shift Request", {
                "employee":employee, 'from_date':['<=',date],
                'to_date':['>=',date], "status": "Approved"}
                ):
                check_in_site, check_out_site = frappe.get_value("Shift Request", {
                    "employee":employee, 'from_date':['<=',date],'to_date':['>=',date], 
                    "status": "Approved"},["check_in_site","check_out_site"]
                )
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
            return response("Resource Not Found", 404, None, "User not assigned to a shift.")

        if not location and site:
            return response("Resource Not Found", 404, None, "No site location set for {site}".format(site=site))

        result=location[0]
        result['user_within_geofence_radius'] = True

        distance = float(haversine(result.latitude, result.longitude, latitude, longitude))
        if distance > float(result.geofence_radius):
            result['user_within_geofence_radius'] = False

        result['site_name'] = site
        if shift:
            result['shift'] = shift

        # log to checkin radius log
        data = result.copy()
        data = {
            **data,
            **{'employee':employee_id, 'user_latitude':latitude, 'user_longitude':longitude, 'user_distance':distance, 'diff':distance-result.geofence_radius}
        }
        if not result['user_within_geofence_radius']:
            frappe.enqueue('one_fm.operations.doctype.checkin_radius_log.checkin_radius_log.create_checkin_radius_log', **{'data':data})
        result['log_type'] = log_type
        return response("Success", 200, result)

    except Exception as error:
        frappe.log_error(title="API Site location", message=frappe.get_traceback())
        return response("Internal Server Error", 500, None, error)
