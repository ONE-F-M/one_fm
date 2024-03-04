import frappe
from one_fm.overrides.attendance_request import AttendanceRequestOverride

def execute() :
    missing_attendances = frappe.db.sql("""
        SELECT ar.name, ar.employee, date_series.missing_date AS missing_date
        FROM `tabAttendance Request` ar
        JOIN (
            SELECT CURDATE() - INTERVAL (a.a + (10 * b.a) + (100 * c.a)) DAY AS missing_date
            FROM (
                SELECT 0 AS a UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
                SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
            ) AS a
            CROSS JOIN (
                SELECT 0 AS a UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
                SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
            ) AS b
            CROSS JOIN (
                SELECT 0 AS a UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL
                SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
            ) AS c
        ) AS date_series
        LEFT JOIN `tabAttendance` a ON ar.employee = a.employee AND DATE(a.attendance_date) = date_series.missing_date
        WHERE ar.workflow_state = 'Approved'
        AND date_series.missing_date BETWEEN ar.from_date AND ar.to_date
        AND date_series.missing_date >= '2023-01-01'
        AND a.name IS NULL
    """, as_dict=True)

    if missing_attendances:
        for att in missing_attendances:
            attendance_request = frappe.get_doc("Attendance Request", att.name)
            mark_wfh(attendance_request, att.missing_date)

def mark_wfh(doc, attendance_date):
    try:
        employee = frappe.get_doc("Employee", doc.employee)
        shift_assignment = AttendanceRequestOverride.get_shift_assignment(doc, attendance_date)
        working_hours = frappe.db.get_value('Shift Type', shift_assignment.shift_type, 'duration')  if shift_assignment  else 8
        # check if attendance exists
        attendance_name = super(AttendanceRequestOverride, doc).get_attendance_record(attendance_date)
        status = "Work From Home"
        if attendance_name:
            # update existing attendance, change the status
            doc = frappe.get_doc("Attendance", attendance_name)
            old_status = doc.status

            if old_status != 'Present':
                doc.db_set({
                    "status": status,
                    "attendance_request": doc.name,
                    "working_hours": working_hours,
                    "reference_doctype":"Attendance Request",
                    "reference_docname":doc.name})
                text = _("Changed the status from {0} to {1} via Attendance Request").format(
                    frappe.bold(old_status), frappe.bold(status)
                )
                doc.add_comment(comment_type="Info", text=text)

                frappe.msgprint(
                    _("Updated status from {0} to {1} for date {2} in the attendance record {3}").format(
                        frappe.bold(old_status),
                        frappe.bold(status),
                        frappe.bold(format_date(attendance_date)),
                        get_link_to_form("Attendance", doc.name),
                    ),
                    title=_("Attendance Updated"),
                )
            elif old_status == 'Present' and status == "Work From Home":
                doc.db_set({
                    "status": status,
                    "attendance_request": doc.name,
                    "working_hours": working_hours,
                    "reference_doctype":"Attendance Request",
                    "reference_docname":doc.name})
                text = _("Changed the status from {0} to {1} via Attendance Request").format(
                    frappe.bold(old_status), frappe.bold(status)
                )
                doc.add_comment(comment_type="Info", text=text)

                frappe.msgprint(
                    _("Updated status from {0} to {1} for date {2} in the attendance record {3}").format(
                        frappe.bold(old_status),
                        frappe.bold(status),
                        frappe.bold(format_date(attendance_date)),
                        get_link_to_form("Attendance", doc.name),
                    ),
                    title=_("Attendance Updated"),
                )
        else:
            attendance = frappe.new_doc("Attendance")
            attendance.employee = doc.employee
            attendance.status = status
            attendance.attendance_date = attendance_date
            attendance.working_hours = working_hours
            attendance.attendance_request = doc.name
            attendance.operations_shift = shift_assignment.shift if shift_assignment else ''
            attendance.roster_type = shift_assignment.roster_type if shift_assignment else ''
            attendance.shift = shift_assignment.shift_type if shift_assignment else ''
            attendance.project = shift_assignment.project if shift_assignment else ''
            attendance.site = shift_assignment.site if shift_assignment else ''
            attendance.operations_role = shift_assignment.operations_role if shift_assignment else ''
            attendance.reference_doctype = "Attendance Request"
            attendance.reference_docname = doc.name
            attendance.save(ignore_permissions=True)
            attendance.submit()
    except Exception as e:
        frappe.log_error(str(frappe.get_traceback()), 'Attendance Request')