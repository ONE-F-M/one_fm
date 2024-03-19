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

# initialize mindee

@frappe.whitelist(allow_guest=True)
def get_magic_link():
    """
    Get magic link and decrypt, return the doc
    """
    result = {}
    try:
        url = frappe.utils.get_url()
        if frappe.form_dict.magic_link:
            decrypted_magic_link = decrypt(frappe.form_dict.magic_link)
            if (frappe.db.exists("Magic Link", {'name':decrypted_magic_link})):
                magic_link = frappe.get_doc("Magic Link", {'name':decrypted_magic_link})
                if magic_link.expired:
                    result = {}
                else:
                    job_applicant = frappe.get_doc('Job Applicant', magic_link.reference_docname)
                    # get other required data like nationality, gender, ...
                    civil_id_required = True if job_applicant.one_fm_nationality=='Kuwaiti' else False
                    civil_id_required = True if job_applicant.one_fm_have_a_valid_visa_in_kuwait else False 
                    result['civil_id_required'] = civil_id_required
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
                    educations = frappe.get_meta("Job Applicant").get_field("one_fm_educational_qualification").options
                    result['education'] = list(educations.split("\n"))
                    result['attachments'] = []
                    if job_applicant.passport_data_page:
                        result['attachments'].append({
                            'name':job_applicant.passport_data_page,
                            'image':url+job_applicant.passport_data_page,
                            'id':'passport_data_page',
                            'placeholder':'Passport Data Page'
                        })
                    if job_applicant.civil_id_front:
                        result['attachments'].append({
                            'name':job_applicant.civil_id_front,
                            'image':url+job_applicant.civil_id_front if job_applicant.civil_id_front else '',
                            'id':'civil_id_front',
                            'placeholder':'Civil ID Front'
                        })
                    if job_applicant.civil_id_back:
                        result['attachments'].append({
                            'name':job_applicant.civil_id_back,
                            'image':url+job_applicant.civil_id_back,
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
    file_path = cstr(frappe.local.site)+"/public/files/user/magic_link/"

    # Check if the directory exists
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    full_path = bench_path+'/sites/'+file_path
    applicant_name = frappe.db.get_value(frappe.form_dict.reference_doctype, frappe.form_dict.reference_docname, 'applicant_name')
    response_data = {}
    errors = []
    # process passport
    reference_doctype = frappe.form_dict.reference_doctype
    reference_docname = frappe.form_dict.reference_docname
    if frappe.form_dict.passport_data_page:
        data_content = frappe._dict(frappe.form_dict.passport_data_page)
        data = data_content.data
        filename = "passport-"+applicant_name+"_"+hashlib.md5(str(datetime.datetime.now()).encode('utf-8')).hexdigest()[:5]+"-"+data_content.name
        content = base64.b64decode(data)
        with open(full_path+filename, "wb") as fh:
            fh.write(content)
        # append to File doctype
        file_url = "/files/user/magic_link/"+filename
        filedoc = frappe.get_doc({
            "doctype":"File", 
            "is_private":0,
            "file_url":"/files/user/magic_link/"+filename, 
            "attached_to_doctype":frappe.form_dict.reference_doctype, 
            "attached_to_name":frappe.form_dict.reference_docname
        }).insert(ignore_permissions=True)
        filedoc.db_set('file_url', file_url)
        frappe.db.set_value(reference_doctype, reference_docname, 'passport_data_page', file_url)
        frappe.db.commit()
        absolute_path = bench_path+'/sites/'+cstr(frappe.local.site)+'/public/files/'+filename
        if os.path.isfile(absolute_path):
            os.remove(absolute_path)

        # delete existing files
        delete_existing_files(reference_doctype, reference_docname, f"%/files/user/magic_link/passport-{applicant_name}_%", filedoc.name)

        # get data from mindee
        try:
            mindee_client = Client(api_key=frappe.local.conf.mindee_passport_api)
            input_doc = mindee_client.doc_from_path(full_path+filename)
            result = input_doc.parse(documents.TypePassportV1)
            # Print a brief summary of the parsed data
            mindee_doc = result.document
            result_dict = frappe._dict(dict(
                birth_place=mindee_doc.birth_place.value,
                expiry_date=mindee_doc.expiry_date.value,
                full_name=mindee_doc.full_name.value,
                given_names=[i.value for i in mindee_doc.given_names],
                is_expired=mindee_doc.is_expired(),
                mrz=mindee_doc.mrz.value,
                mrz1=mindee_doc.mrz1.value,
                mrz2=mindee_doc.mrz2.value,
                type=mindee_doc.type,
                birth_date=mindee_doc.birth_date.value,
                country=mindee_doc.country.value,
                gender=mindee_doc.gender.value,
                id_number=mindee_doc.id_number.value,
                issuance_date=mindee_doc.issuance_date.value,
                surname=mindee_doc.surname.value
            ))
            # result_dict = frappe._dict({'birth_place': 'ORAIFITE', 'expiry_date': '2033-02-06', 'full_name': 'EMMANUEL ANTHONY', 'given_names': ['EMMANUEL', 'CHIEMEKA'], 'is_expired': False, 'mrz': 'P<NGAANTHONY<<EMMANUEL<CHIEMEKA<<<<<<<<<<<<<B504093262NGA9303070M330206070324917405<<<46', 'mrz1': 'P<NGAANTHONY<<EMMANUEL<CHIEMEKA<<<<<<<<<<<<<', 'mrz2': 'B504093262NGA9303070M330206070324917405<<<46', 'type': 'passport', 'birth_date': '1993-03-07', 'country': 'NGA', 'gender': 'M', 'id_number': 'B50409326', 'issuance_date': '2023-02-07', 'surname': 'ANTHONY'})
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
                    frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_last_name', v.title())
                    frappe.db.set_value(reference_doctype, reference_docname, 'applicant_name', frappe.db.get_value(reference_doctype, reference_docname, 'one_fm_first_name').title() + ' ' + v.title())
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
                            frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_first_name', j.title())
                        if i==1:
                            frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_second_name', j.title())
                        if i==2:
                            frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_third_name', j.title())
                        if i==3:
                            frappe.db.set_value(reference_doctype, reference_docname, 'one_fm_forth_name', j.title())
            response_data['passport']=result_dict
            # return frappe._dict()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Mindee-Passport")
            errors.append("We could not process your passport document.")
        
    # civil id front
    if frappe.form_dict.civil_id_front:
        data_content = frappe._dict(frappe.form_dict.civil_id_front)
        reference_doctype = frappe.form_dict.reference_doctype
        reference_docname = frappe.form_dict.reference_docname
        data = data_content.data
        filename = "civil_id_front-"+applicant_name+"_"+hashlib.md5(str(datetime.datetime.now()).encode('utf-8')).hexdigest()[:5]+"-"+data_content.name
        content = base64.b64decode(data)
        with open(full_path+filename, "wb") as fh:
            fh.write(content)
        # append to File doctype
        file_url = "/files/user/magic_link/"+filename
        filedoc = frappe.get_doc({
            "doctype":"File", 
            "is_private":0,
            "file_url":"/files/user/magic_link/"+filename, 
            "attached_to_doctype":frappe.form_dict.reference_doctype, 
            "attached_to_name":frappe.form_dict.reference_docname
        }).insert(ignore_permissions=True)
        filedoc.db_set('file_url', file_url)
        frappe.db.set_value(reference_doctype, reference_docname, 'civil_id_front', file_url)
        frappe.db.commit()
        absolute_path = frappe.utils.get_bench_path()+'/sites/'+cstr(frappe.local.site)+'/public/files/'+filename
        if os.path.isfile(absolute_path):
            os.remove(absolute_path)

        # delete existing files
        delete_existing_files(reference_doctype, reference_docname, f"%/files/user/magic_link/civil_id_front-{applicant_name}_%", filedoc.name)

        # process file detection
        try:
            # Init a new client and add your custom endpoint (document)
            mindee_client = Client(api_key=frappe.local.conf.mindee_passport_api).add_endpoint(
                account_name="onefm",
                endpoint_name="kuwait_civil_id_front",
            )

            # Load a file from disk and parse it.
            # The endpoint name must be specified since it cannot be determined from the class.
            result = mindee_client.doc_from_path(
                frappe.utils.get_bench_path()+'/sites/'+cstr(frappe.local.site)+'/public/'+file_url
            ).parse(documents.TypeCustomV1, endpoint_name="kuwait_civil_id_front")

            civil_id_front = {} #{'birth_date': '1999-12-28', 'civil_id_no': '299122801358', 'expiry_date': '2028-01-30', 'name': 'ALI', 'nationality': 'KWT', 'passport_number': '', 'sex': ''}
            # Iterate over all the fields in the document
            for field_name, field_values in result.document.fields.items():
                civil_id_front[field_name] = str(field_values)
            response_data['civil_id_front']=civil_id_front
            # update record
            job_applicant = frappe.get_doc(reference_doctype, reference_docname)
            if civil_id_front.get('birth_date'):job_applicant.db_set('one_fm_date_of_birth', civil_id_front.get('birth_date'))
            if civil_id_front.get('civil_id_no'):job_applicant.db_set('one_fm_cid_number', civil_id_front.get('civil_id_no'))
            if civil_id_front.get('expiry_date'):job_applicant.db_set('one_fm_cid_expire', civil_id_front.get('expiry_date'))
            if civil_id_front.get('name'):job_applicant.db_set('applicant_name', civil_id_front.get('name'))
            if civil_id_front.get('passport_number'):job_applicant.db_set('one_fm_passport_number', civil_id_front.get('passport_number'))
            if civil_id_front.get('sex'):
                if civil_id_front.get('sex')=='M':sex="Male"
                elif civil_id_front.get('sex')=="F":sex="Female"
                else:sex="Other"
                job_applicant.db_set('one_fm_gender', sex)
            if civil_id_front.get('nationality'):
                country_code = civil_id_front.get('nationality')
                country = frappe.db.get_value("Country", {'code_alpha3':country_code}, 'name')
                if not country:
                    country = frappe.db.get_value("Country", {'code':country_code}, 'name')
                if country:
                    if country=='Kuwait':
                        nationality = 'Kuwaiti'
                    else:
                        nationality = frappe.db.get_value("Nationality", {'country':country}, 'name')
                    job_applicant.db_set('one_fm_nationality', nationality)
                    job_applicant.db_set('country', country)

            frappe.db.commit()

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Mindee-Civil ID")
            errors.append("We could not process your Civil ID document.")

    # civil id Back
    if frappe.form_dict.civil_id_back:
        data_content = frappe._dict(frappe.form_dict.civil_id_back)
        reference_doctype = frappe.form_dict.reference_doctype
        reference_docname = frappe.form_dict.reference_docname
        data = data_content.data
        filename = "civil_id_back-"+applicant_name+"_"+hashlib.md5(str(datetime.datetime.now()).encode('utf-8')).hexdigest()[:5]+"-"+data_content.name
        content = base64.b64decode(data)
        with open(full_path+filename, "wb") as fh:
            fh.write(content)
        # append to File doctype
        file_url = "/files/user/magic_link/"+filename
        filedoc = frappe.get_doc({
            "doctype":"File", 
            "is_private":0,
            "file_url":"/files/user/magic_link/"+filename, 
            "attached_to_doctype":frappe.form_dict.reference_doctype, 
            "attached_to_name":frappe.form_dict.reference_docname
        }).insert(ignore_permissions=True)
        filedoc.db_set('file_url', file_url)
        frappe.db.set_value(reference_doctype, reference_docname, 'civil_id_back', file_url)
        frappe.db.commit()
        absolute_path = frappe.utils.get_bench_path()+'/sites/'+cstr(frappe.local.site)+'/public/files/'+filename
        if os.path.isfile(absolute_path):
            os.remove(absolute_path)

        # delete existing files
        delete_existing_files(reference_doctype, reference_docname, f"%/files/user/magic_link/civil_id_back-{applicant_name}_%", filedoc.name)

        # process file detection
        response_data['civil_id_back']={'done':True} #fake response

    return frappe._dict({**response_data, **{'errors':errors}})

       
def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False
    
def delete_existing_files(reference_doctype,reference_docname, file_url_filter, newly_created_docname):
    bench_path = frappe.utils.get_bench_path()
    try:
        files = frappe.get_all("File", filters={"is_private":0,"attached_to_doctype":reference_doctype, "attached_to_name":reference_docname, "file_url": ["like", file_url_filter], "name": ["!=", newly_created_docname]}, fields=["name", "file_url"])

        for f in files:
            frappe.delete_doc("File", f.name)

            doc_file_url = bench_path+'/sites/'+cstr(frappe.local.site)+'/public/'+f.file_url
            if os.path.isfile(doc_file_url):
                os.remove(doc_file_url)

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error deleting existing files")


@frappe.whitelist(allow_guest=True)
def update_job_applicant():
    try:
        data = frappe.form_dict

        # All fields for name
        name_fields = ['applicant_name', 'one_fm_first_name', 'one_fm_second_name', 'one_fm_third_name', 'one_fm_forth_name', 'one_fm_last_name']

        # If updated field is a name field then convert it into title case
        if data.field in name_fields:
            data.value = data.value.title()

        # Update field
        frappe.db.set_value(data.doctype, data.docname, data.field, data.value)

        if data.field=='one_fm_last_name':
            frappe.db.set_value(data.doctype, data.docname, 'applicant_name', frappe.db.get_value(data.doctype, data.docname, 'one_fm_first_name') + ' ' + data.value)
        if data.field=='one_fm_first_name':
            frappe.db.set_value(data.doctype, data.docname, 'applicant_name', data.value+' '+frappe.db.get_value(data.doctype, data.docname, 'one_fm_last_name'))
    except Exception as e:
        return {'error':str(e)}

    return {'msg':'success'}


@frappe.whitelist(allow_guest=True)
def submit_job_applicant(job_applicant):
    try:
        set_expire_magic_link('Job Applicant', job_applicant, 'Job Applicant')
        return {'msg':'Your application has been successfully submitted, we will be intouch soonest.'}
    except Exception as e:
        return {'error':e}