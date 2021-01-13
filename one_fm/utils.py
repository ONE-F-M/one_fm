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
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate, formatdate ,get_url, get_datetime, add_to_date
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
        # parent_item_group_code = frappe.db.get_value('Item Group', parent_item_group, 'item_group_code')
        parent_item_group_code = ""
        item_code = parent_item_group_code

        if subitem_group:
            # subitem_group_code = frappe.db.get_value('Item Group', subitem_group, 'item_group_code')
            subitem_group_code = frappe.db.get_value('Item Group', subitem_group, 'one_fm_item_group_abbr')
            item_code = subitem_group_code

            if item_group:
                # item_group_code = frappe.db.get_value('Item Group', item_group, 'item_group_code')
                item_group_code = frappe.db.get_value('Item Group', item_group, 'one_fm_item_group_abbr')
                item_code = subitem_group_code+"-"+item_group_code

                if cur_item_id:
                    item_code = subitem_group_code+"-"+item_group_code+"-"+cur_item_id

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
    # name = "WRH-"+doc.warehouse_code
    name = "WRH"
    if doc.one_fm_is_project_warehouse and doc.one_fm_project:
        project_code = frappe.db.get_value('Project', doc.one_fm_project, 'one_fm_project_code')
        if project_code:
            name += '-'+project_code
    # if doc.is_group == '1':
    #     name += '-'+'01'
    # else:
    #     name += '-'+'02'
    doc.name = name +'-'+doc.warehouse_code # +'-'+doc.warehouse_name

@frappe.whitelist(allow_guest=True)
def item_group_naming_series(doc, method):
    # doc.name = doc.item_group_code+'-'+doc.item_group_name
    pass

@frappe.whitelist(allow_guest=True)
def item_naming_series(doc, method):
    doc.name = doc.item_code
    doc.item_name = doc.item_code

@frappe.whitelist(allow_guest=True)
def validate_get_warehouse_parent(doc, method):
    if doc.parent_warehouse:
        parent_wh_code = frappe.db.get_value('Warehouse', doc.parent_warehouse, 'warehouse_code')
        # if parent_wh_code:
        #     doc.warehouse_code = parent_wh_code + " - "
        doc.warehouse_code = str(int(parent_wh_code)+1).zfill(4)

    else:
        new_warehouse_code = frappe.db.sql("select warehouse_code+1 from `tabWarehouse` where parent ='{0}' order by warehouse_code desc limit 1".format(doc.parent_warehouse))
        if new_warehouse_code:
            new_warehouse_code_final = new_warehouse_code[0][0]
        else:
            new_warehouse_code_final = '1'
        doc.warehouse_code = str(int(new_warehouse_code_final)).zfill(4)

@frappe.whitelist()
def validate_item_group(doc, method):
    if doc.parent_item_group and doc.parent_item_group != 'All Item Group' and not doc.one_fm_item_group_descriptions:
        set_item_group_description_form_parent(doc)

@frappe.whitelist()
def before_insert_item(doc, method):
    if not doc.item_id:
        set_item_id(doc)
    if not doc.item_code:
        set_item_code(doc)

@frappe.whitelist()
def validate_item(doc, method):
    if not doc.item_barcode:
        doc.item_barcode = doc.item_code
    if not doc.parent_item_group:
        doc.parent_item_group = "All Item Groups"
    set_item_description(doc)

def set_item_id(doc):
    next_item_id = "0000"
    item_id = get_item_id_series("All Item Groups", doc.subitem_group, doc.item_group)
    if item_id:
        next_item_id = str(int(item_id)+1)
        for i in range(0, 4-len(next_item_id)):
            next_item_id = '0'+next_item_id
    doc.item_id = next_item_id

def set_item_code(doc):
    if doc.item_id:
        doc.item_code = get_item_code("All Item Groups", doc.subitem_group, doc.item_group, doc.item_id)

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
    if parent.one_fm_item_group_descriptions:
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
def get_item_id_series(parent_item_group, subitem_group, item_group):
    previous_item_id = frappe.db.sql("select item_id from `tabItem` where parent_item_group='{0}' and subitem_group='{1}' and item_group='{2}' order by item_id desc".format(parent_item_group, subitem_group, item_group))
    if previous_item_id:
        return previous_item_id[0][0]
    else:
        return '0000'

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
    validate_transferable_field(doc)
    set_job_applicant_fields(doc)
    if not doc.one_fm_is_easy_apply:
        validate_mandatory_fields(doc)
    set_job_applicant_status(doc, method)
    set_average_score(doc, method)
    # if doc.is_new():
    #     set_childs_for_application_web_form(doc, method)
    if frappe.session.user != 'Guest' and not doc.one_fm_is_easy_apply:
        validate_mandatory_childs(doc)
    if doc.one_fm_applicant_status in ["Shortlisted", "Selected"]:
        create_job_offer_from_job_applicant(doc.name)

def validate_transferable_field(doc):
    if doc.one_fm_applicant_is_overseas_or_local != 'Local':
        doc.one_fm_is_transferable = ''
    if doc.one_fm_is_transferable == 'No':
        doc.status = 'Rejected'

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
        source_of_hire = 'Overseas'
        if doc.one_fm_source_of_hire == 'Local':
            source_of_hire = 'Local'
        elif doc.one_fm_source_of_hire == 'Local and Overseas' and doc.one_fm_have_a_valid_visa_in_kuwait and doc.one_fm_visa_type:
            source_of_hire = 'Local'
        filters['source_of_hire'] = source_of_hire
        if source_of_hire == 'Local' and doc.one_fm_visa_type:
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
                {'University':'one_fm_university'}]

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
    if doc.one_fm_erf:
        field_list = []
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
    set_salary_details(job_offer, erf)
    set_other_benefits_to_terms(job_offer, erf)

def set_salary_details(job_offer, erf):
    job_offer.one_fm_provide_salary_advance = erf.provide_salary_advance
    total_amount = 0
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
        {'provide_company_insurance': 'Company Insurance'}]
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
