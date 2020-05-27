# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
import frappe, os
import json
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content_from_uploaded_file, read_csv_content
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, formatdate ,get_url, get_datetime
from datetime import tzinfo, timedelta, datetime
from dateutil import parser
from datetime import date
from frappe.model.naming import set_name_by_naming_series
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import expire_allocation, create_leave_ledger_entry
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
    comma_or, get_fullname, add_years, add_months, add_days, nowdate,get_first_day,get_last_day, today
import datetime


@frappe.whitelist(allow_guest=True)
def paid_sick_leave_validation(doc, method):
    salary = get_salary(doc.employee)
    daily_rate = salary/30

    allocation_records = get_leave_allocation_records(nowdate(), doc.employee, "Sick Leave - مرضية")
    allocation_from_date = allocation_records[doc.employee]["Sick Leave - مرضية"].from_date
    allocation_to_date = allocation_records[doc.employee]["Sick Leave - مرضية"].to_date

    curr_year_applied_days = get_approved_leaves_for_period(doc.employee, "Sick Leave - مرضية", allocation_from_date, allocation_to_date)

    remain_paid = 0
    remain_three_quarter_paid = 0
    remain_half_paid = 0
    remain_quarter_paid = 0
    remain_without_paid = 0

    if curr_year_applied_days>=0 and curr_year_applied_days<=15:
        remain_paid = 15-curr_year_applied_days
        if doc.total_leave_days > remain_paid:
            remain_three_quarter_paid = doc.total_leave_days-remain_paid
            if remain_three_quarter_paid>10:
                remain_three_quarter_paid = 10
                remain_half_paid = (doc.total_leave_days-remain_paid)-10
                if remain_half_paid>10:
                    remain_half_paid = 10
                    remain_quarter_paid = ((doc.total_leave_days-remain_paid)-10)-10
                    if remain_quarter_paid>10:
                        remain_quarter_paid = 10
                        remain_without_paid = (((doc.total_leave_days-remain_paid)-10)-10)-10

    elif curr_year_applied_days>15 and curr_year_applied_days<=25:
        remain_three_quarter_paid = 25-curr_year_applied_days
        if doc.total_leave_days>remain_three_quarter_paid:
            remain_half_paid = doc.total_leave_days-remain_three_quarter_paid
            if remain_half_paid>10:
                remain_half_paid = 10
                remain_quarter_paid = (doc.total_leave_days-remain_three_quarter_paid)-10
                if remain_quarter_paid>10:
                    remain_quarter_paid = 10
                    remain_without_paid = ((doc.total_leave_days-remain_three_quarter_paid)-10)-10
        else:
            remain_three_quarter_paid = doc.total_leave_days


    elif curr_year_applied_days>25 and curr_year_applied_days<=35:
        remain_half_paid = 35-curr_year_applied_days
        if doc.total_leave_days>remain_half_paid:
            remain_quarter_paid = doc.total_leave_days-remain_half_paid
            if remain_quarter_paid>10:
                remain_quarter_paid = 10
                remain_without_paid = (doc.total_leave_days-remain_half_paid)-10
        else:
            remain_half_paid = doc.total_leave_days


    elif curr_year_applied_days>35 and curr_year_applied_days<=45:
        remain_quarter_paid = 45-curr_year_applied_days
        if doc.total_leave_days>remain_quarter_paid:
            remain_quarter_paid = doc.total_leave_days-remain_quarter_paid
            if remain_quarter_paid>10:
                remain_quarter_paid = 10
                remain_without_paid = (curr_year_applied_days-35)-10

    elif curr_year_applied_days>45 and curr_year_applied_days<=75:
        remain_without_paid = 75-curr_year_applied_days
        if doc.total_leave_days<remain_without_paid:
            remain_without_paid = doc.total_leave_days


    # frappe.msgprint('Year Applied days : '+cstr(curr_year_applied_days))
    # frappe.msgprint('Employee Salary : '+cstr(salary))
    # frappe.msgprint('Daily Rate : '+cstr(daily_rate))
    # frappe.msgprint('Remain Paid : '+cstr(remain_paid))

    # frappe.msgprint('Remain Three Quarter Paid : '+cstr(remain_three_quarter_paid))
    # frappe.msgprint('Remain Half Paid : '+cstr(remain_half_paid))
    # frappe.msgprint('Remain Quarter Paid : '+cstr(remain_quarter_paid))
    # frappe.msgprint('Remain Without Paid : '+cstr(remain_without_paid))

    if remain_three_quarter_paid>0:
        deduction_notes = """
            Employee Salary: <b>{0}</b><br>
            Daily Rate: <b>{1}</b><br>
            Deduction Days Number: <b>{2}</b><br>
            Paid Percent: <b>75%</b>
        """.format(salary,daily_rate,remain_three_quarter_paid)

        frappe.get_doc({
            "doctype":"Additional Salary",
            "employee": doc.employee,
            "docstatus": 1,
            "salary_component": 'Sick Leave Deduction',
            "payroll_date": doc.from_date,
            "leave_application": doc.name,
            "notes": deduction_notes,
            "amount": remain_three_quarter_paid*daily_rate*0.25
        }).insert(ignore_permissions=True)

    if remain_half_paid>0:
        deduction_notes = """
            Employee Salary: <b>{0}</b><br>
            Daily Rate: <b>{1}</b><br>
            Deduction Days Number: <b>{2}</b><br>
            Paid Percent: <b>50%</b>
        """.format(salary,daily_rate,remain_half_paid)

        frappe.get_doc({
            "doctype":"Additional Salary",
            "employee": doc.employee,
            "docstatus": 1,
            "salary_component": 'Sick Leave Deduction',
            "payroll_date": doc.from_date,
            "leave_application": doc.name,
            "notes": deduction_notes,
            "amount": remain_half_paid*daily_rate*0.5
        }).insert(ignore_permissions=True)

    if remain_quarter_paid>0:
        deduction_notes = """
            Employee Salary: <b>{0}</b><br>
            Daily Rate: <b>{1}</b><br>
            Deduction Days Number: <b>{2}</b><br>
            Paid Percent: <b>25%</b>
        """.format(salary,daily_rate,remain_quarter_paid)

        frappe.get_doc({
            "doctype":"Additional Salary",
            "employee": doc.employee,
            "docstatus": 1,
            "salary_component": 'Sick Leave Deduction',
            "payroll_date": doc.from_date,
            "leave_application": doc.name,
            "notes": deduction_notes,
            "amount": remain_quarter_paid*daily_rate*0.75
        }).insert(ignore_permissions=True)

    if remain_without_paid>0:
        deduction_notes = """
            Employee Salary: <b>{0}</b><br>
            Daily Rate: <b>{1}</b><br>
            Deduction Days Number: <b>{2}</b><br>
            Paid Percent: <b>0%</b>
        """.format(salary,daily_rate,remain_without_paid)

        frappe.get_doc({
            "doctype":"Additional Salary",
            "employee": doc.employee,
            "docstatus": 1,
            "salary_component": 'Sick Leave Deduction',
            "payroll_date": doc.from_date,
            "leave_application": doc.name,
            "notes": deduction_notes,
            "amount": remain_without_paid*daily_rate
        }).insert(ignore_permissions=True)



@frappe.whitelist(allow_guest=True)
def bereavement_leave_validation(doc, method):
    allocation = frappe.db.sql("select name from `tabLeave Allocation` where leave_type='Bereavement - وفاة' and employee='{0}' and docstatus=1 and '{1}' between from_date and to_date order by to_date desc limit 1".format(doc.employee, nowdate()))
    if allocation:
        allocation_doc = frappe.get_doc('Leave Allocation', allocation[0][0])
        allocation_doc.new_leaves_allocated = allocation_doc.new_leaves_allocated+doc.total_leave_days
        allocation_doc.total_leaves_allocated = allocation_doc.new_leaves_allocated+allocation_doc.unused_leaves
        allocation_doc.save()
        frappe.db.commit()
        print("Increase Bereavement leave balance for employee {0}".format(doc.employee))

        ledger = frappe._dict(
            doctype='Leave Ledger Entry',
            employee=doc.employee,
            leave_type='Bereavement - وفاة',
            transaction_type='Leave Allocation',
            transaction_name=allocation[0][0],
            leaves = doc.total_leave_days,
            from_date = allocation_doc.from_date,
            to_date = allocation_doc.to_date,
            is_carry_forward=0,
            is_expired=0,
            is_lwp=0
        )
        frappe.get_doc(ledger).submit()




@frappe.whitelist(allow_guest=True)
def update_employee_hajj_status(doc, method):
    if doc.leave_type == 'Hajj leave - حج':
        emp_doc = frappe.get_doc('Employee', doc.employee)
        emp_doc.went_to_hajj = 1
        emp_doc.flags.ignore_mandatory = True
        emp_doc.save()
        frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def validate_hajj_leave(doc, method):
    if doc.leave_type == 'Hajj leave - حج':
        emp_doc = frappe.get_doc('Employee', doc.employee)
        if emp_doc.went_to_hajj:
            frappe.throw("You can't apply for hajj leave twice")


def get_salary(employee):
    salary_amount = 0

    salary_slip_name = frappe.db.sql("select name from `tabSalary Slip` where employee='{0}' order by creation desc limit 1".format(employee))
    if salary_slip_name:
        doc = frappe.get_doc('Salary Slip', salary_slip_name[0][0])

        for earning in doc.earnings:
            if earning.salary_component =='Basic':
                salary_amount = earning.amount

    else:
        doc = frappe.new_doc("Salary Slip")
        doc.payroll_frequency= "Monthly"
        doc.start_date=get_first_day(getdate(nowdate()))
        doc.end_date=get_last_day(getdate(nowdate()))
        doc.employee= str(employee)
        doc.posting_date= nowdate()
        doc.insert(ignore_permissions=True)

        if doc.name:
            for earning in doc.earnings:
                if earning.salary_component =='Basic':
                    salary_amount = earning.amount

            doc.delete()

    return salary_amount



@frappe.whitelist(allow_guest=True)
def hooked_leave_allocation_builder():
    emps = frappe.get_all("Employee",filters = {"status": "Active"}, fields = ["name", "date_of_joining","went_to_hajj"])
    for emp in emps:
        lts = frappe.get_list("Leave Type", fields = ["name","max_leaves_allowed"])
        for lt in lts:
            allocation_records = get_leave_allocation_records(nowdate(), emp.name, lt.name)

            if not allocation_records:
                allocation_from_date = ""
                allocation_to_date = ""
                new_leaves_allocated = 0
                if getdate(add_years(emp.date_of_joining,1)) > getdate(nowdate()):
                    allocation_from_date = emp.date_of_joining
                    allocation_to_date = add_days(add_years(emp.date_of_joining,1),-1)
                else:
                    day = "0" + str(getdate(emp.date_of_joining).day) if len(str(getdate(emp.date_of_joining).day)) == 1 else str(getdate(emp.date_of_joining).day)
                    month = "0" + str(getdate(emp.date_of_joining).month) if len(str(getdate(emp.date_of_joining).month)) == 1 else str(getdate(emp.date_of_joining).month)
                    year = str(getdate(nowdate()).year)

                    if getdate(emp.date_of_joining).month<=getdate(nowdate()).month:
                        if getdate(emp.date_of_joining).day<=getdate(nowdate()).day:
                            year = str(getdate(nowdate()).year)
                        else:
                            year = str(getdate(nowdate()).year-1)
                    else:
                        year = str(getdate(nowdate()).year-1)

                    allocation_from_date = year + "-" + month + "-" + day
                    allocation_to_date = add_days(add_years(allocation_from_date,1),-1)

                if lt.name == "Annual Leave - اجازة اعتيادية":
                    default_annual_leave_balance = frappe.db.get_value('Company', {"name": frappe.defaults.get_user_default("company")}, 'default_annual_leave_balance')
                    new_leaves_allocated = default_annual_leave_balance/365

                    su = frappe.new_doc("Leave Allocation")
                    su.update({
                        "leave_type": "Annual Leave - اجازة اعتيادية",
                        "employee": emp.name,
                        "from_date": allocation_from_date,
                        "to_date": allocation_to_date,
                        "carry_forward": 1,
                        "new_leaves_allocated": new_leaves_allocated
                        })
                    su.save(ignore_permissions=True)
                    su.submit()
                    frappe.db.commit()
                    print('New **Annual Leave - اجازة اعتيادية** for employee {0}'.format(emp.name))

                if lt.name == "Sick Leave - مرضية":
                    sl = frappe.new_doc("Leave Allocation")
                    sl.update({
                            "leave_type": "Sick Leave - مرضية",
                            "employee": emp.name,
                            "from_date": allocation_from_date,
                            "to_date": allocation_to_date,
                            "new_leaves_allocated": lt.max_leaves_allowed  #75
                            })
                    sl.save(ignore_permissions=True)
                    sl.submit()
                    frappe.db.commit()
                    print('New **Sick Leave - مرضية** for employee {0}'.format(emp.name))

                if lt.name == "Hajj leave - حج" and not emp.went_to_hajj:
                    sl = frappe.new_doc("Leave Allocation")
                    sl.update({
                            "leave_type": "Hajj leave - حج",
                            "employee": emp.name,
                            "from_date": allocation_from_date,
                            "to_date": allocation_to_date,
                            "new_leaves_allocated": lt.max_leaves_allowed  #21
                            })
                    sl.save(ignore_permissions=True)
                    sl.submit()
                    frappe.db.commit()
                    print('New **Hajj leave - حج** for employee {0}'.format(emp.name))

                if lt.name == "Bereavement - وفاة":
                    sl = frappe.new_doc("Leave Allocation")
                    sl.update({
                            "leave_type": "Bereavement - وفاة",
                            "employee": emp.name,
                            "from_date": allocation_from_date,
                            "to_date": allocation_to_date,
                            "new_leaves_allocated": lt.max_leaves_allowed  #150
                            })
                    sl.save(ignore_permissions=True)
                    sl.submit()
                    frappe.db.commit()
                    print('New **Bereavement - وفاة** for employee {0}'.format(emp.name))


def increase_daily_leave_balance():
    emps = frappe.get_all("Employee",filters = {"status": "Active"}, fields = ["name","annual_leave_balance"])
    for emp in emps:
        allocation = frappe.db.sql("select name from `tabLeave Allocation` where leave_type='Annual Leave - اجازة اعتيادية' and employee='{0}' and docstatus=1 and '{1}' between from_date and to_date order by to_date desc limit 1".format(emp.name,nowdate()))
        if allocation:
            if emp.annual_leave_balance>0:
                leave_balance = emp.annual_leave_balance/365
            else:
                default_annual_leave_balance = frappe.db.get_value('Company', {"name": frappe.defaults.get_user_default("company")}, 'default_annual_leave_balance')
                leave_balance = default_annual_leave_balance/365

            final_leave_balance = leave_balance

            allocation_records = get_leave_allocation_records(nowdate(), emp.name, 'Sick Leave - مرضية')
            allocation_from_date = allocation_records[emp.name]["Sick Leave - مرضية"].from_date
            allocation_to_date = allocation_records[emp.name]["Sick Leave - مرضية"].to_date

            attendance = frappe.db.sql_list("select attendance_date from `tabAttendance` where docstatus=1 and status='On Leave' and leave_type='Sick Leave - مرضية' and employee='{0}' and attendance_date between '{1}' and '{2}' ".format(emp.name, allocation_from_date, allocation_to_date))

            attendance_until_today = frappe.db.sql("select count(attendance_date) from `tabAttendance` where docstatus=1 and status='On Leave' and leave_type='Sick Leave - مرضية' and employee='{0}' and attendance_date between '{1}' and '{2}' ".format(emp.name, allocation_from_date, getdate(nowdate())))[0][0]

            if getdate(nowdate()) not in attendance:
                attendance_until_today = 0

            if attendance_until_today>=0 and attendance_until_today<=15:
                final_leave_balance = leave_balance
            elif attendance_until_today>15 and attendance_until_today<=25:
                final_leave_balance = leave_balance*0.75
            elif attendance_until_today>25 and attendance_until_today<=35:
                final_leave_balance = leave_balance*0.5
            elif attendance_until_today>35 and attendance_until_today<=45:
                final_leave_balance = leave_balance*0.25
            elif attendance_until_today>45 and attendance_until_today<=75:
                final_leave_balance = leave_balance*0.0

            print(attendance_until_today)
            print('******************************************')
            print(final_leave_balance)

            doc = frappe.get_doc('Leave Allocation', allocation[0][0])
            doc.new_leaves_allocated = doc.new_leaves_allocated+final_leave_balance
            doc.total_leaves_allocated = doc.new_leaves_allocated+doc.unused_leaves
            doc.save()
            frappe.db.commit()
            print("Increase daily leave balance for employee {0}".format(emp.name))

            ledger = frappe._dict(
                doctype='Leave Ledger Entry',
                employee=emp.name,
                leave_type='Annual Leave - اجازة اعتيادية',
                transaction_type='Leave Allocation',
                transaction_name=allocation[0][0],
                leaves = final_leave_balance,
                from_date = allocation_from_date,
                to_date = allocation_to_date,
                is_carry_forward=0,
                is_expired=0,
                is_lwp=0
            )
            frappe.get_doc(ledger).submit()


def get_leave_allocation_records(date, employee=None, leave_type=None):
    conditions = (" and employee='%s'" % employee) if employee else ""
    conditions += (" and leave_type='%s'" % leave_type) if leave_type else ""
    leave_allocation_records = frappe.db.sql("""
        select employee, leave_type, total_leaves_allocated, from_date, to_date
        from `tabLeave Allocation`
        where %s between from_date and to_date and docstatus=1 {0}""".format(conditions), (date), as_dict=1)

    allocated_leaves = frappe._dict()
    for d in leave_allocation_records:
        allocated_leaves.setdefault(d.employee, frappe._dict()).setdefault(d.leave_type, frappe._dict({
            "from_date": d.from_date,
            "to_date": d.to_date,
            "total_leaves_allocated": d.total_leaves_allocated
        }))

    return allocated_leaves


@frappe.whitelist(allow_guest=True)
def get_approved_leaves_for_period(employee, leave_type, from_date, to_date):
    #"
    leave_applications = frappe.db.sql("""
        select name,employee, leave_type, from_date, to_date, total_leave_days
        from `tabLeave Application`
        where employee=%(employee)s and leave_type=%(leave_type)s
            and docstatus=1 and status='Approved'
            and (from_date between %(from_date)s and %(to_date)s
                or to_date between %(from_date)s and %(to_date)s
                or (from_date < %(from_date)s and to_date > %(to_date)s))
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "employee": employee,
        "leave_type": leave_type
    }, as_dict=1)

    leave_days = 0
    for leave_app in leave_applications:
        leave_days += leave_app.total_leave_days

    return leave_days



@frappe.whitelist()
def get_item_code(parent_item_group = None ,subitem_group = None ,item_group = None ,cur_item_id = None):
    item_code = None
    if parent_item_group:
        parent_item_group_code = frappe.db.get_value('Item Group', parent_item_group, 'item_group_code')
        item_code = parent_item_group_code

        if subitem_group:
            subitem_group_code = frappe.db.get_value('Item Group', subitem_group, 'item_group_code')
            item_code = parent_item_group_code+subitem_group_code

            if item_group:
                item_group_code = frappe.db.get_value('Item Group', item_group, 'item_group_code')
                item_code = parent_item_group_code+subitem_group_code+item_group_code

                if cur_item_id:
                    item_code = parent_item_group_code+subitem_group_code+item_group_code+cur_item_id

    return item_code


@frappe.whitelist(allow_guest=True)
def pam_salary_certificate_expiry_date():
    pam_salary_certificate = frappe.db.sql("select name,pam_salary_certificate_expiry_date from `tabPAM Salary Certificate`")
    for pam in pam_salary_certificate:
        date_difference = date_diff(pam[1], getdate(nowdate()))

        page_link = get_url("/desk#Form/PAM Salary Certificate/" + pam[0])
        setting = frappe.get_doc("PAM Salary Certificate Setting")

        if date_difference>0 and date_difference<setting.notification_start and date_difference%setting.notification_period == 0 :
            frappe.get_doc({
                "doctype":"ToDo",
                # "subject": "PAM salary certificate expiry date",
                "description": "PAM Salary Certificate will Expire after {0} day".format(date_difference),
                "reference_type": "PAM Salary Certificate",
                "reference_name": pam[0],
                "owner": 'omar.ja93@gmail.com',
                "date": pam[1]
            }).insert(ignore_permissions=True)

            print("PAM Salary Certificate will Expire after {0} day".format(date_difference))



@frappe.whitelist(allow_guest=True)
def pam_authorized_signatory():
    pam_authorized_signatory = frappe.db.sql("select name,authorized_signatory_expiry_date from `tabPAM Authorized Signatory List`")
    for pam in pam_authorized_signatory:
        date_difference = date_diff(pam[1], getdate(nowdate()))

        page_link = get_url("/desk#Form/PAM Authorized Signatory List/" + pam[0])
        setting = frappe.get_doc("PAM Authorized Signatory Setting")

        if date_difference>0 and date_difference<setting.notification_start and date_difference%setting.notification_period == 0 :
            frappe.get_doc({
                "doctype":"ToDo",
                # "subject": "PAM salary certificate expiry date",
                "description": "PAM Authorized Signatory will Expire after {0} day".format(date_difference),
                "reference_type": "PAM Authorized Signatory List",
                "reference_name": pam[0],
                "owner": 'omar.ja93@gmail.com',
                "date": pam[1]
            }).insert(ignore_permissions=True)

            print("PAM Authorized Signatory will Expire after {0} day".format(date_difference))



@frappe.whitelist(allow_guest=True)
def warehouse_naming_series(doc, method):
    doc.name = doc.warehouse_code+' - '+doc.warehouse_name

@frappe.whitelist(allow_guest=True)
def item_group_naming_series(doc, method):
    doc.name = doc.item_group_code+'-'+doc.item_group_name

@frappe.whitelist(allow_guest=True)
def item_naming_series(doc, method):
    doc.name = doc.item_code



@frappe.whitelist(allow_guest=True)
def validate_get_warehouse_parent(doc, method):
    new_warehouse_code = frappe.db.sql("select warehouse_code+1 from `tabWarehouse` where parent ='{0}' order by warehouse_code desc limit 1".format(doc.parent_warehouse))
    if new_warehouse_code:
        new_warehouse_code_final = new_warehouse_code[0][0]
    else:
        new_warehouse_code_final = '1'

    doc.warehouse_code = str(int(new_warehouse_code_final)).zfill(3)



@frappe.whitelist(allow_guest=True)
def validate_get_item_group_parent(doc, method):
    first_parent = doc.parent_item_group
    second_parent = frappe.db.get_value('Item Group', {"name": first_parent}, 'parent_item_group')

    if first_parent == 'All Item Groups' or second_parent == 'All Item Groups':
        doc.is_group = 1

    new_item_group_code = frappe.db.sql("select item_group_code+1 from `tabItem Group` where parent_item_group ='{0}' order by item_group_code desc limit 1".format(doc.parent_item_group))
    if new_item_group_code:
        new_item_group_code_final = new_item_group_code[0][0]
    else:
        new_item_group_code_final = '1'

    doc.item_group_code = str(int(new_item_group_code_final)).zfill(3)


@frappe.whitelist(allow_guest=True)
def get_item_id_series(parent_item_group, subitem_group, item_group):
    previous_item_id = frappe.db.sql("select item_id from `tabItem` where parent_item_group='{0}' and subitem_group='{1}' and item_group='{2}' order by item_id desc".format(parent_item_group, subitem_group, item_group))
    if previous_item_id:
        return previous_item_id[0][0]
    else:
        return '0000'




def after_insert_job_applicant(doc, method):
    website_user_for_job_applicant(doc.email_id, doc.one_fm_applicant_password, doc.one_fm_first_name, doc.one_fm_last_name)

@frappe.whitelist(allow_guest=True)
def website_user_for_job_applicant(email_id, applicant_password, first_name, last_name=''):
    if not frappe.db.exists ("User", email_id):
        from frappe.utils import random_string
        user = frappe.get_doc({
            "doctype": "User",
            "first_name": first_name,
            "last_name": last_name,
            "email": email_id,
            "user_type": "Website User",
            "send_welcome_email": False
        })
        user.flags.ignore_permissions=True
        # user.reset_password_key=random_string(32)
        user.add_roles("Job Applicant")
        from frappe.utils.password import update_password
        update_password(user=user.name, pwd=applicant_password)
        return user

def validate_job_applicant(doc, method):
    set_job_applicant_fields(doc)
    validate_mandatory_fields(doc)
    set_job_applicant_status(doc, method)
    set_average_score(doc, method)
    if doc.is_new():
        set_childs_for_application_web_form(doc, method)
    if doc.one_fm_applicant_status == "Shortlisted":
        create_job_offer_from_job_applicant(doc.name)

def set_childs_for_application_web_form(doc, method):
    set_required_documents(doc, method)
    set_job_basic_skill(doc, method)
    set_job_languages(doc, method)

def set_job_languages(doc, method):
    if not doc.one_fm_languages:
        job = frappe.get_doc('Job Opening', doc.job_title)
        if job.one_fm_languages:
            set_languages(doc, job.one_fm_languages)
        elif doc.one_fm_erf:
            erf = frappe.get_doc('ERF', doc.one_fm_erf)
            if erf.languages:
                set_languages(doc, erf.languages)

def set_languages(doc, languages):
    for language in languages:
        lang = doc.append('one_fm_languages')
        lang.language = language.language
        lang.language_name = language.language_name
        lang.speak = 0
        lang.read = 0
        lang.write = 0

def set_job_basic_skill(doc, method):
    if not doc.one_fm_designation_skill:
        job = frappe.get_doc('Job Opening', doc.job_title)
        if job.one_fm_designation_skill:
            set_designation_skill(doc, job.one_fm_designation_skill)
        elif doc.one_fm_erf:
            erf = frappe.get_doc('ERF', doc.one_fm_erf)
            if erf.designation_skill:
                set_designation_skill(doc, erf.designation_skill)

def set_designation_skill(doc, skills):
    for designation_skill in skills:
        skill = doc.append('one_fm_designation_skill')
        skill.skill = designation_skill.skill

def set_required_documents(doc, method):
    if doc.one_fm_source_of_hire and not doc.one_fm_documents_required:
        filters = {}
        filters['source_of_hire'] = doc.one_fm_source_of_hire
        if doc.one_fm_source_of_hire == 'Local' and doc.one_fm_visa_type:
            filters['visa_type'] = doc.one_fm_visa_type
        else:
            filters['visa_type'] = ''

        from one_fm.one_fm.doctype.recruitment_document_checklist.recruitment_document_checklist import get_recruitment_document_checklist
        document_checklist_obj = get_recruitment_document_checklist(filters)
        document_checklist = False
        if document_checklist_obj and document_checklist_obj.recruitment_documents:
            document_checklist = document_checklist_obj.recruitment_documents
        if document_checklist:
            for checklist in document_checklist:
                doc_required = doc.append('one_fm_documents_required')
                fields = ['document_required', 'required_when', 'or_required_when', 'type_of_copy', 'or_type_of_copy', 'not_mandatory']
                for field in fields:
                    doc_required.set(field, checklist.get(field))

def set_job_applicant_fields(doc):
    doc.email_id = doc.one_fm_email_id

def validate_mandatory_fields(doc):
    field_list = [{'First Name':'one_fm_first_name'}, {'Last Name':'one_fm_last_name'}, {'Passport Number':'one_fm_passport_number'},
                {'Place of Birth':'one_fm_place_of_birth'}, {'Email ID':'one_fm_email_id'},
                {'Marital Status':'one_fm_marital_status'}, {'Passport Holder of':'one_fm_passport_holder_of'},
                {'Passport Issued on':'one_fm_passport_issued'}, {'Passport Expires on ':'one_fm_passport_expire'},
                {'Gender':'one_fm_gender'}, {'Religion':'one_fm_religion'},
                {'Date of Birth':'one_fm_date_of_birth'}, {'Educational Qualification':'one_fm_educational_qualification'},
                {'University':'one_fm_university'}];
    mandatory_fields = []
    for fields in field_list:
        for field in fields:
            if not doc.get(fields[field]):
                mandatory_fields.append(field)

    if len(mandatory_fields) > 0:
        message = 'Mandatory fields required in Job Applicant<br><br><ul>'
        for mandatory_field in mandatory_fields:
            message += '<li>' + mandatory_field +'</li>'
        message += '</ul>'
        frappe.throw(message)

def set_average_score(doc, method):
    if doc.one_fm_job_applicant_score:
        total = 0
        no_of_interview = 0
        for score in doc.one_fm_job_applicant_score:
            total += score.score
            no_of_interview += 1
        if total > 0 and no_of_interview > 0:
            doc.one_fm_average_interview_score = total/no_of_interview
            if doc.one_fm_applicant_status == 'Draft':
                doc.one_fm_applicant_status = 'Interview'
        if doc.one_fm_career_history_score:
            doc.one_fm_average_score = (total+doc.one_fm_career_history_score)/(no_of_interview+1)

def set_job_applicant_status(doc, method):
    if doc.one_fm_applicant_status != 'Selected':
        if doc.one_fm_documents_required:
            verified = True
            exception = False
            status = 'Verified'
            for document_required in doc.one_fm_documents_required:
                if not document_required.received:
                    if not document_required.exception:
                        status = 'Not Verified'
                    else:
                        status = 'Verified - With Exception'
            doc.one_fm_document_verification = status

def create_job_offer_from_job_applicant(job_applicant):
    if not frappe.db.exists('Job Offer', {'job_applicant': job_applicant, 'docstatus': ['<', 2]}):
        job_app = frappe.get_doc('Job Applicant', job_applicant)
        erf = frappe.get_doc('ERF', job_app.one_fm_erf)
        job_offer = frappe.new_doc('Job Offer')
        job_offer.job_applicant = job_app.name
        job_offer.applicant_name = job_app.applicant_name
        job_offer.offer_date = today()
        set_erf_details(job_offer, erf)
        job_offer.save(ignore_permissions = True)

def set_erf_details(job_offer, erf):
    job_offer.erf = erf.name
    job_offer.designation = erf.designation
    set_salary_details(job_offer, erf)
    set_other_benefits_to_terms(job_offer, erf)

def set_salary_details(job_offer, erf):
    total_amount = 0
    for salary in erf.salary_details:
        total_amount += salary.amount
        salary_details = job_offer.append('one_fm_salary_details')
        salary_details.salary_component = salary.salary_component
        salary_details.amount = salary.amount
    job_offer.one_fm_job_offer_total_salary = total_amount

def set_other_benefits_to_terms(job_offer, erf):
    if erf.other_benefits:
        for benefit in erf.other_benefits:
            terms = job_offer.append('offer_terms')
            terms.offer_term = benefit.benefit
            terms.value = 'Company Provided'
    terms_list = ['Kuwait Visa processing Fees', 'Kuwait Residency Fees', 'Kuwait insurance Fees']
    for term in terms_list:
        terms = job_offer.append('offer_terms')
        terms.offer_term = term
        terms.value = 'Borne By The Company'

    hours = erf.shift_hours if erf.shift_hours else 9
    vacation_days = erf.vacation_days if erf.vacation_days else 30
    terms = job_offer.append('offer_terms')
    terms.offer_term = 'Working Hours'
    terms.value = str(hours)+' hours a day, (Subject to Operational Requirements) from Sunday to Thursday'
    terms = job_offer.append('offer_terms')
    terms.offer_term = 'Annual Leave'
    terms.value = '('+str(vacation_days)+') days paid leave, as per Kuwait Labor Law (Private Sector)'
    terms = job_offer.append('offer_terms')
    terms.offer_term = 'Probation Period'
    terms.value = '(100) working days'

@frappe.whitelist(allow_guest=True)
def get_job_opening(job_opening_id):
    return frappe.get_doc('Job Opening', job_opening_id)

@frappe.whitelist(allow_guest=True)
def get_erf(erf_id):
    return frappe.get_doc('ERF', erf_id)

def get_applicant():
	return frappe.get_value("Job Applicant",{"one_fm_email_id": frappe.session.user}, "name")

def applicant_has_website_permission(doc, ptype, user, verbose=False):
    if doc.name == get_applicant():
        return True
    else:
        return False
