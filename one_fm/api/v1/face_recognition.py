import frappe, ast, base64, time
from frappe import _
from one_fm.one_fm.page.face_recognition.face_recognition import update_onboarding_employee
from one_fm.api.v1.utils import get_current_shift
from one_fm.api.v1.utils import response
import grpc
import json
from one_fm.proto import facial_recognition_pb2, facial_recognition_pb2_grpc, enroll_pb2, enroll_pb2_grpc


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

        if res.enrollment == "FAILED":
            return response(res.message, 400, None, res.data)

        doc = frappe.get_doc("Employee", {"user_id": frappe.session.user})
        doc.enrolled = 1
        doc.save(ignore_permissions=True)
        update_onboarding_employee(doc)
        frappe.db.commit()

        return response("Success", 201, "User enrolled successfully.")

    except Exception as error:
       return response("Internal Server Error", 500, None, error)


@frappe.whitelist()
def verify_checkin_checkout(employee_id: str = None, video : str = None, log_type: str = None, skip_attendance: int = None, latitude: float = None, longitude: float = None):
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
        return response("Bad Request", 400, "Invalid skip_attendance. skip_atten must be 0 or 1.")

    if not isinstance(latitude, float):
        return response("Bad Request", 400, None, "latitude must be of type float.")

    if not isinstance(longitude, float):
        return response("Bad Request", 400, None, "longitude must be of type float.")

    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        # setup channel
        face_recognition_service_url = frappe.local.conf.face_recognition_service_url
        channel = grpc.secure_channel(face_recognition_service_url, grpc.ssl_channel_credentials())
        # setup stub
        stub = facial_recognition_pb2_grpc.FaceRecognitionServiceStub(channel)

        # request body
        req = facial_recognition_pb2.FaceRecognitionRequest(
            username = frappe.session.user,
            media_type = "video",
            media_content = video
        )
        # Call service stub and get response
        res = stub.FaceRecognition(req)

        if res.verification == "FAILED":
            msg = res.message
            data = res.data
            return response(msg, 400, None, data)

        doc = create_checkin_log(employee, log_type, skip_attendance, latitude, longitude)
        return response("Success", 201, doc)

    except Exception as error:
        return response("Internal Server Error", 500, None, error)


def create_checkin_log(employee: str, log_type: str, skip_attendance: int, latitude: float, longitude: float) -> dict:
    checkin = frappe.new_doc("Employee Checkin")
    checkin.employee = employee
    checkin.log_type = log_type
    checkin.device_id = frappe.utils.cstr(latitude)+","+frappe.utils.cstr(longitude)
    checkin.skip_auto_attendance = skip_attendance
    checkin.save()
    frappe.db.commit()
    return checkin.as_dict()

@frappe.whitelist()
def get_site_location(employee_id: str = None, latitude: float = None, longitude: float = None) -> dict:

    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not latitude:
        return response("Bad Request", 400, None, "latitude required.")

    if not longitude:
        return response("Bad Request", 400, None, "longitude required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee must be of type str.")

    try:
        from one_fm.api.doc_events import haversine

        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))

        shift = get_current_shift(employee)
        if not shift or len(shift) == 0:
            return response("Resource Not Found", 400, None, "User not assigned to a shift.")

        site = frappe.get_value("Operations Shift", shift.shift, "site")
        location = frappe.db.sql("""
            SELECT loc.latitude, loc.longitude, loc.geofence_radius
            FROM `tabLocation` as loc
            WHERE
                loc.name in(SELECT site_location FROM `tabOperations Site` where name=%(site)s)
        """, {'site': site}, as_dict=1)

        if not location:
            return response("Resource Not Found", 404, None, "No site location set for {site}".format(site=site))

        result=location[0]
        result['user_within_geofence_radius'] = True

        distance = float(haversine(result.latitude, result.longitude, latitude, longitude))
        if distance > float(result.geofence_radius):
            result['user_within_geofence_radius'] = False

        result['site_name']=site
        # log to checkin radius log
        data = result.copy()
        data = {
            **data,
            **{'employee':employee_id, 'user_latitude':latitude, 'user_longitude':longitude, 'user_distance':distance, 'diff':distance-result.geofence_radius}
        }
        frappe.enqueue('one_fm.one_fm.doctype.checkin_radius_log.checkin_radius_log.create_checkin_radius_log',
            **{'data':data})
        return response("Success", 200, result)

    except Exception as error:
        return response("Internal Server Error", 500, None, error)
