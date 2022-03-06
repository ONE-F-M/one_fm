# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, nowdate, cint
import datetime
from datetime import date
from frappe.utils.data import flt, nowdate, getdate, cint
from frappe.utils import cint, cstr, flt, nowdate, comma_and, date_diff, getdate , add_days
import frappe, json
from frappe.utils.file_manager import save_file
from one_fm.processor import sendemail

no_cache = 1
no_sitemap = 1

def get_context(context):
    context.show_search = True


@frappe.whitelist(allow_guest=True)
def get_website_info_data():
    data = []
    about_us_info = frappe.get_doc("Website Info")
    data.append(about_us_info.section_title)
    data.append(about_us_info.section_header)

    about_us_content = frappe.db.sql(""" select font_icon,subject from `tabAbout Us Subject` order by idx """)
    data.append(about_us_content)

    our_vision = frappe.db.sql(""" select subject from `tabOur Vision` order by idx """)
    data.append(our_vision)

    our_mission = frappe.db.sql(""" select subject from `tabOur Mission` order by idx """)
    data.append(our_mission)

    data.append(about_us_info.services_title)

    services_content = frappe.db.sql(""" select font_icon,title,subject from `tabServices Subject` order by idx """)
    data.append(services_content)

    data.append(about_us_info.address)
    data.append(about_us_info.phone)
    data.append(about_us_info.email)

    data.append(about_us_info.facebook)
    data.append(about_us_info.youtube)
    data.append(about_us_info.twitter)
    data.append(about_us_info.instagram)

    return data



@frappe.whitelist(allow_guest=True)
def get_website_info_count():
    project_count = frappe.db.sql(""" select count(name) from `tabProject` """)[0][0]
    employee_count = frappe.db.sql(""" select count(name) from `tabEmployee` """)[0][0]
    sites_count = frappe.db.sql(""" select count(name) from `tabSite` """)[0][0]
    clients_count = frappe.db.sql(""" select count(name) from `tabCustomer` """)[0][0]
    return project_count, employee_count, sites_count, clients_count


@frappe.whitelist(allow_guest=True)
def get_clients_info():
    customer_image = []
    customer_name = []

    customers = frappe.db.sql(""" select image,customer_name from `tabCustomer` """)
    if customers:
        for customer in customers:
            customer_image.append(customer[0])
            customer_name.append(customer[1])
        return customer_image,customer_name
    else:
        return None


@frappe.whitelist(allow_guest=True)
def get_jobs_info():
    job_name = []
    job_title = []
    job_description = []

    jobs = frappe.db.sql(""" select name,job_title,description from `tabJob Opening` where status='Open' """)
    if jobs:
        for job in jobs:
            job_name.append(job[0])
            job_title.append(job[1])
            job_description.append(job[2])
        return job_name, job_title, job_description
    else:
        return None



@frappe.whitelist(allow_guest=True)
def add_new_job_applicant(job_opening, applicant_name, applicant_email, applicant_cover, applicant_files):
    if not frappe.db.exists("Job Applicant", {"job_title": job_opening, "email_id": applicant_email}) :
        doc = frappe.get_doc({
            "doctype":"Job Applicant",
            "job_title": job_opening,
            "applicant_name": applicant_name,
            "email_id": applicant_email,
            "cover_letter": applicant_cover
        })
        doc.insert(ignore_permissions=True)

        return 1, doc.name
    else:
        job_applicant_name = frappe.db.get_value("Job Applicant", {"job_title": job_opening, "email_id": applicant_email}, "name")

        return job_applicant_name


@frappe.whitelist(allow_guest=True)
def edit_job_applicant(job_applicant, job_opening, applicant_name, applicant_email, applicant_cover, applicant_files):
    doc = frappe.get_doc("Job Applicant", job_applicant)
    doc.flags.ignore_permissions = True
    doc.delete()

    applicant_doc = frappe.get_doc({
        "doctype":"Job Applicant",
        "job_title": job_opening,
        "applicant_name": applicant_name,
        "one_fm_first_name": applicant_name,
        "one_fm_last_name": applicant_name,
        "email_id": applicant_email,
        "cover_letter": applicant_cover
    })
    applicant_doc.insert(ignore_permissions=True)

    if applicant_files:
        fd_json = json.loads(applicant_files)
        print(fd_json)
        fd_list = list(fd_json["files_data"])
        for fd in fd_list:
            filedoc = save_file(fd["filename"], fd["dataurl"], "Job Applicant", applicant_doc.name, decode=True, is_private=1)

    return 1


@frappe.whitelist(allow_guest=True)
def send_contact_email(contact_name, contact_email, contact_subject, contact_message):

    sender = frappe.get_value("Email Account", filters = {"default_outgoing": 1}, fieldname = "email_id") or None

    # msg = frappe.render_template('client_customizer/templates/emails/employee_disclaimer.html', context={"page_link": page_link,"employee_name": emp_name})

    applied_subject =  "Thanks for contacting us"
    applied_msg =  "<b>We have received your email and our Customer Service team will be responding to you soon.</b>"

    message_details = """

        <b>Name:</b> {0}<br>
        <b>Email:</b> {1}<br>
        <b>Subject:</b> {2}<br>
        <hr stle='width:50%;'>
        <b>Message:</b><br><br>
        {3}

    """.format(contact_name, contact_email, contact_subject, contact_message)

    try:
        sendemail(sender=sender, recipients= 'omar.ja93@gmail.com',
            content=message_details, subject=contact_subject)

        sendemail(sender=sender, recipients= contact_email,
            content=applied_msg, subject=applied_subject)
        return 1
    except:
        return 0





@frappe.whitelist(allow_guest=True)
def attach_file_to_application(filedata, job_applicant_name):
    if filedata:
        fd_json = json.loads(filedata)

        # return filedata

        fd_list = list(fd_json["files_data"])
        for fd in fd_list:
            filedoc = save_file(fd["filename"], fd["dataurl"], "Job Applicant", job_applicant_name, decode=True, is_private=0)


@frappe.whitelist(allow_guest=True)
def request_new_quote(person_name, organization_name, quote_email, mobile_no, quote_notes):
    doc = frappe.get_doc({
        "doctype":"Lead",
        "lead_name": person_name,
        "company_name": organization_name,
        "email_id": quote_email,
        "mobile_no": mobile_no,
        "notes": quote_notes
    })
    doc.insert(ignore_permissions=True)

    if doc.name:
        return 1
    else:
        return 0
