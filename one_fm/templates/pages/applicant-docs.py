import os, io
from google.cloud import vision
import frappe
from frappe.utils import cstr
import json
import base64
import datetime
import hashlib

@frappe.whitelist(allow_guest=True)
def populate_nationality():
    return frappe.get_list('Nationality', pluck='name')

@frappe.whitelist(allow_guest=True)
def fetch_nationality(code):
    country = frappe.get_value('Country', {'code_alpha3':code},["country_name"])
    return frappe.get_value('Nationality', {'country':country},["name"])

@frappe.whitelist(allow_guest=True)
def get_civil_id_text(images, is_kuwaiti=0):
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
        
        # Load the Images
        image_files = json.loads(images)

        front_image_path = upload_image(image_files["front_side"],hashlib.md5((image_files["front_side"]).encode('utf-8')).hexdigest())
        back_image_path = upload_image(image_files["back_side"],hashlib.md5((image_files["back_side"]).encode('utf-8')).hexdigest())

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

    for index in range(1,len(texts)):
        assemble[index] = texts[index].description
    
    if is_kuwaiti:
        result["Civil ID No."] = texts[find_index(assemble,"CARD")+1].description
        result["Nationality"] = texts[find_index(assemble,"Nationality")+1].description
        result["Date Of Birth"] = datetime.datetime.strptime(texts[find_index(assemble,"Birth")+2].description, '%d/%m/%Y').strftime('%Y-%m-%d')
        result["Expiry Date"] = datetime.datetime.strptime(texts[find_index(assemble,"Birth")+3].description, '%d/%m/%Y').strftime('%Y-%m-%d')
        if texts[find_index(assemble,"Sex")-1].description == "M" or texts[find_index(assemble,"Sex")-1].description == "F":
            result["Gender"] = texts[find_index(assemble,"Sex")-1].description
        else:
            result["Gender"] = ""

        result["Name"] = ""
        for i in range(find_index(assemble,"Name")+1,find_index(assemble,"Nationality")-2):
            result["Name"] = result["Name"] + texts[i].description + " "
        
        result["Arabic Name"]= ""
        for i in range(find_index(assemble,"No")+1,find_index(assemble,"Name")-1):
            result["Arabic Name"] = result["Arabic Name"] + texts[i].description + " "

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
    print(texts[0].description)
    if is_kuwaiti:
        if find_index(assemble,"all"):
            result["PACI No."] = texts[find_index(assemble,"all")-1].description
        else:
            result["PACI No."] = " "
    
    return result

def find_index(dictionary, word):
    for d in dictionary:
        if dictionary[d] == word:
            return d

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