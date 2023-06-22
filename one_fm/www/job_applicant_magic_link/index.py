from google.cloud import vision
import os, io, base64, datetime, hashlib, frappe, json
from frappe.utils import cstr
import frappe.sessions
from mindee import Client, documents

from dateutil.parser import parse
from frappe import _
from frappe.utils.password import decrypt
from frappe.model.document import Document
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link
from one_fm.utils import set_expire_magic_link


@frappe.whitelist(allow_guest=True)
def get_magic_link():
    """
    Get magic link and decrypt, return the doc
    """
    result = {}
    try:
        
        if frappe.form_dict.magic_link:
            decrypted_magic_link = decrypt(frappe.form_dict.magic_link)
            if (frappe.db.exists("Magic Link", {'name':decrypted_magic_link})):
                magic_link = frappe.get_doc("Magic Link", {'name':decrypted_magic_link})
                if magic_link.expired:
                    result = {}
                else:
                    job_applicant = frappe.get_doc('Job Applicant', magic_link.reference_docname)
                    # get other required data like nationality, gender, ...
                    nationalities = frappe.get_all("Nationality", fields=["name as nationality", "nationality_arabic", "country"])
                    nationalities_dict = {}
                    for i in nationalities:
                        nationalities_dict[i.country] = i
                    countries = frappe.get_all("Country", fields=["name", "code", "code_alpha3", "country_name", "one_fm_country_name_arabic",
                        "time_zones"])
                    countries_dict = {}
                    for i in countries:
                        countries_dict[i.name] = i
                        if nationalities_dict.get(i.name):
                           countries_dict[i.name] = {**countries_dict[i.name], **nationalities_dict.get(i.name)} 

                    result['job_applicant'] = job_applicant
                    result['nationalities'] = nationalities_dict
                    result['countries'] = countries_dict
                    result['genders'] = [i.name for i in frappe.get_all("Gender")]
                    result['religions'] = [i.name for i in frappe.get_all("Religion")]
            else:
                result = {}
        else:
            result = {}

        return result
    except:
        frappe.log_error(frappe.get_traceback(), 'Magic Link')
        return result

@frappe.whitelist(allow_guest=True)
def upload_image():
    print(frappe.form_dict)

    return {}
