import frappe, base64, os
from frappe import _

from one_fm.one_fm.page.face_recognition.face_recognition import update_onboarding_employee
from datetime import timedelta
from one_fm.utils import get_current_shift, is_holiday,get_holiday_today
from one_fm.api.v1.utils import (
    response, verify_via_face_recogniton_service
)
from frappe.utils import add_days, cint, cstr, flt, getdate, now_datetime, strip_html
from one_fm.api.doc_events import haversine
from one_fm.overrides.employee import (
    has_day_off, is_employee_on_leave, NOT_RETURNED_FROM_LEAVE
)

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
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        if not filename:
            filename = frappe.session.user+'.mp4'

        video_file = frappe.request.files.get("video_file") or video or frappe.request.files.get("video")
        endpoint_state = frappe.db.get_single_value("ONEFM General Setting", 'enable_face_recognition_endpoint')
        if not video_file:
            if endpoint_state:
                return response(_("No Video Captured"), 400, None,
                                _("No video was captured. Please record your face again and retry."))

        employee_name = frappe.db.get_value("Employee", {"employee_id": employee_id}, "name")
        if not employee_name:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. Please contact the IT Helpdesk.").format(employee_id))

        # check Face Recognition Endpoint

        if endpoint_state:
            if not face_recog_base_url:
                frappe.log_error(
                    title=f"Mobile API: face_recognition.enroll | {employee_id}",
                    message="face_recognition_service_base_url is not set in site config.",
                )
                frappe.db.commit()
                return response(_("Enrollment Unavailable"), 503, None,
                                _("Face enrollment is temporarily unavailable. Please contact your Site Supervisor."))
            status, message = verify_via_face_recogniton_service(url=face_recog_base_url + "enroll", data={"username": frappe.session.user, "filename": filename}, files={"video_file": video_file})
        else:
            status, message = True, 'Successful'

        if not status:
            return response(_("Enrollment Failed"), 400, None, message)

        doc = frappe.get_doc("Employee", employee_name)

        # Set a context flag to indicate an API update (It will affect in 'Employee' validate method)
        frappe.flags.allow_enrollment_update = True

        doc.db_set('enrolled',1)

        update_onboarding_employee(doc)
        frappe.db.commit()

        return response("Success", 201,
                        _("You are enrolled. You will be taken to check-in shortly."))
    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: face_recognition.enroll | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)


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
        current_shift = shift

        if not employee_id:
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        if not log_type:
            return response(_("Missing Log Type"), 400, None,
                            _("Please select whether you are checking in or out."))

        if log_type not in {"IN", "OUT"}:
            return response(_("Invalid Log Type"), 400, None,
                            _("Please select whether you are checking in or out."))

        if latitude is None or cstr(latitude).strip() == "":
            return response(_("Location Unavailable"), 400, None,
                            _("Your location could not be read. Please enable GPS and try again."))

        if longitude is None or cstr(longitude).strip() == "":
            return response(_("Location Unavailable"), 400, None,
                            _("Your location could not be read. Please enable GPS and try again."))

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return response(_("Location Unavailable"), 400, None,
                            _("Your location could not be read. Please enable GPS and try again."))

        skip_attendance = cint(skip_attendance)

        endpoint_state = frappe.db.get_single_value("ONEFM General Setting", 'enable_face_recognition_endpoint')
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id}, ["name", "custom_enable_face_recognition"], as_dict=1)

        if not employee or not employee.name:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. Please contact the IT Helpdesk.").format(employee_id))

        video_file = frappe.request.files.get("video_file") or video or frappe.request.files.get("video")
        if not video_file:
            if endpoint_state and employee.custom_enable_face_recognition:
                return response(_("No Video Captured"), 400, None,
                                _("No video was captured. Please record your face again and retry."))

        right_now = now_datetime()
        if log_type == "IN":
            ShiftAssignment = frappe.qb.DocType("Shift Assignment")
            ShiftType = frappe.qb.DocType("Shift Type")
            shift_rows = (
                frappe.qb.from_(ShiftAssignment)
                .join(ShiftType)
                .on(ShiftAssignment.shift_type == ShiftType.name)
                .select(
                    ShiftAssignment.start_datetime,
                    ShiftType.begin_check_in_before_shift_start_time,
                )
                .where(ShiftAssignment.employee == employee.name)
                .orderby(ShiftAssignment.creation, order=frappe.qb.desc)
                .limit(1)
            ).run(as_dict=True)

            if not shift_rows:
                return response(_("No Shift Assigned"), 400, None,
                                _("You have no shift assigned. Please contact your Site Supervisor."))

            shift_info = shift_rows[0]
            shift_actual_start = shift_info.start_datetime - timedelta(minutes=cint(shift_info.begin_check_in_before_shift_start_time))
            if right_now < shift_actual_start:
                return response(_("Too Early to Check In"), 400, None,
                                _("You cannot check in yet. Check-in opens {0} minutes before your shift starts, at {1}.").format(
                                    cint(shift_info.begin_check_in_before_shift_start_time), _fmt_clock(shift_actual_start)))
        # check Face Recognition Endpoint

        if not filename:
            filename = frappe.session.user+'.mp4'
        if endpoint_state and employee.custom_enable_face_recognition:
            if not face_recog_base_url:
                frappe.log_error(
                    title=f"Mobile API: face_recognition.verify_checkin_checkout | {employee_id}",
                    message="face_recognition_service_base_url is not set in site config.",
                )
                frappe.db.commit()
                return response(_("Verification Unavailable"), 503, None,
                                _("Face verification is temporarily unavailable. Please contact your Site Supervisor."))
            status, message = verify_via_face_recogniton_service(url=face_recog_base_url + "verify", data={
                "username": frappe.session.user, "filename": filename
                }, files={"video_file": video_file})
        else:
            status, message = True, 'Successful'

        if not status:
            return response(_("Face Verification Failed"), 400, None, message)
        doc = create_checkin_log(employee.name, log_type, skip_attendance, latitude, longitude,current_shift, "Mobile App")
        return response("Success", 201, doc, None)

    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: face_recognition.verify_checkin_checkout | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)


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


def _fmt_clock(value) -> str:
    """A datetime as the banner shows it, e.g. "09:00 AM"."""
    return value.strftime("%I:%M %p").lstrip("0")


def get_checkin_windows(employee: str) -> list:
    """Today's shifts with their check-in boundaries (WI-001777).

    Deliberately separate from ``one_fm.utils.get_current_shift``, whose query only
    returns a shift once its window is already OPEN. Five callers depend on that to
    decide whether a checkin is permitted, so it must not be widened - but a banner
    that says when the next window opens needs to see the whole day.

    Boundaries come from the Shift Type, not from any assumed hour:
      opens_at      = start - begin_check_in_before_shift_start_time
      late_after    = start + late_entry_grace_period   (flagged late, still allowed)
      blocked_after = start + working_hours_threshold_for_absent
    """
    ShiftAssignment = frappe.qb.DocType("Shift Assignment")
    ShiftType = frappe.qb.DocType("Shift Type")

    today = getdate()
    rows = (
        frappe.qb.from_(ShiftAssignment)
        .join(ShiftType)
        .on(ShiftAssignment.shift_type == ShiftType.name)
        .select(
            ShiftAssignment.name,
            ShiftAssignment.start_datetime,
            ShiftAssignment.end_datetime,
            ShiftType.begin_check_in_before_shift_start_time.as_("opens_before"),
            ShiftType.late_entry_grace_period.as_("late_grace"),
            ShiftType.working_hours_threshold_for_absent.as_("absent_after_hours"),
        )
        .where(
            (ShiftAssignment.employee == employee)
            & (ShiftAssignment.status == "Active")
            & (ShiftAssignment.docstatus == 1)
            & (ShiftAssignment.start_datetime >= today)
            & (ShiftAssignment.start_datetime < add_days(today, 1))
        )
        .orderby(ShiftAssignment.start_datetime)
    ).run(as_dict=True)

    windows = []
    for row in rows:
        if not row.start_datetime:
            continue
        windows.append(
            frappe._dict(
                shift_assignment=row.name,
                start=row.start_datetime,
                opens_at=row.start_datetime - timedelta(minutes=cint(row.opens_before)),
                late_after=row.start_datetime + timedelta(minutes=cint(row.late_grace)),
                blocked_after=row.start_datetime
                + timedelta(hours=flt(row.absent_after_hours)),
            )
        )

    return windows


def get_checkin_window_message(employee: str) -> str:
    """Why check-in is unavailable right now, in words an employee can act on.

    Consulted only when no window is open - the path that previously ended at the
    unhelpful "You are not assigned to a shift" regardless of the reason. Returns an
    empty string when the employee genuinely has no shift today, leaving the existing
    day-off/holiday/leave messages to speak.
    """
    windows = get_checkin_windows(employee)
    if not windows:
        return ""

    now = now_datetime()
    closed = [w for w in windows if now > w.blocked_after]
    upcoming = [w for w in windows if now < w.opens_at]

    # Back-to-back shifts: name the one that closed AND when the next one opens, so
    # the employee is not left guessing which shift the message is about.
    if closed and upcoming:
        return _(
            "Check-In Window Closed: Your {0} shift check-in window closed at {1}. "
            "Your next shift check-in opens at {2}. Please contact your Site "
            "Supervisor if you are reporting late."
        ).format(
            _fmt_clock(closed[-1].start),
            _fmt_clock(closed[-1].blocked_after),
            _fmt_clock(upcoming[0].opens_at),
        )

    if closed:
        return _(
            "Check-In Window Closed: Your shift check-in window closed at {0}. "
            "Please contact your Site Supervisor for late check-in authorization."
        ).format(_fmt_clock(closed[-1].blocked_after))

    if upcoming:
        return _(
            "Check-In Unavailable: Your scheduled shift starts at {0}. "
            "Check-in opens at {1}."
        ).format(_fmt_clock(upcoming[0].start), _fmt_clock(upcoming[0].opens_at))

    return ""


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
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        if latitude is None or cstr(latitude).strip() == "":
            return response(_("Location Unavailable"), 400, None,
                            _("Your location could not be read. Please enable GPS and try again."))

        if longitude is None or cstr(longitude).strip() == "":
            return response(_("Location Unavailable"), 400, None,
                            _("Your location could not be read. Please enable GPS and try again."))

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            return response(_("Location Unavailable"), 400, None,
                            _("Your location could not be read. Please enable GPS and try again."))

        employee = frappe.db.get_value("Employee", {"employee_id": employee_id}, ["name", "holiday_list", "employee_name", "shift_working", "status"], as_dict=1)
        if not employee:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. Please contact the IT Helpdesk.").format(employee_id))

        # Block employees who have not returned from leave. This takes priority over
        # every shift check below, so the banner says what to do about the status
        # rather than talking about a check-in window the status makes irrelevant.
        if employee.status == NOT_RETURNED_FROM_LEAVE:
            return response(_("Action Required"), 403, None,
                            _("You are currently marked as '{0}'. Please contact your Site "
                              "Supervisor to complete your Duty Resumption process."
                              ).format(NOT_RETURNED_FROM_LEAVE))
        
        today = getdate()
        
        # check for fingerprint appointment
        fingerprint_appointment = frappe.db.exists("Employee Schedule", {
            "employee": employee.name,
            "date": today,
            "employee_availability": "Fingerprint Appointment"
        })
        if fingerprint_appointment:
            return response(_("Fingerprint Appointment"), 404, None,
                            _("You have a fingerprint appointment scheduled today, so check-in is "
                              "not required. See you soon!"))

        # check for medical appointment
        medical_appointment = frappe.db.exists("Employee Schedule", {
            "employee": employee.name,
            "date": today,
            "employee_availability": "Medical Appointment"
        })
        if medical_appointment:
            return response(_("Medical Appointment"), 404, None,
                            _("You have a medical appointment scheduled today, so check-in is "
                              "not required. See you soon!"))
        shift = frappe.get_doc("Shift Assignment", shift) if shift and shift != 'undefined' else None
        upcoming_shifts = []

        if not shift:
            shift_details = get_current_shift(employee.name, attach_upcoming_shifts=True)
            if shift_details:
                if shift_details['type'] == "Early":
                    # check if user can checkin with the correct time
                    return response(_("Too Early to Check In"), 404, None,
                                    _("It is too early to check in. Check-in opens in {0} minutes.").format(shift_details['time']))
                elif shift_details['type'] == "Late":
                    return response(_("Check-Out Window Closed"), 404, None,
                                    _("The check-out window for your shift closed {0} minutes ago. "
                                      "Please contact your Site Supervisor.").format(shift_details['time']))
                elif shift_details['type'] == "Upcoming":
                    return response(_("Shift Not Started"), 404, None,
                                    _("Check-in for your shift opens in {0} minutes.").format(shift_details['time']))
                elif shift_details['type'] == "On Time":
                    shift = shift_details['data']  # Return the object of Shift Assignment
                    upcoming_shifts = shift_details['upcoming_shifts']

        date = cstr(getdate())

        if shift:
            if shift.is_replaced == 1:
                return response(_("Shift Reassigned"), 404, None,
                                _("Another employee has been assigned to this shift, so you cannot "
                                  "check in. Please contact your Site Supervisor."))

            if is_attendance_request_exists(employee.name, date):
                return response(_("Attendance Request Approved"), 404, None,
                                _("You have an approved attendance request for today. Your attendance "
                                  "will be marked automatically, so no check-in is needed."))

            log_type = shift.get_next_checkin_log_type()
            if log_type == 'IN':
                if shift.after_4hrs():
                    # check if hrs has passed since shift start. Here we can also allow those who checked out tp checkin by checkin if OUT exist for same shift
                    return response(_("Check-In Window Closed"), 404, None,
                                    _("You are more than 4 hours late, so check-in is no longer allowed. "
                                      "Please contact your Site Supervisor to record your attendance."))

            location = get_shift_site_location(shift, date, log_type, latitude, longitude)
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

                # Show the resolved geofence Location as the check-in site name so an
                # approved Shift Request / check-in-site override is reflected. Fall back to
                # the Operations Shift site only when the location has no name.
                result['site_name'] = result.get('name') or site
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

            frappe.log_error(
                title=f"Mobile API: face_recognition.get_site_location | {employee_id}",
                message=(
                    f"No usable Location for shift {shift.name}.\n"
                    f"site={site!r} site_location={shift.get('site_location')!r} "
                    f"operations_shift={shift.get('shift')!r}\n"
                    f"user_latitude={latitude} user_longitude={longitude}"
                ),
            )
            frappe.db.commit()
            return response(_("Site Location Missing"), 404, None,
                            _("Your site location has not been set up yet, so check-in is "
                              "unavailable. Please contact your Site Supervisor."))

        else:
            if employee.shift_working:
                if has_day_off(employee.name, date):
                    return response(_("Day Off"), 404, None,
                                    _("Dear {0}, today is your day off. Happy recharging!").format(employee.employee_name))
            if employee.holiday_list:
                holiday_today = get_holiday_today(str(getdate()))
                if holiday_today.get(employee.holiday_list):
                    return response(_("Holiday"), 404, None,
                                    _("Today is a holiday, so no check-in is needed. Enjoy your day!"))


            if is_employee_on_leave(employee.name, date):
                return response(_("On Leave"), 404, None,
                                _("You are on approved leave today, so no check-in is needed. See you soon!"))

            status, message = is_holiday(employee=employee, date=date)
            if status:
                return response(_("Holiday"), 404, None, message)

            # WI-001777: the employee may well have a shift today whose check-in
            # window is simply not open - get_current_shift only returns a shift once
            # it is. Saying "not assigned to a shift" in that case is both wrong and
            # unactionable, so quote the configured window instead.
            window_message = get_checkin_window_message(employee.name)
            if window_message:
                return response(_("Check-In Unavailable"), 404, None, window_message)

            return response(_("No Shift Assigned"), 404, None,
                            _("You have no shift assigned today. Please contact your Site "
                              "Supervisor if you were expecting to work."))

    except Exception as error:
        frappe.log_error(
            title=f"Mobile API: face_recognition.get_site_location | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(error)) or type(error).__name__)


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


def get_shift_site_location(shift, date, log_type, latitude=None, longitude=None):
    """
        Method to retrieves the site location details (latitude, longitude, and optionally geofence radius)
        for a given shift on a specific date, considering both shift and shift request information.

        Args:
            shift (object): A object of Shift Assignment
            date (str): The date (YYYY-MM-DD format) for which to retrieve the location.
            log_type (str): "IN" or "OUT".
            latitude (float, optional): The user's current latitude for multi-location matching.
            longitude (float, optional): The user's current longitude for multi-location matching.

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
                ["name", "latitude", "longitude", "geofence_radius"],
                as_dict=True
            )
        elif shift.shift:
            # Fetch the site from Operations Shift to get the location of the Site
            site = frappe.get_value("Operations Shift", shift.shift, "site")

            # Check for multi-location support
            multi_locations = frappe.get_all(
                "Operations Site Location Items",
                filters={"parent": site, "parenttype": "Operations Site"},
                fields=["site_location", "disabled"]
            )

            if multi_locations:
                if latitude is None or longitude is None:
                    # Cannot determine proximity without user coordinates;
                    # return the first enabled location as fallback
                    for loc_row in multi_locations:
                        if not loc_row.disabled and loc_row.site_location:
                            return frappe.db.get_value(
                                "Location", loc_row.site_location,
                                ["name", "latitude", "longitude", "geofence_radius"], as_dict=True
                            )
                    return None

                # Multi-location mode: find the first enabled location
                # that contains the user's current position
                for loc_row in multi_locations:
                    if not loc_row.site_location:
                        continue
                    if loc_row.disabled:
                        continue
                    loc_data = frappe.db.get_value(
                        "Location", loc_row.site_location,
                        ["name", "latitude", "longitude", "geofence_radius"], as_dict=True
                    )
                    if not loc_data:
                        continue
                    dist = float(haversine(loc_data.latitude, loc_data.longitude, latitude, longitude))
                    if dist <= float(loc_data.geofence_radius):
                        return loc_data

                # No enabled location matched the user's position
                return None
            else:
                # Single location fallback (legacy): use the site_location field
                # on the Operations Site record directly
                site_location = frappe.db.get_value("Operations Site", site, "site_location")
                if site_location:
                    return frappe.db.get_value(
                        "Location", site_location,
                        ["name", "latitude", "longitude", "geofence_radius"], as_dict=True
                    )
                return None
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
                ["name", "latitude", "longitude", "geofence_radius"],
                as_dict=True
            )
    return None

@frappe.whitelist()
def checkin_list(employee_id, from_date, to_date):
    """
    This method retrives employee checkin list
    """
    try:
        if not employee_id:
            return response(_("Missing Employee ID"), 400, None,
                            _("Please enter your Employee ID."))

        employee = frappe.db.get_value("Employee", {"employee_id":employee_id}, "name")
        if not employee:
            return response(_("Employee Not Found"), 404, None,
                            _("No employee record found for Employee ID {0}. Please contact the IT Helpdesk.").format(employee_id))

        try:
            from_date = getdate(from_date)
            to_date = getdate(to_date)
        except Exception:
            return response(_("Invalid Date Range"), 400, None,
                            _("Please select a valid date range."))

        if from_date > to_date:
            return response(_("Invalid Date Range"), 400, None,
                            _("The start date cannot be after the end date."))

        checkins = frappe.get_all("Employee Checkin", filters={
            "employee": employee,
            "time": ["BETWEEN", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
            },
            fields=["name", "employee_name", "time", "log_type","employee.employee_name_in_arabic"],
            order_by="time DESC"
        )
        return response("success", 200, checkins)
    except Exception as e:
        frappe.log_error(
            title=f"Mobile API: face_recognition.checkin_list | {employee_id}",
            message=frappe.get_traceback(),
        )
        frappe.db.commit()
        return response(_("Something Went Wrong"), 500, None,
                        strip_html(cstr(e)) or type(e).__name__)
