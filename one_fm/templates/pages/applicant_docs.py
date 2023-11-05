from google.cloud import vision
import os, io, base64, datetime, hashlib, frappe, json
from frappe.utils import cstr
import frappe.sessions
from mindee import Client, documents


from dateutil.parser import parse
from frappe import _
from frappe.model.document import Document
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link
from one_fm.utils import set_expire_magic_link

def get_context(context):
    context.title = _("Job Applicant")
    magic_link = authorize_magic_link(frappe.form_dict.magic_link, 'Job Applicant', 'Job Applicant')
    if magic_link:
        # Find Job Applicant from the magic link
        job_applicant = frappe.get_doc('Job Applicant', frappe.db.get_value('Magic Link', magic_link, 'reference_docname'))
        context.job_applicant = job_applicant
        context.is_kuwaiti = context.civil_id_reqd = 0
        if job_applicant.one_fm_nationality == 'Kuwaiti':
            context.is_kuwaiti = 1
        if job_applicant.one_fm_have_a_valid_visa_in_kuwait == 1:
            context.civil_id_reqd = 1
        context.applicant_name = job_applicant.one_fm_first_name
        context.applicant_designation = job_applicant.designation
        context.email_id = job_applicant.one_fm_email_id

@frappe.whitelist(allow_guest=True)
def populate_nationality():
    return frappe.get_list('Nationality', pluck='name', ignore_permissions=True)

@frappe.whitelist(allow_guest=True)
def fetch_nationality(code):
    country = frappe.get_value('Country', {'code_alpha3':code},["country_name"])
    return frappe.get_value('Nationality', {'country':country},["name"])

@frappe.whitelist(allow_guest=True)
def populate_country():
    return frappe.get_list('Country', pluck='name', ignore_permissions=True)
    
@frappe.whitelist(allow_guest=True)
def token():
    return frappe.local.session.data.csrf_token

@frappe.whitelist(allow_guest=True)
def get_civil_id_text():
    """This API redirects the image fetched from frontend and
    runs it though Google Vision API, each side at a time.

    Args:
        images (json): Consist of two base64 encoded strings(front_side, back_side).
        is_kuwaiti (int): 0 for non-Kuwaiti and 1 for Kuwaiti

    Returns:
        result: dictionary consisting of text fetched from both front and back side.
    """
    try:

        result = {}

        # initialize google vision client library
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cstr(frappe.local.site) + frappe.local.conf.google_application_credentials
        client = vision.ImageAnnotatorClient()

        front_civil = frappe.local.form_dict['front_civil']
        back_civil = frappe.local.form_dict['back_civil']
        is_kuwaiti = frappe.local.form_dict['is_kuwaiti']
        magic_link = frappe.form_dict.magic_link

        # Load images
        front_image_path = upload_image(front_civil, "front_civil-"+hashlib.md5(str(datetime.datetime.now()).encode('utf-8')).hexdigest(), magic_link)
        back_image_path = upload_image(back_civil, "back_civil-"+hashlib.md5(str(datetime.datetime.now()).encode('utf-8')).hexdigest(), magic_link)

        front_text = get_front_side_civil_id_text(front_image_path, client, is_kuwaiti)
        back_text = get_back_side_civil_id_text(back_image_path, client, is_kuwaiti)

        result.update({'front_text': front_text})
        result.update({'back_text': back_text})
        return result

    except Exception as e:
        frappe.throw(e)

def get_front_side_civil_id_text(image_path, client, is_kuwaiti):
    """ This method fetches the image from the provided image path, calls the vision api to exrtract text from the image
        and parses through the obtained texts to get relevant texts for the required fields in the front side of the civil ID.

    Args:
        image_path (str): Path to image file
        client (obj): Vision API client library object
        is_kuwaiti (int): 0 for non-Kuwaiti and 1 for Kuwaiti

    Returns:
        dict: Dictionary of obtained texts for the required fields.
    """

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)  # returns TextAnnotation

    texts = response.text_annotations

    result = {}
    assemble = {}
    index = 0
    result["Civil_ID_Front"] = image_path

    for index in range(1,len(texts)):
        assemble[index] = texts[index].description

    if is_kuwaiti == 1:
        if find_index(assemble,"CARD"):
            result["Civil_ID_No"] = texts[find_index(assemble,"CARD")+1].description

        if find_index(assemble,"Nationality"):
            result["Country_Code"] = texts[find_index(assemble,"Nationality")+1].description

        if find_index(assemble,"Birth"):
            if is_date(texts[find_index(assemble,"Birth")+2].description):
                result["Date_Of_Birth"] = datetime.datetime.strptime(texts[find_index(assemble,"Birth")+2].description, '%d/%m/%Y').strftime('%Y-%m-%d')

            if is_date(texts[find_index(assemble,"Birth")+3].description):
                result["Expiry_Date"] = datetime.datetime.strptime(texts[find_index(assemble,"Birth")+3].description, '%d/%m/%Y').strftime('%Y-%m-%d')

        if find_index(assemble,"Sex"):
            if texts[find_index(assemble,"Sex")-1].description == "M" or texts[find_index(assemble,"Sex")-1].description == "F":
                result["Gender"] = texts[find_index(assemble,"Sex")-1].description
            else:
                result["Gender"] = ""

        result["First_Name"] = result["Last_Name"] = result["Second_Name"] =  result["Third_Name"] = Name = ""
        if find_index(assemble,"Name") and find_index(assemble,"Nationality"):
            for i in range(find_index(assemble,"Name")+1,find_index(assemble,"Nationality")-2):
                Name = Name + str(texts[i].description).capitalize() + " "
            Name = Name.split()
            result["First_Name"] = Name[0]
            result["Last_Name"] = Name[len(Name)] if len(Name) > 1 else ""
            result["Second_Name"] = Name[1] if len(Name) > 2 else ""
            result["Third_Name"] = Name[2] if len(Name) > 3 else ""

        result["First_Arabic_Name"] = result["Last_Arabic_Name"] = result["Second_Arabic_Name"] = result["Third_Arabic_Name"] = Ar_Name = ""
        if find_index(assemble,"No") and find_index(assemble,"Name"):
            for i in range(find_index(assemble,"No")+1,find_index(assemble,"Name")-1):
                Ar_Name = Ar_Name + texts[i].description + " "
            Ar_Name = Ar_Name.split()
            result["First_Arabic_Name"] = Name[0]
            result["Last_Arabic_Name"] = Name[len(Name)] if len(Name) > 1 else ""
            result["Second_Arabic_Name"] = Name[1] if len(Name) > 2 else ""
            result["Third_Arabic_Name"] = Name[2] if len(Name) > 3 else ""

    else:
        if find_index(assemble,"Civil"):
            result["Civil_ID_No"] = texts[find_index(assemble,"Civil")+3].description

        if find_index(assemble,"Nationality"):
            result["Country_Code"] = texts[find_index(assemble,"Nationality")+1].description
            result["Passport_Number"] = texts[find_index(assemble,"Nationality")-4].description

        if find_index(assemble,"Sex"):
            if is_date(texts[find_index(assemble,"Sex")+1].description):
                result["Date_Of_Birth"] = datetime.datetime.strptime(texts[find_index(assemble,"Sex")+1].description, '%d/%m/%Y').strftime('%Y-%m-%d')
            if is_date(texts[find_index(assemble,"Sex")+2].description):
                result["Expiry_Date"] = datetime.datetime.strptime(texts[find_index(assemble,"Sex")+2].description, '%d/%m/%Y').strftime('%Y-%m-%d')

            result["Gender"] = ""
            if texts[find_index(assemble,"Sex")+1].description == "M" or texts[find_index(assemble,"Sex")+1].description == "F":
                result["Gender"] = texts[find_index(assemble,"Sex")+1].description

        result["First_Name"] = result["Last_Name"] = result["Second_Name"] =  result["Third_Name"] = Name = ""
        if find_index(assemble,"Name") and find_index(assemble,"Passport"):
            for i in range(find_index(assemble,"Name")+1,find_index(assemble,"Passport") - 1):
                Name = Name + str(texts[i].description).capitalize() + " "
            name_list = Name.split()
            result["First_Name"] = name_list[0]
            result["Last_Name"] = name_list[len(name_list)-1] if len(name_list) >= 2   else ""
            result["Second_Name"] = name_list[1] if len(name_list) == 3 else ""
            result["Third_Name"] = name_list[2] if len(name_list) == 4 else ""

        result["First_Arabic_Name"] = result["Last_Arabic_Name"] = result["Second_Arabic_Name"] = result["Third_Arabic_Name"] = Ar_Name = ""
        if find_index(assemble,"الرقه") and find_index(assemble,"Name"):
            for i in range(find_index(assemble,"الرقه")+1,find_index(assemble,"Name")):
                Ar_Name = Ar_Name + texts[i].description + " "
            ar_name_list = Ar_Name.split()
            result["First_Arabic_Name"] = ar_name_list[0]
            result["Last_Arabic_Name"] = ar_name_list[len(ar_name_list)-1] if len(ar_name_list) >= 2 else ""
            result["Second_Arabic_Name"] = ar_name_list[1] if len(ar_name_list) == 3 else ""
            result["Third_Arabic_Name"] = ar_name_list[2] if len(ar_name_list) == 4 else ""

    return result

def get_back_side_civil_id_text(image_path, client, is_kuwaiti):
    """ This method fetches the image from the provided image path, calls the vision api to exrtract text from the image
        and parses through the obtained texts to get relevant texts for the required fields in the back side side of the civil ID.

    Args:
        image_path (str): Path to image file
        client (obj): Vision API client library object
        is_kuwaiti (int): 0 for non-Kuwaiti and 1 for Kuwaiti

    Returns:
        dict: Dictionary of obtained texts for the required fields.
    """

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)  # returns TextAnnotation

    texts = response.text_annotations

    result = {}
    assemble = {}
    index = 0
    result["Civil_ID_Back"] = image_path


    for index in range(1,len(texts)):
        assemble[index] = texts[index].description
    if is_kuwaiti == 1:
        if find_index(assemble,"all"):
            result["PACI_No"] = texts[find_index(assemble,"all")-1].description
        else:
            result["PACI_No"] = " "

    else:
        result["PACI_No"] = ""
        if find_index(assemble,"YI"):
            result["PACI_No"] = texts[find_index(assemble,"YI")-1].description

        result["Sponsor_Name"]= ""
        if find_index(assemble, "(") and find_index(assemble, ")") and find_index(assemble,"العنوان:"):
            for i in range(find_index(assemble,")")+1,find_index(assemble,"العنوان:")):
                result["Sponsor_Name"] = result["Sponsor_Name"] + texts[i].description + " "

            result["Sponsor_Name"] = result["Sponsor_Name"]

    return result

@frappe.whitelist(allow_guest=True)
def get_passport_text():
    try:
        result = {}
        magic_link = frappe.form_dict.magic_link
        front_passport = frappe.form_dict.front_passport
        # back_passport = frappe.form_dict.back_passport
        if front_passport:
            front_text = get_passport_data(upload_image(front_passport, "passport-"+hashlib.md5(str(datetime.datetime.now()).encode('utf-8')).hexdigest(), magic_link))
        else:
            front_text = {}

        result.update({'front_text': front_text})
        return result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Passport Reader")
        frappe.throw(e)


def get_passport_data(image_path):
    try:
        # Init a new client
        mindee_client = Client(api_key=frappe.local.conf.mindee_passport_api)
        # Load a file from disk
        input_doc = mindee_client.doc_from_path(image_path)
        # Parse the Passport by passing the appropriate type
        result = input_doc.parse(documents.TypePassportV1)
        # Print a brief summary of the parsed data
        doc = result.document
        result_dict = frappe._dict(dict(
            birth_place=doc.birth_place.value,
            expiry_date=doc.expiry_date.value,
            full_name=doc.full_name.value,
            given_names=[i.value for i in doc.given_names],
            is_expired=doc.is_expired(),
            mrz=doc.mrz.value,
            mrz1=doc.mrz1.value,
            mrz2=doc.mrz2.value,
            type=doc.type,
            birth_date=doc.birth_date.value,
            country=doc.country.value,
            gender=doc.gender.value,
            id_number=doc.id_number.value,
            issuance_date=doc.issuance_date.value,
            surname=doc.surname.value
        ))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Mindee")
        return frappe._dict({})
    return result_dict

def get_passport_front_text(image_path, client):
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)  # returns TextAnnotation
    f = open("demofilesg.txt", "a")
    f.write(str(response))
    f.close()
    texts = response.text_annotations
    
    result = {}
    assemble = {}
    index = 0

    for index in range(1,len(texts)):
        assemble[index] = texts[index].description

    text_length = len(texts)
    fuzzy = False
    result["Passport_Front"] = image_path

    if(text_length >= 5):
        if is_date(texts[text_length - 4].description, fuzzy):
            result["Passport_Date_of_Issue"] = datetime.datetime.strptime(texts[text_length - 4].description, '%d/%m/%Y').strftime('%Y-%m-%d')
        else:
            result["Passport_Date_of_Issue"] = ""
        if is_date(texts[text_length - 3].description, fuzzy):
            result["Passport_Date_of_Expiry"] = datetime.datetime.strptime(texts[text_length - 3].description, '%d/%m/%Y').strftime('%Y-%m-%d')
        else:
           result["Passport_Date_of_Expiry"] = ""

        mrz = texts[text_length - 1].description

        result["Passport_Number"] = mrz.split("<")[0]

    return result

def get_passport_back_text(image_path, client):
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)  # returns TextAnnotation
    

    texts = response.text_annotations
    result = {}
    assemble = {}
    index = 0
    result["Passport_Back"] = image_path

    for index in range(1,len(texts)):
        assemble[index] = texts[index].description

    result["Passport_Place_of_Issue"] = ""
    if find_index(assemble, "Place") and find_index(assemble, "of") and find_index(assemble, "Issue"):
        result["Passport_Place_of_Issue"] = texts[find_index(assemble, "Issue") + 3].description

    return result

def find_index(dictionary, word):
    for d in dictionary:
        if dictionary[d] == word:
            return d

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

def upload_image(image, filename, magic_link):
    """ This method writes a file to a server directory
    Args:
        image (str): Base64 encoded image
        filename (str): Name of the file
    Returns:
        str: Path to uploaded image
    """
    if not image:
        frappe.throw("Empty")
    content = base64.b64decode(image)
    file_path = "/private/files/user/"+filename + ".png"
    image_path = cstr(frappe.local.site)+file_path
    with open(image_path, "wb") as fh:
        fh.write(content)

    frappe.enqueue(attached_uploaded_image_to_job_applicant, file_path=file_path, magic_link=magic_link)
    return image_path

def attached_uploaded_image_to_job_applicant(file_path, magic_link):
    decrypted_magic_link = frappe.utils.password.decrypt(magic_link)
    if decrypted_magic_link:
        # Find Job Applicant from the magic link
        job_applicant = frappe.db.get_values('Magic Link', decrypted_magic_link, ['reference_docname', 'reference_doctype'], as_dict=1)
        if job_applicant:
            job_applicant = job_applicant[0]
            doc = frappe.get_doc({
                "doctype":"File", 
                "file_url":file_path, 
                "attached_to_doctype":job_applicant.reference_doctype, 
                "attached_to_name":job_applicant.reference_docname
            }).insert(ignore_permissions=True)
            frappe.db.commit()


@frappe.whitelist()
def send_applicant_doc_magic_link(job_applicant, applicant_name, designation):
    '''
        Method used to send the magic Link for Get More Details from the Job Applicant
        args:
            job_applicant: ID of the Job Applicant
            applicant_name: Name of the applicant
            designation: Designation applied
    '''
    applicant_email = frappe.db.get_value('Job Applicant', job_applicant, 'one_fm_email_id')
    # Check applicant have an email id or not
    if applicant_email:
        # Email Magic Link to the Applicant
        subject = "Fill More Details"
        url_prefix = "/applicant_docs?magic_link="
        msg = "<b>Please fill more information like your passport detail by clicking on the magic link below</b>\
            <br/>Applicant ID: {0}<br/>Applicant Name: {1}<br/>Designation: {2}</br>".format(job_applicant, applicant_name, designation)
        send_magic_link('Job Applicant', job_applicant, 'Job Applicant', [applicant_email], url_prefix, msg, subject)
    else:
        frappe.throw(_("No Email ID found for the Job Applicant"))

@frappe.whitelist(allow_guest=True)
def update_job_applicant(job_applicant, data):
    doc = update_application_function(job_applicant, data)
    doc.save(ignore_permissions=True)
    set_expire_magic_link('Job Applicant', job_applicant, 'Job Applicant')
    return True


@frappe.whitelist(allow_guest=True)
def save_as_draft(job_applicant, data):
    doc = update_application_function(job_applicant, data)
    doc.docstatus = 0
    doc.flags.ignore_validate = True
    doc.flags.ignore_mandatory = True
    doc.save(ignore_permissions=True)
    return True


@frappe.whitelist(allow_guest=True)
def update_application_function(job_applicant, data):
    new_doc = frappe.get_doc('Job Applicant', job_applicant)
    try:
        applicant_details = json.loads(data)

        for field in applicant_details:
            new_doc.set(field, applicant_details[field])
        for documents, path in applicant_details['applicant_doc'].items():
            new_doc.append("one_fm_documents_required", {
            "document_required": documents,
            "attach": frappe.get_value('File', {'file_name':path.split("\\")[-1]}, ["file_url"]),
            "type_of_copy": "Soft Copy",
            })
    except Exception as e:
        frappe.log_error(e, "Update Job Applicant (Magic Link)")
        
    return new_doc


@frappe.whitelist(allow_guest=True)
def get_uploaded_data(data: dict=None):
    if not isinstance(data, dict):
        data = json.loads(data)
    list_of_keys = []
    try:
        if len(data.keys()) > 0:
            for ind, val in enumerate(data.keys()):
                if ind == 0 and type(data[val]) == dict:
                    for key in data[val].keys():
                        list_of_keys.append(key)
                break
                    
    except:
        pass

    return list_of_keys


