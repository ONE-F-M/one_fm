import frappe, base64, os
from frappe import _

from one_fm.one_fm.page.face_recognition.face_recognition import update_onboarding_employee
from datetime import timedelta
from one_fm.utils import get_current_shift, is_holiday,get_holiday_today
from one_fm.api.v1.utils import (
    response, verify_via_face_recogniton_service
)
from frappe.utils import cstr, getdate,now_datetime
from one_fm.api.doc_events import haversine
from one_fm.overrides.employee import has_day_off, is_employee_on_leave

# setup channel for face recognition

face_recog_base_url = frappe.local.conf.face_recognition_service_base_url
site_path = os.getcwd()+frappe.utils.get_site_path().replace('./', '/')
video_path = site_path + '/public/files/video.mp4'
video_txt_path = site_path + '/public/files/video.txt'


def base64_to_mp4(base64_string):
    # Decode the Base64 string to bytes
    video_data = base64.b64decode(base64_string)
    try:os.remove(video_path)
    except:pass
    # Write the bytes to an MP4 file
    with open(video_txt_path, 'w') as text_file:
            text_file.write(base64_string)

    with open(video_path, 'wb') as mp4_file:
        mp4_file.write(video_data)


@frappe.whitelist()
def enroll(employee_id: str = None, filename: str = None, video: str = None) -> dict:
    """This method enrolls the user face into the system for future face recognition use cases.

    Args:
        employee_id (str): employee_id of user

    Returns:
        response (dict): {
            message (str): Brief message indicating the response,
            status_code (int): Status code of response.
            data (dict): Enrollment status,
            error (str): Any error handled.
        }
    """
    try:
        if not employee_id:
            return response("Bad Request", 400, None, "Employee ID required.")

        if not filename:
            filename = frappe.session.user+'.mp4'

        video_file = frappe.request.files.get("video_file") or video or frappe.request.files.get("video")
        endpoint_state = frappe.db.get_single_value("ONEFM General Setting", 'enable_face_recognition_endpoint')
        if not video_file:
            if endpoint_state:
                return response("Bad Request", 400, None, "Video File is required.")

        # check Face Recognition Endpoint

        if endpoint_state:
            if not face_recog_base_url:
                return response("Bad Request", 400, None, "Face Recognition Service configuration is not available.")
            status, message = verify_via_face_recogniton_service(url=face_recog_base_url + "enroll", data={"username": frappe.session.user, "filename": filename}, files={"video_file": video_file})
        else:
            status, message = True, 'Successful'


        doc = frappe.get_doc("Employee", {"employee_id": employee_id})
        if not doc:
            return response("Resource Not Found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))



        if not status:
            return response("Bad Request", 400, None, message)

        # Set a context flag to indicate an API update (It will affect in 'Employee' validate method)
        frappe.flags.allow_enrollment_update = True

        doc.db_set('enrolled',1)

        update_onboarding_employee(doc)
        frappe.db.commit()

        return response("Success", 201,
                        "User enrolled successfully.<br>Please wait for 10sec, you will be redirected to checkin.")
    except Exception as error:
        frappe.log_error(message=frappe.get_traceback(), title="Enrollment")
        return response("Internal Server Error", 500, None, error)


@frappe.whitelist()
def verify_checkin_checkout(employee_id: str = None, log_type: str = None,shift: str = None,
                            skip_attendance: str = None, latitude: str = None, longitude: str = None,
                            filename: str = None,video: str = None):
    """This method verifies user checking in/checking out.

    Args:
        employee_id (srt): employee_id of user
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
            current_shift = shift
            skip_attendance = int(skip_attendance) if skip_attendance else 0
            latitude = float(latitude)
            longitude = float(longitude)
        except:
            return response("Bad Request", 400, None,
                            "skip_attendance must be an integer, latitude and longitude must be float.")

        if not employee_id:
            return response("Bad Request", 400, None, "Employee ID is required")

        if not log_type:
            return response("Bad Request", 400, None, "Log type parameter required")

        if not skip_attendance:
            return response("Bad Request", 400, None, "Skip attendance parameter required.")

        if not latitude:
            return response("Bad Request", 400, None, "Latitude parameter required.")

        if not longitude:
            return response("Bad Request", 400, None, "Longitude parameter required.")

        if not isinstance(log_type, str):
            return response("Bad Request", 400, None, "Invalid log type format. Please enter a valid value.")

        if log_type not in {"IN", "OUT"}:
            return response("Bad Request", 400, None, "Invalid log type. Log type must be IN/OUT.")

        if not isinstance(skip_attendance, int):
            return response("Bad Request", 400, None, "Skip attendance parameter must be an integer.")

        if skip_attendance not in {0, 1}:
            return response("Bad Request", 400, "Invalid skip attendance parameter. It must be 0 or 1.")

        if not isinstance(latitude, float):
            return response("Bad Request", 400, None, "Latitude must be of type float.")

        if not isinstance(longitude, float):
            return response("Bad Request", 400, None, "Longitude must be of type float.")

        endpoint_state = frappe.db.get_single_value("ONEFM General Setting", 'enable_face_recognition_endpoint')
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id}, ["name", "custom_enable_face_recognition"], as_dict=1)

        video_file = frappe.request.files.get("video_file") or video or frappe.request.files.get("video")
        if not video_file:
            if endpoint_state and employee.custom_enable_face_recognition:
                return response("Bad Request", 400, None, "Video File is required.")


        if not employee.name:
            return response("Resource Not Found", 404, None, "No employee record found with {employee_id}".format(employee_id=employee_id))
        
        right_now = now_datetime()
        if log_type == "IN":
            shift_info = frappe.db.sql(f"""
                SELECT 
                    sa.start_datetime, 
                    st.begin_check_in_before_shift_start_time 
                FROM 
                    `tabShift Assignment` sa
                JOIN 
                    `tabShift Type` st ON sa.shift_type = st.name
                WHERE 
                    sa.employee = '{employee.name}' 
                ORDER BY 
                    sa.creation DESC 
                LIMIT 1
            """, as_dict=1)[0]
            shift_actual_start = shift_info.start_datetime - timedelta(minutes=shift_info.begin_check_in_before_shift_start_time)
            if right_now < shift_actual_start:
                return response("Bad Request", 400, None, f" Oops! You can't check in right now. Your check-in time is {shift_info.begin_check_in_before_shift_start_time} minutes before you start your shift." + "\U0001F612")
        # check Face Recognition Endpoint
        
        if not filename:
            filename = frappe.session.user+'.mp4'
        if endpoint_state and employee.custom_enable_face_recognition:
            if not face_recog_base_url:
                return response("Bad Request", 400, None, "Face Recognition Service configuration is not available.")
            status, message = verify_via_face_recogniton_service(url=face_recog_base_url + "verify", data={
                "username": frappe.session.user, "filename": filename
                }, files={"video_file": video_file})
        else:
            status, message = True, 'Successful'

        if not status:
            return response("Bad Request", 400, None, message)
        doc = create_checkin_log(employee.name, log_type, skip_attendance, latitude, longitude,current_shift, "Mobile App")
        return response("Success", 201, doc, None)

    except Exception as error:
        frappe.log_error(message=frappe.get_traceback(), title="Verify Checkin Error")
        return response("Internal Server Error", 500, None, error)


def create_checkin_log(employee: str, log_type: str, skip_attendance: int, latitude: float, longitude: float,current_shift:str,
                       source: str) -> dict:
    checkin = frappe.new_doc("Employee Checkin")
    checkin.employee = employee
    checkin.log_type = log_type
    checkin.device_id = frappe.utils.cstr(latitude) + "," + frappe.utils.cstr(longitude)
    checkin.skip_auto_attendance = 0  #skip_attendance
    checkin.source = source
    checkin.shift_assignment=current_shift
    checkin.save()
    frappe.db.commit()
    return checkin.as_dict()


def check_employee_non_shift(employee):
    shift_working, employement_type = frappe.get_value("Employee", employee, ["shift_working", "employment_type"])
    if shift_working == 0 and employement_type != "Contract":
        return True
    return False

def has_day_off(employee,date):
    """
        Confirm if the employee schedule for that day and employee is set to day off
    """
    return frappe.db.exists("Employee Schedule", {"employee": employee, "date": date, "employee_availability": "Day Off"})


@frappe.whitelist()
def get_site_location(employee_id: str = None, shift: str = None,latitude: float = None, longitude: float = None) -> dict:
    try:
        if not employee_id:
            return response("Bad Request", 400, None, "Employee ID required.")

        if not latitude:
            return response("Bad Request", 400, None, "Latitude required.")

        if not longitude:
            return response("Bad Request", 400, None, "Longitude required.")

        if not isinstance(employee_id, str):
            return response("Bad Request", 400, None, "Invalid Employee ID format. Please enter a valid value.")

        employee = frappe.db.get_value("Employee", {"employee_id": employee_id}, ["name", "holiday_list", "employee_name", "shift_working"], as_dict=1)
        if not employee:
            return response("Resource Not Found", 404, None,
                            "No employee record found with {employee_id}".format(employee_id=employee_id))
        
        today = getdate()
        
        # check for fingerprint appointment
        fingerprint_appointment = frappe.db.exists("Employee Schedule", {
            "employee": employee.name,
            "date": today,
            "employee_availability": "Fingerprint Appointment"
        })
        if fingerprint_appointment:
            return response("Resource Not Found", 404, None, "You have a fingerprint appointment. See you soon!")

        # check for medical appointment
        medical_appointment = frappe.db.exists("Employee Schedule", {
            "employee": employee.name,
            "date": today,
            "employee_availability": "Medical Appointment"
        })
        if medical_appointment:
            return response("Resource Not Found", 404, None, "You have a medical appointment. See you soon!")
        shift = frappe.get_doc("Shift Assignment", shift) if shift and shift != 'undefined' else None
        upcoming_shifts = []

        if not shift:
            shift_details = get_current_shift(employee.name, attach_upcoming_shifts=True)
            if shift_details:
                if shift_details['type'] == "Early":
                    # check if user can checkin with the correct time
                    return response("Resource Not Found", 404, None,
                                    f"You are checking in too early. Check-in is allowed in {shift_details['time']} minutes.")
                elif shift_details['type'] == "Late":
                    return response("Resource Not Found", 404, None,
                                    f"You are checking out too late. Check-out was allowed until {shift_details['time']} minutes ago.")
                elif shift_details['type'] == "Upcoming":
                    return response("Resource Not Found", 404, None,
                                    f"Check-in for your shift starts in {shift_details['time']} minutes.")
                elif shift_details['type'] == "On Time":
                    shift = shift_details['data']  # Return the object of Shift Assignment
                    upcoming_shifts = shift_details['upcoming_shifts']

        date = cstr(getdate())

        if shift:
            if shift.is_replaced == 1:
                return response("Resource Not Found", 404, None, f"You have been replaced with another Employee.")

            if is_attendance_request_exists(employee.name, date):
                return response("Resource Not Found", 404, None,
                                f"You have an attendance request for today. Your attendance will be marked.")

            log_type = shift.get_next_checkin_log_type()
            if log_type == 'IN':
                if shift.after_4hrs():
                    # check if hrs has passed since shift start. Here we can also allow those who checked out tp checkin by checkin if OUT exist for same shift
                    return response("Resource Not Found", 404, None,
                                    "You are 4 or more hours late, you cannot checkin at this time.")

            location = get_shift_site_location(shift, date, log_type)
            site = frappe.get_value("Operations Shift", shift.shift, "site")

            if location:
                result = location
                result['user_within_geofence_radius'] = True
                # Convert upcoming_shifts to dictionaries with log_type
                if upcoming_shifts:
                    result['upcoming_shifts'] = [
                        {**upcoming_shift.as_dict(), 'log_type': upcoming_shift.get_next_checkin_log_type(), 'is_completed': upcoming_shift.get("is_completed", False)}
                        for upcoming_shift in upcoming_shifts
                    ]
                else:
                    result['upcoming_shifts'] = []

                distance = float(haversine(result.latitude, result.longitude, latitude, longitude))
                if distance > float(result.geofence_radius):
                    result['user_within_geofence_radius'] = False

                result['site_name'] = site
                if shift:
                    result['shift'] = {**shift.as_dict(), 'log_type': log_type, 'is_completed': shift.get("is_completed", False)}

                # log to checkin radius log
                data = result.copy()
                data = {
                    **data,
                    **{'employee': employee_id, 'user_latitude': latitude, 'user_longitude': longitude,
                       'user_distance': distance, 'diff': distance - result.geofence_radius}
                }
                if not result['user_within_geofence_radius']:
                    frappe.enqueue(
                        'one_fm.operations.doctype.checkin_radius_log.checkin_radius_log.create_checkin_radius_log',
                        **{'data': data})
                result['log_type'] = log_type
                facial_recognition_endpoint_state  = frappe.db.get_single_value("ONEFM General Setting", 'enable_face_recognition_endpoint')
                result['endpoint_status'] = facial_recognition_endpoint_state
                return response("Success", 200, result)

            elif site:
                return response("Resource Not Found", 404, None, "No site location set for {site}".format(site=site))

        else:
            if employee.shift_working:
                if has_day_off(employee.name, date):
                    return response("Resource Not Found", 404, None,
                                    f"Dear {employee.employee_name}, Today is your day off.  Happy Recharging!.")
            if employee.holiday_list:
                holiday_today = get_holiday_today(str(getdate()))
                if holiday_today.get(employee.holiday_list):
                    return response("Resource Not Found", 404, None, "Today is your holiday, have fun.")


            if is_employee_on_leave(employee.name, date):
                return response("Resource Not Found", 404, None, "You are currently on leave, see you soon!")

            status, message = is_holiday(employee=employee, date=date)
            if status:
                return response("Resource Not Found", 404, None, message)
            return response("Resource Not Found", 404, None, "You are not assigned to a shift.")

    except Exception as error:
        frappe.log_error(title="API Site location", message=frappe.get_traceback())
        return response("Internal Server Error", 500, None, error)


def is_attendance_request_exists(employee, date):
    return frappe.db.exists(
        "Attendance Request",
        {
            "employee": employee,
            "from_date": ["<=", date],
            "to_date": [">=", date],
            "docstatus": 1
        }
    )


def get_shift_site_location(shift, date, log_type):
    """
        Method to retrieves the site location details (latitude, longitude, and optionally geofence radius)
        for a given shift on a specific date, considering both shift and shift request information.

        Args:
            shift (object): A object of Shift Assignment
            date (str): The date (YYYY-MM-DD format) for which to retrieve the location.
            log_type (str): "IN" or "OUT".

        Return:
            dict (or None): If a valid location is found, a dictionary containing the following keys is returned:
                latitude (float): The latitude of the site location.
                longitude (float): The longitude of the site location.
                geofence_radius (float, optional): The geofence radius of the site location.
            None: If no valid location information is found.
    """
    location = get_shift_request_site_location(shift.employee, date, log_type)
    if not location:
        if shift.site_location:
            return frappe.get_value(
                "Location",
                {"name": shift.site_location},
                ["latitude", "longitude", "geofence_radius"],
                as_dict=True
            )
        elif shift.shift:
            # Fetch the site from Operations Shift to get the location of the Site
            site = frappe.get_value("Operations Shift", shift.shift, "site")
            result = frappe.db.sql("""
                SELECT
                    loc.latitude, loc.longitude, loc.geofence_radius
                FROM
                    `tabLocation` as loc
                WHERE
                    loc.name IN (
                        SELECT site_location FROM `tabOperations Site` where name="{site}"
                    )
            """.format(site=site), as_dict=1)
            return result[0] if result else None
    return location


def get_shift_request_site_location(employee, date, log_type):
    """
        This function retrieves the site location details for an employee's approved shift request on a specific date.
        It checks for an "Approved" shift request that overlaps with the provided date and returns the corresponding check-in
        or check-out site location (depending on the log_type) along with its latitude, longitude, and geofence radius.

        Args:
            employee (str): The employee ID for whom to fetch the shift request details.
            date (str): The date (YYYY-MM-DD format) for which to check the shift request.
            log_type (str): "IN" or "OUT". This specifies whether to retrieve the check-in
                or check-out site location from the shift request.

        Return:
            dict (or None): If an approved shift request is found overlapping the provided date and log_type,
                a dictionary containing the following keys is returned:
                latitude (float): The latitude of the site location.
                longitude (float): The longitude of the site location.
                geofence_radius (float): The geofence radius of the site location (optional, depending on your data model).
            None: If no approved shift request is found or there's an error retrieving the location details.
    """

    location = False
    shift_request_exists = frappe.db.exists(
        "Shift Request",
        {
            "employee": employee,
            "from_date": ["<=", date],
            "to_date": [">=", date],
            "status": "Approved"
        }
    )
    if shift_request_exists:
        shift_request_details = frappe.get_value(
            "Shift Request",
            {
                "employee": employee,
                "from_date": ["<=", date],
                "to_date": [">=", date],
                "status": "Approved"
            },
            ["check_in_site", "check_out_site"],
            as_dict=True
        )
        if log_type == "IN":
            # Fetch check in site location from shift request
            location = shift_request_details.check_in_site
        else:
            # Fetch check out site location from shift request
            location = shift_request_details.check_out_site
        if location:
            # Return the location details
            return frappe.get_value(
                "Location",
                {"name": location},
                ["latitude", "longitude", "geofence_radius"],
                as_dict=True
            )
    return None

@frappe.whitelist()
def checkin_list(employee_id, from_date, to_date):
    """
    This method retrives employee checkin list
    """
    try:
        employee = frappe.db.get_value("Employee", {"employee_id":employee_id}, "name")
        if not employee:
            return response("Success", 404, None, "No employee record found for {employee_id}".format(employee_id=employee_id))
        checkins = frappe.get_all("Employee Checkin", filters={
            "employee": employee,
            "time": ["BETWEEN", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
            },
            fields=["name", "employee_name", "time", "log_type","employee.employee_name_in_arabic"],
            order_by="time DESC"
        )
        return response("success", 200, checkins)
    except Exception as e:
        return response("error", 500, None, str(e))
