# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import frappe
from frappe import _
import frappe, os
import json
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content_from_uploaded_file, read_csv_content
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, formatdate ,get_url, get_datetime
from datetime import tzinfo, timedelta, datetime
from dateutil import parser
from datetime import date
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
    comma_or, get_fullname, add_years, add_months, add_days, nowdate , comma_and
import datetime


@frappe.whitelist(allow_guest=True)
def paid_sick_leave_validation(doc, method):
    allocation_records = get_leave_allocation_records(nowdate(), doc.employee, "Sick Leave - مرضية")
    allocation_from_date = allocation_records[doc.employee]["Sick Leave - مرضية"].from_date
    allocation_to_date = allocation_records[doc.employee]["Sick Leave - مرضية"].to_date
    
    curr_year_applied_days = get_approved_leaves_for_period(doc.employee, "Sick Leave - مرضية", allocation_from_date, allocation_to_date)

    # curr_total_applied_days = curr_year_applied_days + doc.total_leave_days

    if curr_year_applied_days>0 and curr_year_applied_days<=15:
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
                
    if curr_year_applied_days>15 and curr_year_applied_days<=25:
        remain_three_quarter_paid = curr_year_applied_days-15
        if remain_three_quarter_paid>10:
            remain_three_quarter_paid = 10
            remain_half_paid = (curr_year_applied_days-15)-10
            if remain_half_paid>10:
                remain_half_paid = 10
                remain_quarter_paid = ((curr_year_applied_days-15)-10)-10
                if remain_quarter_paid>10:
                    remain_quarter_paid = 10
                    remain_without_paid = (((curr_year_applied_days-15)-10)-10)-10
                
    if curr_year_applied_days>25 and curr_year_applied_days<=35:
        remain_half_paid = curr_year_applied_days-25
        if remain_half_paid>10:
            remain_half_paid = 10
            remain_quarter_paid = (curr_year_applied_days-25)-10
            if remain_quarter_paid>10:
                remain_quarter_paid = 10
                remain_without_paid = ((curr_year_applied_days-25)-10)-10

    if curr_year_applied_days>35 and curr_year_applied_days<=45:
        remain_quarter_paid = curr_year_applied_days-35
        if remain_quarter_paid>10:
            remain_quarter_paid = 10
            remain_without_paid = (curr_year_applied_days-35)-10
                
    if curr_year_applied_days>45 and curr_year_applied_days<=75:
        remain_without_paid = curr_year_applied_days-45
           


    frappe.msgprint(cstr(allocation_records))
    frappe.msgprint(cstr(curr_year_applied_days))

    # frappe.get_doc({
    #     "doctype":"Additional Salary",
    #     "employee": doc.employee,
    #     "salary_component": 'Sick Leave Deduction',
    #     "payroll_date": doc.from_date,
    #     "amount": 1000
    # }).insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def hooked_leave_allocation_builder():
    emps = frappe.get_all("Employee",filters = {"status": "Active"}, fields = ["name", "date_of_joining"])
    for emp in emps:
        lts = frappe.get_list("Leave Type", fields = ["name"])
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
                    allocation_from_date = year + "-" + month + "-" + day
                    allocation_to_date = add_days(add_years(allocation_from_date,1),-1)

                # if lt.name == "Annual Leave - اجازة اعتيادية":
                #     prev_year_date = frappe.utils.data.add_years(frappe.utils.data.nowdate(), -1)
                #     prev_year_allocation_records = get_leave_allocation_records(prev_year_date, emp.name, "Annual Leave - اجازة اعتيادية")
                #     if prev_year_allocation_records:
                #         from_date = prev_year_allocation_records[emp.name]["Annual Leave - اجازة اعتيادية"].from_date
                #         to_date = prev_year_allocation_records[emp.name]["Annual Leave - اجازة اعتيادية"].to_date
                #         prev_year_total_leaves_allocated = prev_year_allocation_records[emp.name]["Annual Leave - اجازة اعتيادية"].total_leaves_allocated                                
                #         prev_year_applied_days = get_approved_leaves_for_period(emp.name, "Annual Leave - اجازة اعتيادية", from_date, to_date)

                #         if prev_year_total_leaves_allocated == prev_year_applied_days:
                #             new_leaves_allocated = 0
                #         elif prev_year_total_leaves_allocated > prev_year_applied_days:
                #             remain_days = prev_year_total_leaves_allocated - prev_year_applied_days
                #             new_leaves_allocated = remain_days + 0
                #             if new_leaves_allocated > 30:
                #                 new_leaves_allocated = 30
                #     else:
                #         new_leaves_allocated = 0

                    # print('New **Annual Leave - اجازة اعتيادية** for employee {0}'.format(emp.name))

                    # su = frappe.new_doc("Leave Allocation")
                    # su.update({
                    #     "leave_type": "Annual Leave - اجازة اعتيادية",
                    #     "employee": emp.name,
                    #     "from_date": allocation_from_date,
                    #     "to_date": add_years(allocation_to_date,4),
                    #     "new_leaves_allocated": new_leaves_allocated
                    #     })
                    # su.save(ignore_permissions=True)
                    # su.submit()
                    # frappe.db.commit()

                if lt.name == "Sick Leave - مرضية":
                    sl = frappe.new_doc("Leave Allocation")
                    sl.update({
                            "leave_type": "Sick Leave - مرضية",
                            "employee": emp.name,
                            "from_date": allocation_from_date,
                            "to_date": allocation_to_date,
                            "new_leaves_allocated": 75
                            })
                    sl.save(ignore_permissions=True)
                    sl.submit()
                    frappe.db.commit()

                    print('New **Sick Leave - مرضية** for employee {0}'.format(emp.name))



# def increase_daily_leave_balance():
#     emps = frappe.get_all("Employee",filters = {"status": "Active"}, fields = ["name"])
#     for emp in emps:
#         allocation = frappe.db.sql("select name from `tabLeave Allocation` where leave_type='Annual Leave - اجازة اعتيادية' and employee='{0}' and docstatus=1 and '{1}' between from_date and to_date order by to_date desc limit 1".format(emp.name,nowdate()))
#         if allocation:
#             if str(frappe.utils.get_last_day(nowdate())) == str(nowdate()):

#                 doc = frappe.get_doc('Leave Allocation', allocation[0][0])

#                 current_year_applied_days = get_approved_leaves_for_period(emp.name, "Annual Leave - اجازة اعتيادية", doc.from_date, doc.to_date)
#                 current_remain_days = flt(doc.new_leaves_allocated)-flt(current_year_applied_days)

#                 if current_remain_days < 30.0:
#                     if current_remain_days + 2.5 >= 30.0:
#                         leave_balance = current_year_applied_days + 30.0
#                     else:
#                         leave_balance = doc.new_leaves_allocated + 2.5
#                     doc.new_leaves_allocated = leave_balance
#                     doc.save()
#                     print("Increase daily leave balance for employee {0}".format(emp.name))



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

