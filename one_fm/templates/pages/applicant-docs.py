import os, io
from google.cloud import vision
import frappe
from frappe.utils import cstr
import json
import frappe.sessions
import base64
import datetime
import hashlib

from dateutil.parser import parse


@frappe.whitelist(allow_guest=True)
def populate_nationality():
    return frappe.get_list('Nationality', pluck='name')

@frappe.whitelist(allow_guest=True)
def fetch_nationality(code):
    country = frappe.get_value('Country', {'code_alpha3':code},["country_name"])
    return frappe.get_value('Nationality', {'country':country},["name"])


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
        
        #initialize google vision client library
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cstr(frappe.local.site) + frappe.local.conf.google_application_credentials
        client = vision.ImageAnnotatorClient()
       
        front_civil = frappe.local.form_dict['front_civil']
        back_civil = frappe.local.form_dict['back_civil']
        is_kuwaiti = frappe.local.form_dict['is_kuwaiti']

        # Load the Images

        front_image_path = upload_image(front_civil,"image1.png")
        back_image_path = upload_image(back_civil,"image2.png")

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
    print(texts[0].description)

    for index in range(1,len(texts)):
        assemble[index] = texts[index].description
    
    if is_kuwaiti == 1:
        result["Civil_ID_No"] = texts[find_index(assemble,"CARD")+1].description
        result["Country_Code"] = texts[find_index(assemble,"Nationality")+1].description
        result["Date_Of_Birth"] = datetime.datetime.strptime(texts[find_index(assemble,"Birth")+2].description, '%d/%m/%Y').strftime('%Y-%m-%d')
        result["Expiry_Date"] = datetime.datetime.strptime(texts[find_index(assemble,"Birth")+3].description, '%d/%m/%Y').strftime('%Y-%m-%d')
        if texts[find_index(assemble,"Sex")-1].description == "M" or texts[find_index(assemble,"Sex")-1].description == "F":
            result["Gender"] = texts[find_index(assemble,"Sex")-1].description
        else:
            result["Gender"] = ""

        result["Name"] = ""
        for i in range(find_index(assemble,"Name")+1,find_index(assemble,"Nationality")-2):
            result["Name"] = result["Name"] + texts[i].description + " "
        
        result["Arabic_Name"]= ""
        for i in range(find_index(assemble,"No")+1,find_index(assemble,"Name")-1):
            result["Arabic_Name"] = result["Arabic_Name"] + texts[i].description + " "

    else:
        result["Civil_ID_No"] = texts[find_index(assemble,"Civil")+3].description
        result["Country_Code"] = texts[find_index(assemble,"Nationality")+1].description
        result["Date_Of_Birth"] = datetime.datetime.strptime(texts[find_index(assemble,"لجن")+1].description, '%d/%m/%Y').strftime('%Y-%m-%d')
        result["Expiry_Date"] = datetime.datetime.strptime(texts[find_index(assemble,"لجن")+2].description, '%d/%m/%Y').strftime('%Y-%m-%d')
        result["Passport_Number"] = texts[find_index(assemble,"Nationality")+2].description
        result["Gender"] = ""
        if texts[find_index(assemble,"Sex")+1].description == "M" or texts[find_index(assemble,"Sex")+1].description == "F":
            result["Gender"] = texts[find_index(assemble,"Sex")+1].description

        result["Name"] = ""
        for i in range(find_index(assemble,"Name")+1,find_index(assemble,"Passport")):
            result["Name"] = result["Name"] + texts[i].description + " "
        
        result["Arabic_Name"]= ""
        for i in range(find_index(assemble,"الرقه")+1,find_index(assemble,"Name")):
            result["Arabic_Name"] = result["Arabic_Name"] + texts[i].description + " "
            
        result["Arabic_Name"] = result["Arabic_Name"][::-1]
    
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
        if find_index(assemble, "(") and find_index(assemble, ")"):
            for i in range(find_index(assemble,")")+1,find_index(assemble,"العنوان:")):
                result["Sponsor_Name"] = result["Sponsor_Name"] + texts[i].description + " "
                
            result["Sponsor_Name"] = result["Sponsor_Name"][::-1]
    
    return result

@frappe.whitelist(allow_guest=True)
def get_passport_text():
    try:
        result = {}
        
        #initialize google vision client library
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cstr(frappe.local.site) + frappe.local.conf.google_application_credentials
        client = vision.ImageAnnotatorClient()
        
        front_passport = frappe.local.form_dict['front_passport']
        back_passport = frappe.local.form_dict['back_passport']

        front_image_path = upload_image(front_passport,hashlib.md5(front_passport.encode('utf-8')).hexdigest())
        back_image_path = upload_image(back_passport,hashlib.md5(back_passport.encode('utf-8')).hexdigest())

        front_text = get_passport_front_text(front_image_path, client)
        back_text = get_passport_back_text(back_image_path, client)
        
        result.update({'front_text': front_text})
        result.update({'back_text': back_text})
        
        return result
    
    except Exception as e:
        frappe.throw(e)

def get_passport_front_text(image_path, client):
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)  # returns TextAnnotation

    texts = response.text_annotations
    
    result = {}
    assemble = {}
    index = 0
    
    for index in range(1,len(texts)):
        assemble[index] = texts[index].description
        
    text_length = len(texts)
    print(text_length)
    fuzzy = False
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

def upload_image(image, filename):
    """ This method writes a file to a server directory
    Args:
        image (str): Base64 encoded image
        filename (str): Name of the file
    Returns:
        str: Path to uploaded image
    """
    content = base64.b64decode(image)
    image_path = cstr(frappe.local.site)+"/private/files/user/"+filename

    with open(image_path, "wb") as fh:
        fh.write(content)
    
    return image_path