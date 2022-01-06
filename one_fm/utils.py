# -*- coding: utf-8 -*-
# encoding: utf-8
from __future__ import unicode_literals
import itertools
from one_fm.api.notification import create_notification_log
from frappe import _
import frappe, os, erpnext
import json
from frappe.model.document import Document
from frappe.utils import get_site_base_path
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils.csvutils import read_csv_content
from frappe.utils import cint, cstr, flt, rounded,  nowdate, comma_and, date_diff, getdate, formatdate ,get_url, get_datetime, add_to_date, time_diff, get_time, time_diff_in_hours
from datetime import tzinfo, timedelta, datetime
from dateutil import parser
from datetime import date
from frappe.model.naming import set_name_by_naming_series
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import expire_allocation, create_leave_ledger_entry
from dateutil.relativedelta import relativedelta
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
    comma_or, get_fullname, add_years, add_months, add_days, nowdate,get_first_day,get_last_day, today
import datetime
from datetime import datetime, time
from frappe import utils
import pandas as pd
from erpnext.hr.utils import get_holidays_for_employee





def check_upload_original_visa_submission_reminder2():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where upload_original_visa_submitted=0 and upload_original_visa_reminder2_done=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.upload_original_visa_reminder2_done = 0
        pam_visa_doc.upload_original_visa_status = 'No Response'
        pam_visa_doc.upload_original_visa_reminder2 = frappe.utils.now()
        pam_visa_doc.save(ignore_permissions = True)


        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Operator'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder", delayed=False)



def check_upload_original_visa_submission_reminder1():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where upload_original_visa_submitted=0 and upload_original_visa_reminder2_start=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.upload_original_visa_reminder1 = frappe.utils.now()
        pam_visa_doc.upload_original_visa_reminder2_start = 0
        pam_visa_doc.upload_original_visa_reminder2_done = 1
        pam_visa_doc.save(ignore_permissions = True)


        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Operator'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')
        cc = frappe.db.get_single_value('PAM Visa Setting', 'grd_supervisor')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder", cc=cc, delayed=False)





def check_upload_original_visa_submission_daily():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where upload_original_visa_submitted=0 and upload_original_visa_reminder2_start=0 and upload_original_visa_reminder2_done=0 and upload_original_visa_status!='No Response' and pam_visa_approval_submitted=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.upload_original_visa_reminder2_start = 1
        pam_visa_doc.save(ignore_permissions = True)


def check_pam_visa_approval_submission_seven():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where pam_visa_approval_submitted=0 and pam_visa_approval_reminder2_done=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.pam_visa_approval_reminder2_done = 0
        pam_visa_doc.pam_visa_approval_status = 'No Response'
        pam_visa_doc.pam_visa_approval_reminder2 = frappe.utils.now()
        pam_visa_doc.save(ignore_permissions = True)


        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Operator'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder", delayed=False)




def check_pam_visa_approval_submission_six_half():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where pam_visa_approval_submitted=0 and pam_visa_approval_reminder2_start=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.pam_visa_approval_reminder1 = frappe.utils.now()
        pam_visa_doc.pam_visa_approval_reminder2_start = 0
        pam_visa_doc.pam_visa_approval_reminder2_done = 1
        pam_visa_doc.save(ignore_permissions = True)


        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Operator'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')
        cc = frappe.db.get_single_value('PAM Visa Setting', 'grd_supervisor')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder", cc=cc, delayed=False)


def check_pam_visa_approval_submission_daily():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where pam_visa_approval_submitted=0 and pam_visa_approval_reminder2_start=0 and pam_visa_approval_reminder2_done=0 and pam_visa_approval_status!='No Response' and status='Apporved'")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.pam_visa_approval_reminder2_start = 1
        pam_visa_doc.save(ignore_permissions = True)



def check_upload_tasriah_reminder2():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where upload_tasriah_submitted=0 and upload_tasriah_reminder2_done=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.upload_tasriah_reminder2_done = 0
        pam_visa_doc.upload_tasriah_status = 'No Response'
        pam_visa_doc.upload_tasriah_reminder2 = frappe.utils.now()
        pam_visa_doc.save(ignore_permissions = True)

        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Operator'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder", delayed=False)





def check_upload_tasriah_reminder1():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where upload_tasriah_submitted=0 and upload_tasriah_reminder2_start=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.upload_tasriah_reminder1 = frappe.utils.now()
        pam_visa_doc.upload_tasriah_reminder2_start = 0
        pam_visa_doc.upload_tasriah_reminder2_done = 1
        pam_visa_doc.save(ignore_permissions = True)


        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Operator'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')
        cc = frappe.db.get_single_value('PAM Visa Setting', 'grd_supervisor')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder", cc=cc, delayed=False)





def check_upload_tasriah_submission_nine():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where pam_visa_submitted_supervisor=1 and upload_tasriah_submitted=0 and upload_tasriah_reminder2_start=0 and upload_tasriah_reminder2_done=0 and upload_tasriah_status!='No Response'")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)

        after_two_days = add_days(pam_visa_doc.pam_visa_reminder_supervisor, 2)

        get_defferent = date_diff(frappe.utils.now(), after_two_days)

        if get_defferent>=0:
            pam_visa_doc.upload_tasriah_reminder2_start = 1
            pam_visa_doc.save(ignore_permissions = True)





def check_grp_supervisor_submission_daily():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where pam_visa_submitted=1 and pam_visa_submitted_supervisor=0")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.pam_visa_reminder_supervisor = frappe.utils.now()
        pam_visa_doc.save(ignore_permissions = True)

        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Supervisor'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_supervisor')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder", delayed=False)


def check_grp_operator_submission_four_half():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where pam_visa_submitted=0 and pam_visa_reminder2_done=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.pam_visa_reminder2_done = 0
        pam_visa_doc.grd_operator_status = 'No Response'
        pam_visa_doc.pam_visa_reminder2 = frappe.utils.now()
        pam_visa_doc.save(ignore_permissions = True)


        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Operator'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')
        cc = frappe.db.get_single_value('PAM Visa Setting', 'grd_supervisor')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder",cc=cc, delayed=False)



def check_grp_operator_submission_four():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where pam_visa_submitted=0 and pam_visa_reminder2_start=1")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.pam_visa_reminder1 = frappe.utils.now()
        pam_visa_doc.pam_visa_reminder2_start = 0
        pam_visa_doc.pam_visa_reminder2_done = 1
        pam_visa_doc.save(ignore_permissions = True)


        page_link = "http://206.189.228.82/desk#Form/PAM Visa/" + cstr(pam_visa)
        # page_link = get_url("/desk#Form/PAM Visa/" + doc.name)
        msg = frappe.render_template('one_fm/templates/emails/pam_visa.html', context={"page_link": page_link, "approval": 'Operator'})
        sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
        recipient = frappe.db.get_single_value('PAM Visa Setting', 'grd_operator')

        frappe.sendmail(sender=sender, recipients= recipient,
            content=msg, subject="PAM Visa Reminder", delayed=False)




def check_grp_operator_submission_daily():
    pam_visas = frappe.db.sql_list("select name from `tabPAM Visa` where pam_visa_submitted=0 and pam_visa_reminder2_start=0 and pam_visa_reminder2_done=0 and grd_operator_status!='No Response'")

    for pam_visa in pam_visas:
        pam_visa_doc = frappe.get_doc("PAM Visa", pam_visa)
        pam_visa_doc.pam_visa_reminder2_start = 1
        pam_visa_doc.save(ignore_permissions = True)

def send_gp_letter_attachment_reminder2():
    gp_letters_request = frappe.db.sql_list("select DISTINCT gp_letter_request_reference from `tabGP Letter` where (gp_letter_attachment is NULL or gp_letter_attachment='' ) ")

    for gp_letter_request in gp_letters_request:
        gp_letter_doc = frappe.get_doc("GP Letter Request", gp_letter_request)
        if gp_letter_doc.upload_reminder1 and not gp_letter_doc.upload_reminder2:
            after_three_days = add_days(gp_letter_doc.upload_reminder1, 3)

            get_defferent = date_diff(getdate(nowdate()), after_three_days)
            # if get_datetime(frappe.utils.now())>=get_datetime(after_three_days):

            if get_defferent>=0:

                grd_name = frappe.db.get_single_value('GP Letter Request Setting', 'grd_name')
                grd_number = frappe.db.get_single_value('GP Letter Request Setting', 'grd_number')

                msg = frappe.render_template('one_fm/templates/emails/gp_letter_attachment_reminder.html', context={"candidates": gp_letter_doc.gp_letter_candidates, "grd_name": grd_name, "grd_number": grd_number})
                sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
                recipient = frappe.db.get_single_value('GP Letter Request Setting', 'travel_agent_email')
                cc = frappe.db.get_single_value('GP Letter Request Setting', 'grd_email')

                frappe.sendmail(sender=sender, recipients= recipient,
                    content=msg, subject="GP Letter Upload Reminder" ,cc=cc, delayed=False)

                gp_letter_doc.upload_reminder2 = frappe.utils.now()
                gp_letter_doc.save(ignore_permissions = True)


def send_gp_letter_attachment_reminder3():
    gp_letters_request = frappe.db.sql_list("select DISTINCT gp_letter_request_reference from `tabGP Letter` where (gp_letter_attachment is NULL or gp_letter_attachment='' ) ")

    for gp_letter_request in gp_letters_request:
        gp_letter_doc = frappe.get_doc("GP Letter Request", gp_letter_request)
        if gp_letter_doc.upload_reminder2 and not gp_letter_doc.upload_reminder3:

            after_four_hour = add_to_date(gp_letter_doc.upload_reminder2, hours=4)

            if get_datetime(frappe.utils.now())>=get_datetime(after_four_hour):

                grd_name = frappe.db.get_single_value('GP Letter Request Setting', 'grd_name')
                grd_number = frappe.db.get_single_value('GP Letter Request Setting', 'grd_number')

                msg = frappe.render_template('one_fm/templates/emails/gp_letter_attachment_reminder.html', context={"candidates": gp_letter_doc.gp_letter_candidates, "grd_name": grd_name, "grd_number": grd_number})
                sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
                recipient = frappe.db.get_single_value('GP Letter Request Setting', 'travel_agent_email')
                cc = frappe.db.get_single_value('GP Letter Request Setting', 'grd_email')

                frappe.sendmail(sender=sender, recipients= recipient,
                    content=msg, subject="GP Letter Upload Reminder" ,cc=cc, delayed=False)

                gp_letter_doc.upload_reminder3 = frappe.utils.now()
                gp_letter_doc.save(ignore_permissions = True)


def send_gp_letter_attachment_no_response():
    gp_letters_request = frappe.db.sql_list("select DISTINCT gp_letter_request_reference from `tabGP Letter` where (gp_letter_attachment is NULL or gp_letter_attachment='' ) ")

    for gp_letter_request in gp_letters_request:
        gp_letter_doc = frappe.get_doc("GP Letter Request", gp_letter_request)
        if gp_letter_doc.upload_reminder3 and not gp_letter_doc.upload_reminder4:

            gp_letter_doc.upload_reminder4 = frappe.utils.now()
            gp_letter_doc.save(ignore_permissions = True)

            page_link = "http://206.189.228.82/desk#Form/GP Letter Request/" + gp_letter_request
            # page_link = get_url("/desk#Form/GP Letter Request/" + gp_letter_request)
            msg = frappe.render_template('one_fm/templates/emails/gp_letter_attachment_no_response.html', context={"page_link": page_link, "gp_letter_request": gp_letter_request})
            sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
            recipient = frappe.db.get_single_value('GP Letter Request Setting', 'grd_email')
            frappe.sendmail(sender=sender, recipients= recipient,
                content=msg, subject="GP Letter Upload No Response", delayed=False)

def send_travel_agent_email():
    gp_letters_request = frappe.db.sql_list("select name from `tabGP Letter Request` where (gp_status is NULL or gp_status='' or gp_status='Reject') and (supplier is not NULL or supplier!='') ")

    for gp_letter_request in gp_letters_request:
        gp_letter_doc = frappe.get_doc("GP Letter Request", gp_letter_request)
        if gp_letter_doc.gp_status!='No Response':
            if not gp_letter_doc.sent_date:
                send_gp_email(gp_letter_doc.pid, gp_letter_doc.gp_letter_candidates, gp_letter_request)

                gp_letter_doc.sent_date = frappe.utils.now()
                gp_letter_doc.save(ignore_permissions = True)
            # elif not gp_letter_doc.reminder1:
            #     send_gp_email(gp_letter_doc.pid, gp_letter_doc.gp_letter_candidates, gp_letter_request)

            #     gp_letter_doc.reminder1 = frappe.utils.now()
            #     gp_letter_doc.save(ignore_permissions = True)
            # elif not gp_letter_doc.reminder2:
            #     send_gp_email(gp_letter_doc.pid, gp_letter_doc.gp_letter_candidates, gp_letter_request)

            #     gp_letter_doc.reminder2 = frappe.utils.now()
            #     gp_letter_doc.save(ignore_permissions = True)
            # else:

            #     gp_letter_doc.gp_status = 'No Response'
            #     gp_letter_doc.save(ignore_permissions = True)

            #     page_link = "http://206.189.228.82/desk#Form/GP Letter Request/" + gp_letter_request
            #     # page_link = get_url("/desk#Form/GP Letter Request/" + gp_letter_request)
            #     msg = frappe.render_template('one_fm/templates/emails/gp_letter_request_no_response.html', context={"page_link": page_link, "gp_letter_request": gp_letter_request})
            #     sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
            #     recipient = frappe.db.get_single_value('GP Letter Request Setting', 'grd_email')
            #     frappe.sendmail(sender=sender, recipients= recipient,
            #         content=msg, subject="GP Letter Request No Response", delayed=False)

def send_gp_letter_reminder():
    gp_letters_request = frappe.db.sql_list("select name from `tabGP Letter Request` where (gp_status is NULL or gp_status='' or gp_status='Reject') and (supplier is not NULL or supplier!='') ")

    for gp_letter_request in gp_letters_request:
        gp_letter_doc = frappe.get_doc("GP Letter Request", gp_letter_request)
        if gp_letter_doc.gp_status!='No Response':
            if gp_letter_doc.sent_date and not gp_letter_doc.reminder1:
                after_three_hour = add_to_date(gp_letter_doc.sent_date, hours=3)
                if get_datetime(frappe.utils.now())>=get_datetime(after_three_hour):
                    send_gp_email(gp_letter_doc.pid, gp_letter_doc.gp_letter_candidates, gp_letter_request)

                    gp_letter_doc.reminder1 = frappe.utils.now()
                    gp_letter_doc.save(ignore_permissions = True)
            if gp_letter_doc.reminder1 and not gp_letter_doc.reminder2:
                after_three_hour = add_to_date(gp_letter_doc.reminder1, hours=3)
                if get_datetime(frappe.utils.now())>=get_datetime(after_three_hour):
                    send_gp_email(gp_letter_doc.pid, gp_letter_doc.gp_letter_candidates, gp_letter_request)

                    gp_letter_doc.reminder2 = frappe.utils.now()
                    gp_letter_doc.save(ignore_permissions = True)
            if gp_letter_doc.reminder2:
                after_three_hour = add_to_date(gp_letter_doc.reminder2, hours=3)
                if get_datetime(frappe.utils.now())>=get_datetime(after_three_hour):
                    send_gp_email(gp_letter_doc.pid, gp_letter_doc.gp_letter_candidates, gp_letter_request)

                    gp_letter_doc.gp_status = 'No Response'
                    gp_letter_doc.save(ignore_permissions = True)

                    page_link = "http://206.189.228.82/desk#Form/GP Letter Request/" + gp_letter_request
                    # page_link = get_url("/desk#Form/GP Letter Request/" + gp_letter_request)
                    msg = frappe.render_template('one_fm/templates/emails/gp_letter_request_no_response.html', context={"page_link": page_link, "gp_letter_request": gp_letter_request})
                    sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
                    recipient = frappe.db.get_single_value('GP Letter Request Setting', 'grd_email')
                    frappe.sendmail(sender=sender, recipients= recipient,
                        content=msg, subject="GP Letter Request No Response", delayed=False)





def send_gp_email(pid, candidates, gp_letter_request):
    gp_letter_doc = frappe.get_doc("GP Letter Request", gp_letter_request)
    page_link = "http://206.189.228.82/gp_letter_request?pid=" + pid
    # page_link = get_url("/gp_letter_request?pid=" + pid)
    msg = frappe.render_template('one_fm/templates/emails/gp_letter_request.html', context={"page_link": page_link, "candidates": candidates})
    sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None
    recipient = frappe.db.get_single_value('GP Letter Request Setting', 'grd_email')

    # my_attachments = [frappe.attach_print('GP Letter Request', gp_letter_request, file_name=gp_letter_doc.excel_sheet_attachment)]

    site_name = cstr(frappe.local.site)
    path = "/home/frappe/frappe-bench/sites/{0}/public/files/{1}.xlsx".format(site_name, gp_letter_request)

    with open(path, "rb") as fileobj:
        filedata = fileobj.read()

    attachments = [{
        'fname': cstr(gp_letter_request)+'.xlsx',
        'fcontent': filedata
    }]

    frappe.sendmail(sender=sender, recipients= recipient,
        content=msg, subject="Request for GP Letter | {0}".format(gp_letter_request), attachments=attachments ,delayed=False)


def create_gp_letter_request():
    gp_letters = frappe.db.sql_list("select name from `tabGP Letter` where gp_letter_request_reference is NULL or gp_letter_request_reference='' ")
    candidates=[]

    for gp_letter in gp_letters:
        # gp_letter_doc = frappe.get_doc("GP Letter", gp_letter)

        # candidates.append(gp_letter_doc.candidate_name)
        candidates.append(gp_letter)

    if len(candidates)>0:
        supplier_category_val = ''
        supplier_subcategory_val = ''
        supplier_name_val = ''

        services_item_group = frappe.db.sql("select name from `tabItem Group` where parent_item_group='All Item Groups' and item_group_name like '%Services%' ")
        if services_item_group:
            supplier_category_val = services_item_group[0][0]

            travel_agent_group = frappe.db.sql("select name from `tabItem Group` where parent_item_group='{0}' and item_group_name like '%Travel Agent%' ".format(supplier_category_val))
            if travel_agent_group:
                supplier_subcategory_val = travel_agent_group[0][0]

        supplier = frappe.db.get_single_value('GP Letter Request Setting', 'default_supplier')
        if supplier:
            supplier_name_val = supplier

        doc = frappe.new_doc('GP Letter Request')
        for candidate in candidates:
            gp_letter_doc = frappe.get_doc("GP Letter", candidate)

            doc.append("gp_letter_candidates",{
                "gp_letter": candidate,
                "candidate": gp_letter_doc.candidate_name,
            })


        doc.supplier_category = supplier_category_val
        doc.supplier_subcategory = supplier_subcategory_val
        doc.supplier = supplier_name_val
        doc.save(ignore_permissions = True)

        site_name = cstr(frappe.local.site)

        import xlsxwriter
        workbook = xlsxwriter.Workbook('/home/frappe/frappe-bench/sites/{0}/public/files/{1}.xlsx'.format(site_name, doc.name))
        worksheet = workbook.add_worksheet()
        worksheet.write('A1', 'Sr.No')
        worksheet.write('B1', 'Candidate Name In English')
        worksheet.write('C1', 'Candidate Name In Arabic')
        worksheet.write('D1', 'Passport Number')
        worksheet.write('E1', 'Candidate Nationality in Arabic')
        worksheet.write('F1', 'Company Name in Arabic')
        worksheet.set_column('B:F', 22)


        gp_letter_request_doc = frappe.get_doc("GP Letter Request", doc.name)

        row = 1
        column = 0
        for candidate in gp_letter_request_doc.gp_letter_candidates:
            worksheet.write(row, column, candidate.idx)
            worksheet.write(row, column+1, candidate.candidate)
            # column += 1
            row += 1
        workbook.close()

        gp_letter_request_doc.excel_sheet_attachment = "/files/{0}.xlsx".format(doc.name)
        gp_letter_request_doc.save(ignore_permissions = True)


        for gp_letter in gp_letters:
            gp_letter_doc = frappe.get_doc("GP Letter", gp_letter)
            gp_letter_doc.gp_letter_request_reference = doc.name
            gp_letter_doc.save(ignore_permissions = True)



@frappe.whitelist(allow_guest=True)
def leave_appillication_on_submit(doc, method):
    if doc.status == "Approved":
        leave_appillication_paid_sick_leave(doc, method)
        update_employee_hajj_status(doc, method)

@frappe.whitelist(allow_guest=True)
def leave_appillication_on_cancel(doc, method):
    update_employee_hajj_status(doc, method)

@frappe.whitelist(allow_guest=True)
def leave_appillication_paid_sick_leave(doc, method):
    if doc.leave_type and frappe.db.get_value("Leave Type", doc.leave_type, 'one_fm_is_paid_sick_leave') == 1:
        create_additional_salary_for_paid_sick_leave(doc)

def create_additional_salary_for_paid_sick_leave(doc):
    salary = get_salary(doc.employee)
    daily_rate = salary/30
    from erpnext.hr.doctype.leave_application.leave_application import get_leave_details
    leave_details = get_leave_details(doc.employee, nowdate())
    curr_year_applied_days = 0
    if doc.leave_type in leave_details['leave_allocation'] and leave_details['leave_allocation'][doc.leave_type]:
        curr_year_applied_days = leave_details['leave_allocation'][doc.leave_type]['leaves_taken']
    if curr_year_applied_days == 0:
        curr_year_applied_days = doc.total_leave_days

    leave_payment_breakdown = get_leave_payment_breakdown(doc.leave_type)

    total_payment_days = 0
    if leave_payment_breakdown:
        threshold_days = 0
        for payment_breakdown in leave_payment_breakdown:
            payment_days = 0
            threshold_days += payment_breakdown.threshold_days
            if total_payment_days < doc.total_leave_days:
                if curr_year_applied_days >= threshold_days and (curr_year_applied_days - doc.total_leave_days) < threshold_days:
                    payment_days = threshold_days - (curr_year_applied_days-doc.total_leave_days) - total_payment_days
                elif curr_year_applied_days <= threshold_days: # Gives true this also doc.total_leave_days <= threshold_days:
                    payment_days = doc.total_leave_days - total_payment_days
                create_additional_salary(salary, daily_rate, payment_days, doc, payment_breakdown)
                total_payment_days += payment_days

    if total_payment_days < doc.total_leave_days and doc.total_leave_days-total_payment_days > 0:
        create_additional_salary(salary, daily_rate, doc.total_leave_days-total_payment_days, doc)

def create_additional_salary(salary, daily_rate, payment_days, leave_application, payment_breakdown=False):
    if payment_days > 0:
        deduction_percentage = 1
        salary_component = frappe.db.get_value("Leave Type", leave_application.leave_type, "one_fm_paid_sick_leave_deduction_salary_component")
        if payment_breakdown:
            deduction_percentage = payment_breakdown.salary_deduction_percentage/100
            salary_component = payment_breakdown.salary_component
        deduction_notes = """
            Employee Salary: <b>{0}</b><br>
            Daily Rate: <b>{1}</b><br>
            Deduction Days Number: <b>{2}</b><br>
            Deduction Percent: <b>{3}%</b>
        """.format(salary, daily_rate, payment_days, deduction_percentage*100)

        additional_salary = frappe.get_doc({
            "doctype":"Additional Salary",
            "employee": leave_application.employee,
            "salary_component": salary_component,
            "payroll_date": leave_application.from_date,
            "leave_application": leave_application.name,
            "notes": deduction_notes,
            "amount": payment_days*daily_rate*deduction_percentage
        }).insert(ignore_permissions=True)
        additional_salary.submit()

def get_leave_payment_breakdown(leave_type):
    leave_type_doc = frappe.get_doc("Leave Type", leave_type)
    return leave_type_doc.one_fm_leave_payment_breakdown if leave_type_doc.one_fm_leave_payment_breakdown else False

def validate_leave_type_for_one_fm_paid_leave(doc, method):
    if doc.is_lwp:
        doc.one_fm_is_paid_sick_leave = False
        doc.one_fm_is_paid_annual_leave = False
    elif doc.one_fm_is_paid_sick_leave:
        doc.is_lwp = False
        doc.one_fm_is_paid_annual_leave = False
        doc.one_fm_is_hajj_leave = False
        if not doc.one_fm_paid_sick_leave_deduction_salary_component and not doc.one_fm_leave_payment_breakdown:
            frappe.throw(_('Either Paid Sick Leave Deduction Salary Component or Leave Payment Breakdown is Mandatory'))
    elif doc.one_fm_is_paid_annual_leave:
        doc.is_lwp = False
        doc.one_fm_is_paid_sick_leave = False
        doc.one_fm_is_hajj_leave = False
        # if not doc.one_fm_annual_leave_allocation_reduction:
        #     frappe.throw(_('Annual Leave Allocation Reduction is Mandatory'))
        if not doc.leave_allocation_matrix:
            frappe.throw(_('Leave Allocation Matrix is Mandatory'))
    elif doc.one_fm_is_hajj_leave:
        doc.one_fm_is_paid_annual_leave = False
        doc.one_fm_is_hajj_leave = False

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
    if doc.leave_type and frappe.db.get_value('Leave Type', doc.leave_type, 'one_fm_is_hajj_leave') == 1:
        if method == "on_submit":
            frappe.db.set_value("Employee", doc.employee, 'went_to_hajj', True)
        if method == "on_cancel":
            frappe.db.set_value("Employee", doc.employee, 'went_to_hajj', False)

@frappe.whitelist(allow_guest=True)
def validate_hajj_leave(doc, method):
    if doc.leave_type and frappe.db.get_value('Leave Type', doc.leave_type, 'one_fm_is_hajj_leave') == 1:
        if frappe.db.get_value('Employee', doc.employee, 'went_to_hajj') == 1:
            frappe.throw(_("You can't apply for hajj leave twice"))

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

@frappe.whitelist()
def hooked_leave_allocation_builder():
    '''
        Function used to create leave allocations
         - Create Leave Allocation for Employee, who is having a valid leave policy
        Triggered from hooks as daily event
    '''
    # Get Active Employee List and set background job to create leave allocations based on the leave policy
    employee_list = frappe.get_all("Employee", filters={"status": "Active"},
        fields=["name", "date_of_joining", "went_to_hajj", "grade", "leave_policy"])
    frappe.enqueue(leave_allocation_builder, timeout=600, employee_list=employee_list)

def leave_allocation_builder(employee_list):
    '''
        Function used to create leave allocations for a given employee list
         - Create Leave Allocation for Employee, who is having a valid leave policy
        args:
            employee_list: List of Employees with minimum data (name, date_of_joining, went_to_hajj, grade and leave_policy)
    '''
    from erpnext.hr.doctype.leave_allocation.leave_allocation import get_leave_allocation_for_period

    # Get Leave Type details (configurations)
    leave_type_details = get_leave_type_details()

    # Iterate Employee List for finidng employee leave policy to create leave allocation
    for employee in employee_list:
        # Get employee Leave Policy Object
        leave_policy = get_employee_leave_policy(employee)

        # Check leave policy and details exists
        if leave_policy and leave_policy.leave_policy_details:

            # Iterate Leave policy details to check if there any Leave Allocation exists, if not then create leave allocation
            for policy_detail in leave_policy.leave_policy_details:
                # Find from_date and to_date to get leave allocation for the current period
                if getdate(add_years(employee.date_of_joining, 1)) > getdate(nowdate()):
                    '''
                        If date of joining + 1 year greater than today, then from_date will be joining date.
                    '''
                    from_date = getdate(employee.date_of_joining)
                else:
                    '''
                        Else, from_date will be sum of joining date and difference in years
                            between the date of joining and today
                    '''
                    datetime1 = get_datetime(getdate(employee.date_of_joining))
                    datetime2 = get_datetime(getdate(nowdate()))

                    time_difference = relativedelta(datetime2, datetime1)
                    difference_in_years = time_difference.years
                    from_date = getdate(add_years(employee.date_of_joining, difference_in_years))

                # to_date is an year of addition to the from date
                to_date = getdate(add_days(add_years(from_date, 1), -1))

                # Check allocation exists for leave type in leave Policy, If not then create leave allocation
                leave_allocated = get_leave_allocation_for_period(employee.name, policy_detail.leave_type, from_date, to_date)
                if not leave_allocated and not (leave_type_details.get(policy_detail.leave_type).is_lwp):
                    create_leave_allocation(employee, policy_detail, leave_type_details, from_date, to_date)

def get_employee_leave_policy(employee):
    '''
        Function used to get leave policy for an employee
        args:
            employee: Object of Employee
        return:
            leave policy Object or False(Boolean)
    '''
    leave_policy = employee.leave_policy
    if not leave_policy and employee.grade:
        '''
            If no leave policy configured in employee and grade is configured in employee,
            get leave policy configured in Employee Grade
        '''
        leave_policy = frappe.db.get_value("Employee Grade", employee.grade, "default_leave_policy")
    if leave_policy:
        return frappe.get_doc("Leave Policy", leave_policy)
    return False

def get_leave_type_details():
    '''
        Function used to get existing leave type details
        return:
            Details of All leave type as dict
    '''
    leave_type_details = frappe._dict()
    leave_types = frappe.get_all("Leave Type",
        fields=["name", "is_lwp", "is_earned_leave", "is_compensatory", "is_carry_forward", "expire_carry_forwarded_leaves_after_days", "one_fm_is_hajj_leave", "one_fm_is_paid_sick_leave", "one_fm_is_paid_annual_leave"])
    for d in leave_types:
        leave_type_details.setdefault(d.name, d)
    return leave_type_details

def create_leave_allocation(employee, policy_detail, leave_type_details, from_date, to_date):
    ''' Creates leave allocation for the given employee in the provided leave policy '''
    leave_type = policy_detail.leave_type
    new_leaves_allocated = policy_detail.annual_allocation
    carry_forward = 0
    if leave_type_details.get(leave_type).is_carry_forward:
        carry_forward = 1

    # Earned Leaves and Compensatory Leaves are allocated by scheduler, initially allocate 0
    if leave_type_details.get(leave_type).is_earned_leave == 1 or leave_type_details.get(leave_type).is_compensatory == 1:
        new_leaves_allocated = 0

    # Annual Leave allocated by scheduler, initially allocate 0
    if leave_type_details.get(leave_type).one_fm_is_paid_annual_leave == 1:
        default_annual_leave_balance = frappe.db.get_value('Company', {"name": frappe.defaults.get_user_default("company")}, 'default_annual_leave_balance')
        new_leaves_allocated = default_annual_leave_balance/365

    allocate_leave = True
    # Hajj Leave is allocated for employees who do not perform hajj before
    if leave_type_details.get(leave_type).one_fm_is_hajj_leave == 1 and employee.went_to_hajj:
        allocate_leave = False

    if allocate_leave:
        allocation = frappe.get_doc(dict(
            doctype="Leave Allocation",
            employee=employee.name,
            leave_type=leave_type,
            from_date=from_date,
            to_date=to_date,
            new_leaves_allocated=new_leaves_allocated,
            carry_forward=carry_forward
        ))
        allocation.save(ignore_permissions = True)
        allocation.submit()

def increase_daily_leave_balance():
    '''
        Function is used to Increase daily leave balance for Annual Leave Allocation
        Triggered from daily scheduler event in hooks
        Annual Leave Allocation:
            It is the Leave Allocation for every employee with a leave type marked true for `Is Paid Annual Leave`
    '''

    # Get List of Leave Allocation for today of a Leave Type (having Is Paid Annual Leave marekd True)
    allocation_list = get_paid_annual_leave_allocation_list()

    # Iterate Allocation List to increment Allocation
    for leave_allocation in allocation_list:
        # Get Allocation object from allocation list
        allocation = frappe.get_doc("Leave Allocation", leave_allocation.name)

        # Get Leave Type object from allocation list
        leave_type = frappe.get_doc("Leave Type", leave_allocation.leave_type)

        # If True, then calculate new_leaves_allocated and update to the Leave Allocation
        if is_employee_allowed_to_avail_increment_existing_allocation(allocation, leave_type):
            # Get Number of Leave Allocated for the allocation of an employee
            new_leaves_allocated = get_new_leave_allocated_for_annual_paid_leave(allocation, leave_type)
            if new_leaves_allocated:
                allocation.new_leaves_allocated = allocation.new_leaves_allocated+new_leaves_allocated
                allocation.total_leaves_allocated = allocation.new_leaves_allocated+allocation.unused_leaves
                allocation.save()
                # Update Leave Ledger to reflect the Leave Allocation
                update_leave_ledger_for_paid_annual_leave(allocation, leave_type.is_carry_forward)

def update_leave_ledger_for_paid_annual_leave(allocation, is_carry_forward):
    '''
        Function is used to Update Leave Ledger Entry for Annual Leave Allocation
        args:
            allocation: Object of Leave Allocation
            is_carry_forward: Boolean
    '''
    # Delete old ledger entry
    frappe.db.sql("""DELETE FROM `tabLeave Ledger Entry`
        WHERE `transaction_name`=%s""", (allocation.name))

    # Create new ledger entry
    args = {
        'leaves': allocation.total_leaves_allocated,
        'from_date': allocation.from_date,
        'to_date': allocation.to_date,
        'is_carry_forward': is_carry_forward
    }
    create_leave_ledger_entry(allocation, args, True)

def get_new_leave_allocated_for_annual_paid_leave(allocation, leave_type):
    '''
        Function is used to get new leave allocated for annual paid leave
        args:
            allocation: Object of Leave Allocation
            leave_type: Object of Leave Type
        return: Fraction of Allocation
    '''
    new_leaves_allocated = 0

    # Fetch employee annual leave allocation from employee
    employee_annual_leave = frappe.db.get_value('Employee', allocation.employee, 'annual_leave_balance')
    if employee_annual_leave and employee_annual_leave <= 0:
        # Fetch employee annual leave allocation from company defaults
        employee_annual_leave = frappe.db.get_value('Company', {"name": frappe.defaults.get_user_default("company")}, 'default_annual_leave_balance')

    # calculate daily allocation factor
    if employee_annual_leave > 0:
        new_leaves_allocated = employee_annual_leave/365

    # Set Daily Allocation from annual leave dependent leave type and reduction level
    if leave_type.one_fm_annual_leave_allocation_reduction:
        from erpnext.hr.doctype.leave_application.leave_application import get_leaves_for_period
        leave_days = 0
        if leave_type.one_fm_paid_sick_leave_type_dependent:
            leave_days += get_leaves_for_period(allocation.employee, leave_type.one_fm_paid_sick_leave_type_dependent, allocation.from_date, allocation.to_date)
        else:
            leave_type_list = frappe.get_all('Leave Type', filters= {'one_fm_is_paid_sick_leave': 1}, fields= ["name"])
            for lt in leave_type_list:
                leave_days += get_leaves_for_period(allocation.employee, lt.name, allocation.from_date, allocation.to_date)

        if leave_days > 0:
            percent_of_reduction = 0
            # Get sorted list of allocation reduction Matrix, since the number of paid sick leave mentioned in the table is start from zero
            allocation_reductions = sorted(leave_type.one_fm_annual_leave_allocation_reduction, key=lambda x: x.number_of_paid_sick_leave)
            for allocation_reduction in allocation_reductions:
                if allocation_reduction.number_of_paid_sick_leave <= leave_days:
                    percent_of_reduction = allocation_reduction.percentage_of_allocation_reduction
            if percent_of_reduction > 0:
                new_leaves_allocated -= new_leaves_allocated * (percent_of_reduction/100)

    return new_leaves_allocated

def get_paid_annual_leave_allocation_list(date=nowdate()):
    '''
        Function is used to get paid annual leave allocation
        args:
            date: date
        return: List of Leave Allocation
    '''
    # Get List of Paid Annual Leave Allocation for a date of a Leave Type (having Is Paid Annual Leave marekd True)
    query = """
        select
            la.name, la.leave_type
        from
            `tabLeave Allocation` la, `tabLeave Type` lt
        where
            lt.one_fm_is_paid_annual_leave=1 and la.docstatus=1 and '{0}' between la.from_date and la.to_date
            and la.leave_type=lt.name
    """
    return frappe.db.sql(query.format(getdate(date)), as_dict=True)

def is_employee_allowed_to_avail_increment_existing_allocation(allocation, leave_type):
    '''
        Function is used to check whether the employee is allowed to avail incrementing the leave allocation
        args:
            allocation: Object of Leave Allocation
            leave_type: Object of Leave Type
        return: Boolean
    '''
    allow_allocation = True

    # Check if employee absent today then not allow annual leave allocation for today
    is_absent = frappe.db.sql("""select name, status from `tabAttendance` where employee = %s and
        attendance_date = %s and docstatus = 1 and status = 'Absent' """,
        (allocation.employee, getdate(nowdate())), as_dict=True)
    if is_absent and len(is_absent) > 0:
        allow_allocation = False

    # Get Leave Application for today for the employee in the allocation
    query = """
        select
            name, status, leave_type
        from
            `tabLeave Application`
        where
            employee = %s and (%s between from_date and to_date) and docstatus = 1
    """
    leave_application = frappe.db.sql(query, (allocation.employee, getdate(nowdate())), as_dict=True)

    '''
        If Leave Application exist for today,
        Check the Leave Allocation Matrix stored inside the Leave Type for allow allocation
    '''
    if leave_application and len(leave_application) > 0:
        allow_allocation = False

        # Check if Leave allocation matrix configured insde the Leave Type
        if leave_type.leave_allocation_matrix:
            for matrix in leave_type.leave_allocation_matrix:
                '''
                    Check if Leave Type in the Matrix and Leave Application Same
                    and if Approval Status in Matrix and Leave Application Status then set allow_allocation as True
                '''
                if matrix.leave_type == leave_application[0].leave_type and matrix.allocate_on_leave_application_status == leave_application[0].status:
                    allow_allocation = True

    return allow_allocation

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
def get_item_code(subitem_group = None ,item_group = None ,cur_item_id = None):
    item_code = ""
    if subitem_group:
        subitem_group_code = frappe.db.get_value('Item Group', subitem_group, 'one_fm_item_group_abbr')
        if subitem_group_code:
            item_code = subitem_group_code
        else:
            frappe.msgprint(_("Set Abbreviation for the Item Group {0}".format(subitem_group)),
                alert=True, indicator='orange')
        if item_group:
            item_group_code = frappe.db.get_value('Item Group', item_group, 'one_fm_item_group_abbr')
            if item_group_code:
                item_code = subitem_group_code+"-"+item_group_code
            else:
                frappe.msgprint(_("Set Abbreviation for the Item Group {0}".format(item_group)),
					alert=True, indicator='orange')
    item_code += ("-"+cur_item_id) if cur_item_id else ""
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
    if doc.one_fm_project:
        name = "WRH"
        project_code = frappe.db.get_value('Project', doc.one_fm_project, 'one_fm_project_code')
        if not project_code:
            project_code = create_new_project_code(doc.one_fm_project)
        if project_code:
            name += '-'+project_code
        doc.name = name +'-'+doc.warehouse_code # +'-'+doc.warehouse_name

def create_new_project_code(project_id):
    project_code = frappe.db.sql("select one_fm_project_code+1 from `tabProject` order by one_fm_project_code desc limit 1")
    if project_code:
        new_project_code = project_code[0][0]
    else:
        new_project_code = '1'
    frappe.db.set_value('Project', project_id, 'one_fm_project_code', str(int(new_project_code)).zfill(4))
    return str(int(new_project_code)).zfill(4)

@frappe.whitelist()
def get_warehouse_children(doctype, parent=None, company=None, is_root=False):
	from erpnext.stock.utils import get_stock_value_from_bin

	if is_root:
		parent = ""

	fields = ['name as value', 'is_group as expandable', 'warehouse_name', 'one_fm_project']
	filters = [
		['docstatus', '<', '2'],
		['ifnull(`parent_warehouse`, "")', '=', parent],
		['company', 'in', (company, None,'')]
	]

	warehouses = frappe.get_list(doctype, fields=fields, filters=filters, order_by='name')

	# return warehouses
	for wh in warehouses:
		wh["balance"] = get_stock_value_from_bin(warehouse=wh.value)
		if company:
			wh["company_currency"] = frappe.db.get_value('Company', company, 'default_currency')
	return warehouses

@frappe.whitelist(allow_guest=True)
def item_group_naming_series(doc, method):
    # doc.name = doc.item_group_code+'-'+doc.item_group_name
    pass

@frappe.whitelist()
def supplier_group_on_update(doc, method):
    """update series list"""
    if doc.abbr:
        set_options = frappe.get_meta('Supplier').get_field("naming_series").options+'\n'+'SUP-'+doc.abbr+'-.######'
        check_duplicate_naming_series(set_options)
        series_list = set_options.split("\n")

        # set in doctype
        set_series_for(doc, 'Supplier', series_list)

        # create series
        map(insert_naming_series, [d.split('.')[0] for d in series_list if d.strip()])
        frappe.db.set_value('Supplier Group', doc.name, 'supplier_naming_series', 'SUP-'+doc.abbr+'-.######')

        frappe.msgprint(_("Series Updated"))

def insert_naming_series(series):
    """insert series if missing"""
    if frappe.db.get_value('Series', series, 'name', order_by="name") == None:
        frappe.db.sql("insert into tabSeries (name, current) values (%s, 0)", (series))

def set_series_for(doc, doctype, ol):
    options = scrub_options_list(ol)

    # update in property setter
    prop_dict = {'options': "\n".join(options)}

    for prop in prop_dict:
        ps_exists = frappe.db.get_value("Property Setter",
            {"field_name": 'naming_series', 'doc_type': doctype, 'property': prop})

        if ps_exists:
            ps = frappe.get_doc('Property Setter', ps_exists)
            ps.value = prop_dict[prop]
            ps.save()
        else:
            ps = frappe.get_doc({
                'doctype': 'Property Setter',
                'doctype_or_field': 'DocField',
                'doc_type': doctype,
                'field_name': 'naming_series',
                'property': prop,
                'value': prop_dict[prop],
                'property_type': 'Text',
                '__islocal': 1
            })
            ps.save()

    frappe.clear_cache(doctype=doctype)

def check_duplicate_naming_series(set_options):
    parent = list(set(
        frappe.db.sql_list("""select dt.name
            from `tabDocField` df, `tabDocType` dt
            where dt.name = df.parent and df.fieldname='naming_series' and dt.name != 'Supplier'""")
        + frappe.db.sql_list("""select dt.name
            from `tabCustom Field` df, `tabDocType` dt
            where dt.name = df.dt and df.fieldname='naming_series' and dt.name != 'Supplier'""")
        ))
    sr = [[frappe.get_meta(p).get_field("naming_series").options, p] for p in parent]
    dt = frappe.get_doc("DocType", 'Supplier')
    options = scrub_options_list(set_options.split("\n"))
    for series in options:
        dt.validate_series(series)
        for i in sr:
            if i[0]:
                existing_series = [d.split('.')[0] for d in i[0].split("\n")]
                if series.split(".")[0] in existing_series:
                    frappe.throw(_("Series {0} already used in {1}").format(series,i[1]))

def scrub_options_list(ol):
    options = list(filter(lambda x: x, [cstr(n).strip() for n in ol]))
    return options

@frappe.whitelist(allow_guest=True)
def item_naming_series(doc, method):
    doc.name = doc.item_code
    doc.item_name = doc.item_code

@frappe.whitelist()
def before_insert_warehouse(doc, method):
    set_warehouse_code(doc)

def set_warehouse_code(doc):
    if doc.one_fm_project:
        query = """
            select
                warehouse_code+1
            from
                `tabWarehouse`
            where one_fm_project = '{0}'
            order by
                warehouse_code
            desc limit 1
        """
        new_warehouse_code = frappe.db.sql(query.format(doc.one_fm_project))
        if new_warehouse_code:
            new_warehouse_code_final = new_warehouse_code[0][0]
        else:
            new_warehouse_code_final = '1'
        doc.warehouse_code = str(int(new_warehouse_code_final)).zfill(4)

@frappe.whitelist()
def after_insert_item_group(doc, method):
    if doc.parent_item_group and doc.parent_item_group != 'All Item Group':
        set_item_group_description_form_parent(doc)
    doc.save(ignore_permissions=True)

@frappe.whitelist()
def before_insert_item(doc, method):
    if not doc.item_id:
        set_item_id(doc)
    if not doc.item_code and doc.item_id:
        doc.item_code = get_item_code(doc.subitem_group, doc.item_group, doc.item_id)

@frappe.whitelist()
def validate_item(doc, method):
    final_description = doc.description
    if not doc.item_barcode:
        doc.item_barcode = doc.item_code
    if not doc.parent_item_group:
        doc.parent_item_group = "All Item Groups"
    doc.description = final_description
    #set_item_description(doc)

def set_item_id(doc):
    next_item_id = "000000"
    item_id = get_item_id_series(doc.subitem_group, doc.item_group)
    if item_id:
        next_item_id = str(int(item_id)+1)
        for i in range(0, 6-len(next_item_id)):
            next_item_id = '0'+next_item_id
    doc.item_id = next_item_id

def set_item_description(doc):
    final_description = ""
    # For Uniform Import
    if doc.uniform_type or doc.uniform_type_description:
        doc.have_uniform_type_and_description = True
    if not doc.item_descriptions:
        if doc.description3:
            child_description = doc.append('item_descriptions')
            child_description.description_attribute = "Size"
            child_description.value = doc.description3
        if doc.description4:
            child_description = doc.append('item_descriptions')
            child_description.description_attribute = "Color"
            child_description.value = doc.description4
        if doc.description5:
            child_description = doc.append('item_descriptions')
            child_description.description_attribute = "Material"
            child_description.value = doc.description5
        if doc.final_description:
            child_description = doc.append('item_descriptions')
            child_description.description_attribute = "Gender"
            child_description.value = doc.final_description


    if doc.one_fm_project:
        final_description+=doc.one_fm_project
    if doc.one_fm_designation:
        final_description+=(' - ' if final_description else '')+doc.one_fm_designation
    if doc.uniform_type:
        final_description+=(' - ' if final_description else '')+doc.uniform_type
    if doc.uniform_type_description:
        final_description+=(' - ' if final_description else '')+doc.uniform_type_description
    for item in doc.item_descriptions:
        final_description+=(' - ' if final_description else '')+item.value
    if doc.other_description:
        final_description+=(' - ' if final_description else '')+doc.other_description
    doc.description = final_description

def set_item_group_description_form_parent(doc):
    parent = frappe.get_doc('Item Group', doc.parent_item_group)
    doc.is_fixed_asset = parent.is_fixed_asset
    if parent.is_fixed_asset and parent.asset_category and not doc.asset_category:
        doc.asset_category = parent.asset_category
    if not doc.one_fm_item_group_descriptions and parent.one_fm_item_group_descriptions:
        for desc in parent.one_fm_item_group_descriptions:
            item_group_description = doc.append('one_fm_item_group_descriptions')
            item_group_description.description_attribute = desc.description_attribute
            item_group_description.from_parent = True

@frappe.whitelist(allow_guest=True)
def validate_get_item_group_parent(doc, method):
    # first_parent = doc.parent_item_group
    # second_parent = frappe.db.get_value('Item Group', {"name": first_parent}, 'parent_item_group')
    #
    # if first_parent == 'All Item Groups' or second_parent == 'All Item Groups':
    #     doc.is_group = 1

    new_item_group_code = frappe.db.sql("select item_group_code+1 from `tabItem Group` where parent_item_group ='{0}' order by item_group_code desc limit 1".format(doc.parent_item_group))
    if new_item_group_code:
        new_item_group_code_final = new_item_group_code[0][0]
    else:
        new_item_group_code_final = '1'

    doc.item_group_code = str(int(new_item_group_code_final)).zfill(3)


@frappe.whitelist(allow_guest=True)
def get_item_id_series(subitem_group, item_group):
    previous_item_id = frappe.db.sql("select item_id from `tabItem` where subitem_group='{0}' and item_group='{1}' order by item_id desc".format(subitem_group, item_group))
    if previous_item_id:
        item_group_abbr = frappe.db.get_value('Item Group', item_group, 'one_fm_item_group_abbr')
        if item_group_abbr:
            abbr_item_group_list = frappe.db.get_list('Item Group', {'one_fm_item_group_abbr': item_group_abbr})
            if abbr_item_group_list and len(abbr_item_group_list) > 1:
                item_id_list = []
                for abbr_item_group in abbr_item_group_list:
                    item_id = frappe.db.sql("select item_id from `tabItem` where item_group='{0}' order by item_id desc".format(abbr_item_group['name']))
                    if item_id:
                        item_id_list.append(item_id[0][0])
                return get_sorted_item_id(item_id_list)
        return previous_item_id[0][0]
    else:
        return '0000'

def get_sorted_item_id(item_id_list):
    max = item_id_list[0]
    for item_id in item_id_list:
        if item_id > max:
            max = item_id
    return max

def filter_uniform_type_description(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select
			parent
		from
			`tabUniform Description Type`
		where
			uniform_type = %(uniform_type)s and uniform_type like %(txt)s
			limit %(start)s, %(page_len)s"""
	return frappe.db.sql(query,
		{
			'uniform_type': filters.get("uniform_type"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)

def validate_job_applicant(doc, method):
    from one_fm.one_fm.utils import check_mendatory_fields_for_grd_and_recruiter
    check_mendatory_fields_for_grd_and_recruiter(doc, method)#fix visa 22
    # validate_pam_file_number_and_pam_designation(doc, method)
    validate_transferable_field(doc)
    set_job_applicant_fields(doc)
    if not doc.one_fm_is_easy_apply:
        validate_mandatory_fields(doc)
    set_job_applicant_status(doc, method)
    set_average_score(doc, method)
    if doc.is_new():
        set_childs_for_application_web_form(doc, method)
    elif not doc.one_fm_documents_required:
        set_required_documents(doc, method)
    if frappe.session.user != 'Guest' and not doc.one_fm_is_easy_apply:
        validate_mandatory_childs(doc)
    if doc.one_fm_applicant_status in ["Shortlisted", "Selected"]:
        create_job_offer_from_job_applicant(doc.name)
    if doc.one_fm_number_of_kids and doc.one_fm_number_of_kids > 0:
        """This part is comparing the number of children with the listed children details in the table and ask user to add all childrens"""
        if doc.one_fm_number_of_kids != len(doc.one_fm_kids_details):
            frappe.throw("Please List All Children in the Table.")

def validate_pam_file_number_and_pam_designation(doc, method):
    if doc.one_fm_erf:
        pam_file_number,pam_designation = frappe.db.get_value('ERF',{'name':doc.one_fm_erf},['pam_file_number','pam_designation'])
        if pam_file_number and pam_designation:
            doc.one_fm_erf_pam_file_number = pam_file_number
            doc.one_fm_erf_pam_designation = pam_designation


def validate_transferable_field(doc):
    if doc.one_fm_applicant_is_overseas_or_local != 'Local':
        doc.one_fm_is_transferable = ''

def validate_mandatory_childs(doc):
    if doc.one_fm_languages:
        for language in doc.one_fm_languages:
            if not language.read or int(language.read) < 1 or not language.write or int(language.write) < 1 or not language.speak or int(language.speak) < 1:
                frappe.throw(_("Language - Row {0}: Should Rate You Read, Write and Speak for {1}".format(language.idx, language.language_name)))

    if doc.one_fm_designation_skill:
        for skill in doc.one_fm_designation_skill:
            if not skill.one_fm_proficiency or int(skill.one_fm_proficiency) < 1:
                frappe.throw(_("Basic Skills - Row {0}: Should Rate Proficiency for Skill {1}".format(skill.idx, skill.skill)))

def set_childs_for_application_web_form(doc, method):
    set_required_documents(doc, method)
    set_job_basic_skill(doc, method)
    set_job_languages(doc, method)

def set_job_languages(doc, method):
    if not doc.one_fm_languages:
        languages = False
        if doc.job_title:
            job = frappe.get_doc('Job Opening', doc.job_title)
            if job.one_fm_languages:
                languages = job.one_fm_languages
        elif doc.one_fm_erf and not languages:
            erf = frappe.get_doc('ERF', doc.one_fm_erf)
            if erf.languages:
                languages = erf.languages
        if languages:
            set_languages(doc, languages)

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
        designation_skill = False
        if doc.job_title:
            job = frappe.get_doc('Job Opening', doc.job_title)
            if job.one_fm_designation_skill:
                designation_skill = job.one_fm_designation_skill
        elif doc.one_fm_erf and not designation_skill:
            erf = frappe.get_doc('ERF', doc.one_fm_erf)
            if erf.designation_skill:
                designation_skill = erf.designation_skill
        if designation_skill:
            set_designation_skill(doc, designation_skill)

def set_designation_skill(doc, skills):
    for designation_skill in skills:
        skill = doc.append('one_fm_designation_skill')
        skill.skill = designation_skill.skill

def set_required_documents(doc, method):
    if not doc.one_fm_documents_required:
        filters = {}
        source_of_hire = 'Overseas'
        if doc.one_fm_nationality == 'Kuwaiti':
            source_of_hire = 'Kuwaiti'
        elif doc.one_fm_have_a_valid_visa_in_kuwait:
            source_of_hire = 'Local'
        if doc.one_fm_have_a_valid_visa_in_kuwait and doc.one_fm_visa_type:
            filters['visa_type'] = doc.one_fm_visa_type
        filters['source_of_hire'] = source_of_hire

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
                {'University / School':'one_fm_university'}]

    field_list.extend(get_mandatory_for_dependent_fields(doc))
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

def get_mandatory_for_dependent_fields(doc):
    field_list = []
    field_list.extend(get_mandatory_fields_current_employment(doc))
    field_list.extend(get_mandatory_fields_visa_details(doc))
    field_list.extend(get_mandatory_fields_contact_details(doc))
    field_list.extend(get_mandatory_fields_work_details(doc))
    return field_list

def get_mandatory_fields_work_details(doc):
    field_list = []
    if doc.one_fm_erf:
        erf = frappe.get_doc('ERF', doc.one_fm_erf)
        if erf.shift_working:
            field_list.append({'Rotation Shift': 'one_fm_rotation_shift'})
        if erf.night_shift:
            field_list.append({'Night Shift': 'one_fm_night_shift'})
        if erf.travel_required:
            if erf.type_of_travel:
                field_list.append({'Type of Travel': 'one_fm_type_of_travel'})
            field_list.append({'Type of Driving License': 'one_fm_type_of_driving_license'})
    return field_list

def get_mandatory_fields_contact_details(doc):
    # if not doc.one_fm_is_agency_applying:
    #     return [{'Country Code for Primary Contact Number': 'one_fm_country_code'},
    #         {'Primary Contact Number': 'one_fm_contact_number'}]
    return []

def get_mandatory_fields_visa_details(doc):
    if doc.one_fm_have_a_valid_visa_in_kuwait:
        return [{'Visa Type': 'one_fm_visa_type'}, {'Civil ID Number': 'one_fm_cid_number'},
            {'Civil ID Valid Till': 'one_fm_cid_expire'}]
    return []

def get_mandatory_fields_current_employment(doc):
    if doc.one_fm_i_am_currently_working:
        return [{'Current Employeer': 'one_fm_current_employer'}, {'Employment Start Date': 'one_fm_employment_start_date'},
            {'Employment End Date': 'one_fm_employment_end_date'}, {'Current Job Title': 'one_fm_current_job_title'},
            {'Current Salary in KWD': 'one_fm_current_salary'}, {'Country of Employment': 'one_fm_country_of_employment'},
            {'Notice Period in Days': 'one_fm_notice_period_in_days'}
        ]
    return []

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
        else:
            doc.one_fm_average_interview_score = total

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
    job_offer.one_fm_provide_accommodation_by_company = erf.provide_accommodation_by_company
    job_offer.one_fm_provide_transportation_by_company = erf.provide_transportation_by_company
    set_salary_details(job_offer, erf)
    set_other_benefits_to_terms(job_offer, erf)

def set_salary_details(job_offer, erf):
    job_offer.one_fm_provide_salary_advance = erf.provide_salary_advance
    total_amount = 0
    job_offer.base = erf.base
    for salary in erf.salary_details:
        total_amount += salary.amount
        salary_details = job_offer.append('one_fm_salary_details')
        salary_details.salary_component = salary.salary_component
        salary_details.amount = salary.amount
    job_offer.one_fm_job_offer_total_salary = total_amount

def set_other_benefits_to_terms(job_offer, erf):
    # if erf.other_benefits:
    #     for benefit in erf.other_benefits:
    #         terms = job_offer.append('offer_terms')
    #         terms.offer_term = benefit.benefit
    #         terms.value = 'Company Provided'
    options = [{'provide_mobile_with_line':'Mobile with Line'}, {'provide_health_insurance':'Health Insurance'},
        {'provide_company_insurance': 'Company Insurance'}, {'provide_laptop_by_company': 'Personal Laptop'},
        {'provide_vehicle_by_company': 'Personal Vehicle'}]
    for option in options:
        if erf.get(option):
            terms = job_offer.append('offer_terms')
            terms.offer_term = options[option]
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

@frappe.whitelist(allow_guest=True)
def check_if_user_exist_as_desk_user(user):
    user_exist = frappe.db.exists('User', user)
    if user_exist:
        return frappe.db.get_value('User', user_exist, 'user_type')
    return False

def get_job_applicant_transferable_overseas(applicant):
    job_applicant = frappe.get_doc('Job Applicant', applicant)
    result = {'overseas': False, 'transferable': False}
    if job_applicant.one_fm_applicant_is_overseas_or_local:
        result['overseas'] = job_applicant.one_fm_applicant_is_overseas_or_local
        if job_applicant.one_fm_is_transferable:
            result['transferable'] = job_applicant.one_fm_is_transferable
    return result

def validate_applicant_overseas_transferable(applicant):
    transferable_details = get_job_applicant_transferable_overseas(applicant)
    if not transferable_details['overseas']:
        frappe.throw(_('Mark the Applicant is Overseas or Local'))
    elif transferable_details['overseas'] == 'Local':
        if not transferable_details['transferable']:
            frappe.throw(_('Mark the Applicant is Transferable or Not'))
        if transferable_details['transferable'] == "No":
            frappe.throw(_("Applicant is Not Transferable"))

@frappe.whitelist()
def set_warehouse_contact_from_project(doc, method):
    if doc.one_fm_project and doc.one_fm_site:
        site = frappe.get_doc("Operations Site", doc.one_fm_site)
        # if site.site_poc:
        #     for poc in site.site_poc:
        #         if poc.poc:
        #             contact = frappe.get_doc('Contact', poc.poc)
        #             links = contact.append('links')
        #             links.link_doctype = doc.doctype
        #             links.link_name = doc.name
        #             contact.save(ignore_permissions=True)
        if site.address:
            address = frappe.get_doc('Address', site.address)
            links = address.append('links')
            links.link_doctype = doc.doctype
            links.link_name = doc.name
            address.save(ignore_permissions=True)

def validate_iban_is_filled(doc, method):
    if not doc.iban and doc.workflow_state == 'Active Account':
        frappe.throw(_("Please Set IBAN before you Mark Open the Bank Account"))

def bank_account_on_update(doc, method):
    update_onboarding_doc_for_bank_account(doc)

def bank_account_on_trash(doc, method):
    if doc.onboard_employee:
        oe = frappe.get_doc('Onboard Employee', doc.onboard_employee)
        oe.bank_account = ''
        oe.bank_account_progress = 0
        oe.bank_account_docstatus = ''
        oe.bank_account_status = ''
        oe.account_name = doc.account_name
        oe.bank = doc.bank
        oe.save(ignore_permissions=True)

def update_onboarding_doc_for_bank_account(doc):
    if doc.onboard_employee:
        progress_wf_list = {'Draft': 0, 'Open Request': 30, 'Processing Bank Account Opening': 70,
            'Rejected by Accounts': 100, 'Active Account': 100}
        bank_account_status = 1
        if doc.workflow_state == 'Rejected by Accounts':
            bank_account_status = 2
        if doc.workflow_state in progress_wf_list:
            progress = progress_wf_list[doc.workflow_state]
        oe = frappe.get_doc('Onboard Employee', doc.onboard_employee)
        oe.bank_account = doc.name
        oe.bank_account_progress = progress
        oe.bank_account_docstatus = bank_account_status
        oe.bank_account_status = doc.workflow_state
        oe.account_name = doc.account_name
        oe.bank = doc.bank
        if oe.workflow_state == 'Duty Commencement':
            oe.workflow_state = 'Bank Account'
        oe.save(ignore_permissions=True)

def issue_roster_actions():
    # Queue roster actions functions to backgrounds jobs
    frappe.enqueue(create_roster_employee_actions, is_async=True, queue='long')
    frappe.enqueue(create_roster_post_actions, is_async=True, queue='long')


def create_roster_employee_actions():
    """
    This function creates a Roster Employee Actions document and issues notifications to relevant supervisors
    directing them to schedule employees that are unscheduled and assigned to them.
    It computes employees not scheduled for the span of two weeks, starting from tomorrow.
    """

    # start date to be from tomorrow
    start_date = add_to_date(cstr(getdate()), days=1)
    # end date to be 14 days after start date
    end_date = add_to_date(start_date, days=14)

    #-------------------- Roster Employee actions ------------------#
    # fetch employees that are active and don't have a schedule in the specified date range
    employees_not_rostered = frappe.db.sql("""
                            select
                                employee from `tabEmployee`
                            where
                                employee not in
                                (select employee
                                from `tabEmployee Schedule`
                                where date >= %(start)s and date <=%(end)s) """,
                                {'start': start_date, 'end': end_date})

    employees = ()

    # fetch employees that are not rostered from the result returned by the query and append to tuple
    for emp in employees_not_rostered:
        employees = employees + emp

    # fetch supervisors and list of employees(not rostered) under them
    result = frappe.db.sql("""select sv.employee, group_concat(e.employee)
            from `tabEmployee` e
            join `tabOperations Shift` sh on sh.name = e.shift
            join `tabEmployee` sv on sh.supervisor=sv.employee
            where e.employee in {employees}
            group by sv.employee """.format(employees=employees))

    # for each supervisor, create a roster action
    for res in result:
        supervisor = res[0]
        employees = res[1].split(",")

        roster_employee_actions_doc = frappe.new_doc("Roster Employee Actions")
        roster_employee_actions_doc.start_date = start_date
        roster_employee_actions_doc.end_date = end_date
        roster_employee_actions_doc.status = "Pending"
        roster_employee_actions_doc.action_type = "Roster Employee"
        roster_employee_actions_doc.supervisor = supervisor

        for emp in employees:
            roster_employee_actions_doc.append('employees_not_rostered', {
                'employee': emp
            })

        roster_employee_actions_doc.save()
        frappe.db.commit()

    #-------------------- END Roster Employee actions ------------------#


def create_roster_post_actions():
    """
    This function creates a Roster Post Actions document that issues actions to supervisors to fill post types that are not filled for a given date range.
    """

    # start date to be from tomorrow
    start_date = add_to_date(cstr(getdate()), days=1)
    # end date to be 14 days after start date
    end_date = add_to_date(start_date, days=14)

    post_types_not_filled_set = set()

    # Fetch post schedules in the date range that are active
    post_schedules = frappe.db.get_list("Post Schedule", {'date': ['between', (start_date, end_date)], 'post_status': 'Planned'}, ["date", "shift", "post_type", "post"], order_by="date asc")
    # Fetch employee schedules for employees who are working
    employee_schedules = frappe.db.get_list("Employee Schedule", {'date': ['between', (start_date, end_date)], 'employee_availability': 'Working'}, ["date", "shift", "post_type"], order_by="date asc")

    for ps in post_schedules:
        # if there is not any employee schedule that matches the post schedule for the specified date, add to post types not filled
        if not any(cstr(es.date).split(" ")[0] == cstr(ps.date).split(" ")[0] and es.shift == ps.shift and es.post_type == ps.post_type for es in employee_schedules):
            post_types_not_filled_set.add(ps.post_type)

    # Convert set to tuple for passing it in the sql query as a parameter
    post_types_not_filled = tuple(post_types_not_filled_set)

    # Fetch supervisor and post types in his/her shift
    result = frappe.db.sql("""select sv.employee, group_concat(distinct ps.post_type)
            from `tabPost Schedule` ps
            join `tabOperations Shift` sh on sh.name = ps.shift
            join `tabEmployee` sv on sh.supervisor=sv.employee
            where ps.post_type in {post_types}
            group by sv.employee""".format(post_types=post_types_not_filled))

    # For each supervisor, create post actions to fill post type specifying the post types not filled
    for res in result:
        supervisor = res[0]
        post_types = res[1].split(",")

        roster_post_actions_doc = frappe.new_doc("Roster Post Actions")
        roster_post_actions_doc.start_date = start_date
        roster_post_actions_doc.end_date = end_date
        roster_post_actions_doc.status = "Pending"
        roster_post_actions_doc.action_type = "Fill Post Type"
        roster_post_actions_doc.supervisor = supervisor

        for post_type in post_types:
            roster_post_actions_doc.append('post_types_not_filled', {
                'post_type': post_type
            })

        roster_post_actions_doc.save()
        frappe.db.commit()

def send_roster_report():
    # Enqueue roster report generation to background
    frappe.enqueue(generate_roster_report, is_async=True, queue='long')

def generate_roster_report():
    """
    This method creates a monthly company wide roster Post and Employee report in a tabular format
    and sends it via email to users having role as 'Operations Manager'.
    """

    start_date = cstr(getdate())
    end_date = add_to_date(start_date, days=30)

    # ---------------------- Roster Post Report -----------------------#
    post_report_table = """
    <table class="table table-bordered table-hover">
        <thead>
            <tr>
                <td><b>Date</b></td>
                <td><b>Active Posts</b></td>
                <td><b>Posts Off</b></td>
                <td><b>Posts Filled</b></td>
                <td><b>Posts Not Filled</b></td>
                <td><b>Result</b></td>
            </tr>
        </thead>
        <tbody>
    """

    for date in pd.date_range(start=start_date, end=end_date):
        active_posts = len(frappe.db.get_list("Post Schedule", {'post_status': 'Planned', 'date': date}, ["post_type"]))
        posts_off = len(frappe.db.get_list("Post Schedule", {'post_status': 'Post Off', 'date': date}))

        posts_filled_count = 0
        posts_not_filled_count = 0

        post_types = frappe.db.get_list("Post Schedule", ["distinct post_type", "post_abbrv"])
        for post_type in post_types:
            # For each post type, get all post schedules and employee schedules assigned to the post type
            posts_count = len(frappe.db.get_list("Post Schedule", {'post_type': post_type.post_type, 'date': date, 'post_status': 'Planned'}))
            posts_fill_count = len(frappe.db.get_list("Employee Schedule", {'post_type': post_type.post_type, 'date': date, 'employee_availability': 'Working'}))

            # Compare count of post schedule vs employee schedule for the given post type, compute post filled/not filled count
            if posts_count == posts_fill_count:
                posts_filled_count += posts_fill_count
            elif posts_count > posts_fill_count:
                posts_filled_count += posts_fill_count
                posts_not_filled_count = posts_not_filled_count + (posts_count - posts_fill_count)

        result = "OK"
        if posts_not_filled_count > 0:
            result = "NOT OK"

        # Append row to post table
        post_report_table += """<tr><td>{current_date}</td>""".format(current_date=cstr(date).split(" ")[0])
        post_report_table += """<td>{active_posts}</td>""".format(active_posts=active_posts)
        post_report_table += """<td>{posts_off}</td>""".format(posts_off=posts_off)
        post_report_table += """<td>{posts_filled}</td>""".format(posts_filled=posts_fill_count)
        post_report_table += """<td>{posts_not_filled}</td>""".format(posts_not_filled=posts_not_filled_count)
        post_report_table += """<td>{result}</td></tr>""".format(result=result)

    post_report_table += """
        </tbody>
    </table>
    """

    # ------------------- Roster Employee Report -------------------#
    employee_report_table = """
    <table class="table table-bordered table-hover">
        <thead>
            <tr>
                <td><b>Date</b></td>
                <td><b>Active Employees</b></td>
                <td><b>Rostered</b></td>
                <td><b>Not Rostered</b></td>
                <td><b>Day offs</b></td>
                <td><b>Sick Leaves</b></td>
                <td><b>Annual Leaves</b></td>
                <td><b>Emergency Leaves</b></td>
                <td><b>Result</b></td>
            </tr>
        </thead>
        <tbody>
    """
    for date in pd.date_range(start=start_date, end=end_date):
        employee_list = get_active_employees(date)
        rostered_employees = get_working_employees(date)
        employees_on_day_off = get_day_off_employees(date)
        employees_on_sick_leave = get_sick_leave_employees(date)
        employees_on_annual_leave = get_annual_leave_employees(date)
        employees_on_emergency_leave = get_emergency_leave_employees(date)

        employee_not_rostered_count = 0

        for employee in employee_list:
            # If no employee schedule is found for an employee on the current date, increment not rostered count
            if not frappe.db.exists({'doctype': 'Employee Schedule', 'date': date, 'employee': employee.employee}):
                employee_not_rostered_count += 1

        result = "OK"
        if employee_not_rostered_count > 0:
            result = "NOT OK"

        # Append row to employee table
        employee_report_table += """<tr><td>{current_date}</td>""".format(current_date=cstr(date).split(" ")[0])
        employee_report_table += """<td>{employee_list}</td>""".format(employee_list=len(employee_list))
        employee_report_table += """<td>{rostered_employees}</td>""".format(rostered_employees=len(rostered_employees))
        employee_report_table += """<td>{employees_not_rostered_count}</td>""".format(employees_not_rostered_count=employee_not_rostered_count)
        employee_report_table += """<td>{employees_on_day_off}</td>""".format(employees_on_day_off=len(employees_on_day_off))
        employee_report_table += """<td>{employees_on_sick_leave}</td>""".format(employees_on_sick_leave=len(employees_on_sick_leave))
        employee_report_table += """<td>{employees_on_annual_leave}</td>""".format(employees_on_annual_leave=len(employees_on_annual_leave))
        employee_report_table += """<td>{employees_on_emergency_leave}</td>""".format(employees_on_emergency_leave=len(employees_on_emergency_leave))
        employee_report_table += """<td>{result}</td></tr>""".format(result=result)

    employee_report_table += """
        </tbody>
    </table>
    """

    recipients = []

    # get list of all entries having role as Operations Manager included
    parent_list = frappe.db.sql("""SELECT DISTINCT parent FROM `tabHas Role` WHERE role=%(role)s""",{'role': "Operations Manager"}, as_dict=1)

    for parent in parent_list:
        # Check if parent is an employee. If yes, append to recipients list
        if frappe.db.exists("Employee", {'user_id': parent.parent}):
            recipients.append(parent.parent)

    # Send Roster Post report email to Operations Managers
    post_report_subject = "Roster Post Report from {start_date} to {end_date}".format(start_date=start_date, end_date=end_date)
    frappe.sendmail(recipients= recipients, content=post_report_table, subject=post_report_subject ,delayed=False)

    # Send Roster Employee report email to Operations Managers
    employee_report_subject = "Roster Employee Report from {start_date} to {end_date}".format(start_date=start_date, end_date=end_date)
    frappe.sendmail(recipients= recipients, content=employee_report_table, subject=employee_report_subject ,delayed=False)



def get_active_employees(date):
        """ returns list of all active employees from where date of joining is greater than provided date """
        return frappe.db.get_list("Employee", {'status': 'Active', 'date_of_joining': ('<=', date)}, ["employee"])

def get_working_employees(date):
    """ returns list of employees who's employee availability status is 'working' for a given date """
    return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Working'})

def get_day_off_employees(date):
    """ returns list of employees who's employee availability status is day off for a given date """
    return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Day Off'})

def get_sick_leave_employees(date):
    """ returns list of employees who's employee availability status is sick leave for a given date """
    return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Sick Leave'})

def get_annual_leave_employees(date):
    """ returns list of employees who's employee availability status is annual leave for a given date """
    return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Annual Leave'})

def get_emergency_leave_employees(date):
    """ returns list of employees who's employee availability status is emergency leave for a given date """
    return frappe.db.get_list("Employee Schedule", {'date': date, 'employee_availability': 'Emergency Leave'})


@frappe.whitelist()
def create_additional_salary_for_overtime_request_for_head_office(doc,method):
    """
    Method called in `Hook.py` Employee Checkin

    Param:
    -------
    checkout record
    method: `on_update`

    Returns:
    --------
    create Addiitonal Salary for Overtime request (OT request)

    Explicit Explanation:
    ----------------------
    Method is covering two cases:
    case1: Employee has OT request within a working day. The system will check the check-out time and accepted the OT request to create an additional salary.
    case2: Employee has OT request within a day off. The system will check both check-in and checkout and accepted OT request to create additional salary and update employee schedule record.
    """
    # Define the `overtime_request_type` `employee_availability` `roster_type` `week_days` values
    overtime_request_type = "Head Office"
    employee_availability = ["Day Off","Working"]
    roster_type = ["Over-Time", "Basic"]
    week_days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


    # Fetch payroll details from HR and Payroll Additional Settings
    overtime_component = frappe.db.get_single_value("HR and Payroll Additional Settings", 'overtime_additional_salary_component')
    working_day_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'working_day_overtime_rate')
    day_off_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'day_off_overtime_rate')
    public_holiday_overtime_rate = frappe.db.get_single_value("HR and Payroll Additional Settings", 'public_holiday_overtime_rate')

    if doc.log_type == "OUT" and frappe.db.exists("Overtime Request",{'employee':doc.employee, 'request_type':overtime_request_type, 'date':getdate(doc.time), 'status':"Accepted"}):
        check_out_time = get_time(doc.time)
        check_out_date = getdate(doc.time)
        overtime_doc = frappe.get_doc("Overtime Request",{'employee':doc.employee, 'request_type':overtime_request_type, 'date':check_out_date, 'status':"Accepted"})
        basic_salary, employee_holiday_list = frappe.db.get_value("Employee",{'name':doc.employee},['one_fm_basic_salary', 'holiday_list'])
        shift_duration = frappe.db.get_value("Operations Shift", doc.operations_shift,['duration'])

        # Pass last parameter as "False" to get weekly off days
        holidays_weekly_off = get_holidays_for_employee(doc.employee, check_out_date, check_out_date, False, False)

        # Pass last paramter as "True" to get non weekly off days, ie, public/additional holidays
        holidays_public_holiday = get_holidays_for_employee(doc.employee, check_out_date, check_out_date, False, True)

        # Check if Employee in a Day OFF
        if frappe.db.exists("Employee Schedule",{'employee':doc.employee, 'date':check_out_date, 'employee_availability':employee_availability[0]}):
            # Get checkin_time for the employee in the same day of OT request
            checkin_datetime = frappe.db.get_value("Employee Checkin",{'employee':doc.employee, 'log_type':"IN"}, ['time'])
            if checkin_datetime:
                if is_checkin_record_available(check_out_date, check_out_time, checkin_datetime, overtime_doc.start_time, overtime_doc.end_time):
                    if basic_salary and shift_duration:
                        if overtime_doc.overtime_hours and not frappe.db.exists("Additional Salary",{'employee':doc.employee, 'payroll_date':getdate(), 'salary_component':overtime_component}):

                            # Check if dayoff is not public holiday
                            if employee_holiday_list:
                                if len(holidays_weekly_off) > 0 and holidays_weekly_off[0].description in week_days:

                                    if day_off_overtime_rate > 0:
                                        hourly_wage = rounded(rounded(flt(basic_salary)/30, 3) / shift_duration, 3)
                                        overtime_amount = rounded(flt(overtime_doc.overtime_hours) * hourly_wage * day_off_overtime_rate,3) # Overtime = `overtime_hours` * day_off_overtime_rate * hourly_wage

                                        create_additional_salary_for_ot(doc.employee, overtime_amount, overtime_component)

                                        update_employee_schedule(frappe.get_doc("Employee Schedule",{'employee':doc.employee, 'date':check_out_date, 'employee_availability':employee_availability[0]}),employee_availability[1],roster_type[0])
                                    else:
                                        frappe.throw(_("No Day Off overtime rate set in HR and Payroll Additional Settings."))

                                # Check if the day off is public holiday
                                elif len(holidays_public_holiday) > 0:

                                    if public_holiday_overtime_rate > 0:
                                        hourly_wage = rounded(rounded(flt(basic_salary)/30, 3) / shift_duration, 3)
                                        overtime_amount = rounded(flt(overtime_doc.overtime_hours) * hourly_wage * public_holiday_overtime_rate,3) # Overtime = `overtime_hours` * public_holiday_overtime_rate * hourly_wage

                                        create_additional_salary_for_ot(doc.employee, overtime_amount, overtime_component)

                                        update_employee_schedule(frappe.get_doc("Employee Schedule",{'employee':doc.employee, 'date':check_out_date, 'employee_availability':employee_availability[0]}),employee_availability[1],roster_type[0])
                                    else:
                                        frappe.throw(_("No Public Holiday overtime rate set in HR and Payroll Additional Settings."))

                    if not basic_salary:
                        frappe.throw("Please Define The Basic Salary for {employee} to Create Overtime Allowance".format(employee=doc.employee))

        # Check if Employee in a Working day
        if frappe.db.exists("Employee Schedule",{'employee':doc.employee, 'date':check_out_date, 'employee_availability':employee_availability[1]}):

            if cstr(check_out_time) >= cstr(overtime_doc.end_time):# Check-out time is equal or after the requested time.

                if basic_salary and shift_duration:
                    if overtime_doc.overtime_hours and not frappe.db.exists("Additional Salary",{'employee':doc.employee, 'payroll_date':getdate(), 'salary_component':overtime_component}):
                        if working_day_overtime_rate > 0:
                            hourly_wage = rounded(rounded(flt(basic_salary)/30, 3) / shift_duration, 3)
                            overtime_amount = rounded(flt(overtime_doc.overtime_hours) * hourly_wage * working_day_overtime_rate ,3) # Overtime = `overtime_hours` * working_day_overtime_rate * hourly_wage
                            create_additional_salary(doc.employee, overtime_amount, overtime_component)
                        else:
                            frappe.throw(_("No Working day overtime rate set in HR and Payroll Additional Settings."))

                if not basic_salary:
                    frappe.throw("Please Define The Basic Salary for {employee} to Create Overtime Allowance".format(employee=doc.employee))

# The method checks the availability of check-in records for Head Office employees during their Day Off
# and verifies both the check-in and checkout time with the requested time in the Overtime request (OT request)
def is_checkin_record_available(check_out_date, check_out_time, checkin_datetime, start_time, end_time):
    """
    Param:
    -------
    check_out_date (eg: 2021-11-11)
    check_out_time (eg: 11:00:00)
    checkin_datetime (eg: 2021-11-11 11:00:00)
    start_time (eg: 10:00:00) - `start_time` mentioned in the overtime request
    end_time (eg: 11:00:00) - `end_time` mentioned in the overtime request

    Returns:
    --------
     boolean (True or False)

    The method verifies the check-in and checkout time to be within the start and end time in the overtime request
    """
    checkin_date = getdate(checkin_datetime)
    checkin_time = get_time(checkin_datetime)
    if checkin_date == check_out_date:
        if cstr(checkin_time) <= cstr(start_time) and cstr(check_out_time) >= cstr(end_time):
            return True
    else:
        return False

# The Method is updating Employee Schedule data for `employee_availability` and `roster_type`
def update_employee_schedule(employee_schedule_doc,employee_availability,roster_type):
    """
    Param:
    ------
    Employee Schedule doctype
    employee_availability: (eg: Working)
    roster_type: (eg: Over-Time)
    """
    employee_schedule_doc.employee_availability = employee_availability #Working
    employee_schedule_doc.roster_type = roster_type #  "Over-Time"
    employee_schedule_doc.save(ignore_permissions=True)

# Create Additional Salary For employee and set the overtime allowance for them and the OT amount

def create_additional_salary_for_ot(employee, amount, overtime_component):

	"""
    Param:
    ------
    Employee & overtime amount & overtime_component

    overtime_component: (eg :"Overtime Allowance")
    """
	additional_salary = frappe.new_doc("Additional Salary")
	additional_salary.employee = employee
	additional_salary.salary_component = overtime_component
	additional_salary.amount = amount
	additional_salary.payroll_date = getdate()
	additional_salary.company = erpnext.get_default_company()
	additional_salary.overwrite_salary_structure_amount = 1
	additional_salary.notes = "Overtime Earning"
	additional_salary.insert()
	additional_salary.submit()

def response(message, data, success, status_code):
     # Function to create response to the API. It generates json with message, success, data object and the status code.
     frappe.local.response["message"] = message
     frappe.local.response["success"] = success
     frappe.local.response["data_obj"] = data
     frappe.local.response["http_status_code"] = status_code
     return

import hashlib
import math, random

@frappe.whitelist()
def send_verification_code(doctype, document_name):
    """ This method sends a one time verification code to the user's email address.
        Upon sending the code to the user, it saves this data in cache.
        Data stored in cache is of key-value pair with a timeout of 300s set to it.
        Cache data is as follows:
            key: md5 hash of user email address, doctype, document
            value: md5 hash of user email address, doctype, document and verification code generated.

    Args:
        doctype (str): Name of the DocType.
        document_name (str): Name of the document of the DocType.

    """
    try:
        verification_code = generate_code()
        employee_user_email = frappe.session.user
        subject = _("Verification code for {doctype}.".format(doctype=doctype))
        message = """Dear user,<br><br>
            An attempt was made to use your signature in {doctype}: {document}.<br><br>
            To use your signature, use the verification code: <b>{verification_code}</b>.<br><br>
            This code will expire in the next 5 minutes.<br>
            If this was not you, ignore this email.<br>
            """.format(doctype=doctype, document=document_name, verification_code=verification_code)

        frappe.sendmail([employee_user_email], subject=subject, content=message, delayed=False)

        cache_key = hashlib.md5((employee_user_email + doctype + document_name).encode('utf-8')).hexdigest()
        cache_value = hashlib.md5((employee_user_email + doctype + document_name + str(verification_code)).encode('utf-8')).hexdigest()

        frappe.cache().set(cache_key, cache_value)
        frappe.cache().expire(cache_key, 300)

    except Exception as e:
        frappe.throw(e)

@frappe.whitelist()
def verify_verification_code(doctype, document_name, verification_code):
    """This method verfies the user verification code by fetching the originally sent code by the system from cache.

    Args:
        doctype (str): Name of the DocType.
        document_name (str): Name of the document of the DocType.
        verification_code (int): User verification code

    Returns:
        boolean: True/False upon verification code being verified.
    """
    try:
        employee_user_email = frappe.session.user
        cache_search_key = hashlib.md5((employee_user_email + doctype + document_name).encode('utf-8')).hexdigest()
        verification_hash = hashlib.md5((employee_user_email + doctype + document_name + str(verification_code)).encode('utf-8')).hexdigest()

        if not frappe.cache().get(cache_search_key):
            frappe.throw(_("Verification code expired. Please try again."))
        
        if verification_hash != frappe.cache().get(cache_search_key).decode('utf-8'):
            frappe.throw(_("Incorrect verification code."))

        return True

    except Exception as e:
        frappe.throw(e)

def generate_code():
    """This method generates a random non-zero 6 digit number.

    Returns:
        int: random 6 digit number.
    """
    digits = "123456789"
    code = ""
    for i in range(6) :
        code += digits[math.floor(random.random() * 9)]
    return code