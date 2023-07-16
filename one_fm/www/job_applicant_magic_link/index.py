import os, io, base64, datetime, hashlib, frappe, json, hashlib
from PIL import Image
from google.cloud import vision
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
        url = 'http://localhost:8003' #frappe.utils.get_url()
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
                    attachments = [i for i in 
                        frappe.db.get_all("File", {'attached_to_doctype':job_applicant.doctype, 
                                'attached_to_name':job_applicant.name}, "*") 
                        if (i.file_name.startswith('passport-') or i.file_name.startswith('civil_id_'))
                    ]
                    result['attachments'] = []
                    for i in attachments:
                        if i.file_name.startswith("passport-"):
                            result['attachments'].append({
                                'name':i.file_name,
                                'image':url+i.file_url,
                                'id':'passport_data_page',
                                'placeholder':'Passport Data Page'
                            })
                        elif i.file_name.startswith("civil_id_front-"):
                            result['attachments'].append({
                                'name':i.file_name,
                                'image':url+i.file_url,
                                'id':'civil_id_front',
                                'placeholder':'Civil ID Front'
                            })
                        elif i.file_name.startswith("civil_id_back-"):
                            result['attachments'].append({
                                'name':i.file_name,
                                'image':url+i.file_url,
                                'id':'civil_id_back',
                                'placeholder':'Civil ID Back'
                            })
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
    bench_path = frappe.utils.get_bench_path()
    file_path = cstr(frappe.local.site)+"/private/files/user/magic_link/"
    full_path = bench_path+'/sites/'+file_path

    # process passport
    if frappe.form_dict.passport_data_page:
        data_content = frappe._dict(frappe.form_dict.passport_data_page)
        reference_doctype = frappe.form_dict.reference_doctype
        reference_docname = frappe.form_dict.reference_docname
        data = data_content.data
        filename = "passport-"+hashlib.md5(str(datetime.datetime.now()).encode('utf-8')).hexdigest()+"-"+data_content.name
        # content = base64.b64decode(data)
        # with open(full_path+filename, "wb") as fh:
        #     fh.write(content)
        # # append to File doctype
        # filedoc = frappe.get_doc({
        #     "doctype":"File", 
        #     "is_private":1,
        #     "file_url":"/private/files/user/magic_link/"+filename, 
        #     "attached_to_doctype":frappe.form_dict.reference_doctype, 
        #     "attached_to_name":frappe.form_dict.reference_docname
        # }).insert(ignore_permissions=True)
        # frappe.db.commit()
        # get data from mindee
        try:
            # mindee_client = Client(api_key=frappe.local.conf.mindee_passport_api)
            # input_doc = mindee_client.doc_from_path(full_path+filename)
            # result = input_doc.parse(documents.TypePassportV1)
            # # Print a brief summary of the parsed data
            # mindee_doc = result.document
            # result_dict = frappe._dict(dict(
            #     birth_place=mindee_doc.birth_place.value,
            #     expiry_date=mindee_doc.expiry_date.value,
            #     full_name=mindee_doc.full_name.value,
            #     given_names=[i.value for i in mindee_doc.given_names],
            #     is_expired=mindee_doc.is_expired(),
            #     mrz=mindee_doc.mrz.value,
            #     mrz1=mindee_doc.mrz1.value,
            #     mrz2=mindee_doc.mrz2.value,
            #     type=mindee_doc.type,
            #     birth_date=mindee_doc.birth_date.value,
            #     country=mindee_doc.country.value,
            #     gender=mindee_doc.gender.value,
            #     id_number=mindee_doc.id_number.value,
            #     issuance_date=mindee_doc.issuance_date.value,
            #     surname=mindee_doc.surname.value
            # ))
            result_dict = frappe._dict({'birth_place': 'ORAIFITE', 'expiry_date': '2033-02-06', 'full_name': 'EMMANUEL ANTHONY', 'given_names': ['EMMANUEL', 'CHIEMEKA'], 'is_expired': False, 'mrz': 'P<NGAANTHONY<<EMMANUEL<CHIEMEKA<<<<<<<<<<<<<B504093262NGA9303070M330206070324917405<<<46', 'mrz1': 'P<NGAANTHONY<<EMMANUEL<CHIEMEKA<<<<<<<<<<<<<', 'mrz2': 'B504093262NGA9303070M330206070324917405<<<46', 'type': 'passport', 'birth_date': '1993-03-07', 'country': 'NGA', 'gender': 'M', 'id_number': 'B50409326', 'issuance_date': '2023-02-07', 'surname': 'ANTHONY'})
            country_code = frappe.db.get_value("Country", {'code_alpha3':result_dict.country}, 'name')
            if not country_code:
                country_code = frappe.db.get_value("Country", {'code':result_dict.country}, 'name')
            if country_code:
                result_dict.country = country_code
            # 'passport_file':filedoc.as_dict()
            
            for k, v in dict(result_dict).items():
                if(k=="country") and v:
                    frappe.db.set_value(frappe.form_dict.reference_doctype, frappe.form_dict.reference_docname, k, country_code)
                    frappe.db.set_value(frappe.form_dict.reference_doctype, frappe.form_dict.reference_docname, 'one_fm_passport_holder_of', country_code)
                if(k=="gender" and v):
                    if v=="M":v="Male"
                    elif v=="F":v="Female"
                    else:v="Other"
                    frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_gender', v)
                if(k=="surname" and v):
                    frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_last_name', v)
                    frappe.db.set_value(reference_doctype, reference_docname, 'applicant_name', frappe.db.get_value(reference_doctype, reference_docname, 'one_fm_first_name') + ' ' + v)
                if(k=="birth_date" and v):
                    frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_date_of_birth', v)
                if(k=="id_number" and v):
                    frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_passport_number', v)
                if(k=="issuance_date" and v):
                    frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_passport_issued', v)
                if(k=="expiry_date" and v):
                    frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_passport_expire', v)
                if(k=="given_names" and v):
                    for i, j in enumerate(v):
                        if i==0:
                            frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_first_name', j)
                        if i==1:
                            frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_second_name', j)
                        if i==2:
                            frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_third_name', j)
                        if i==3:
                            frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_forth_name', j)
            return frappe._dict({'mindee':result_dict})
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Mindee")
            return frappe._dict({})
        

    return {}

@frappe.whitelist(allow_guest=True)
def update_job_applicant():
    try:
        data = frappe.form_dict
        frappe.db.set_value(data.doctype, data.docname, data.field, data.value)
        if data.field=='one_fm_last_name':
            frappe.db.set_value(data.doctype, data.docname, 'applicant_name', frappe.db.get_value(data.doctype, data.docname, 'one_fm_first_name') + ' ' + data.value)
        if data.field=='one_fm_first_name':
            frappe.db.set_value(data.doctype, data.docname, 'applicant_name', data.value+' '+frappe.db.get_value(data.doctype, data.docname, 'one_fm_first_name'))
    except Exception as e:
        return {'error':str(e)}

    return {'msg':'success'}