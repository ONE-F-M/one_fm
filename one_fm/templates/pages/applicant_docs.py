import os, io
from google.cloud import vision
import frappe
from frappe.utils import cstr
import json
import base64

@frappe.whitelist()
def fetch_text_for_kuwaiti_civilid(images):
    """This API redirects the image fetched from frontend and 
    runs it though Google Vision API, each side at a time.

    Args:
        images (json): Consist of two base64 encoded images(front_side, back_side).

    Returns:
        text_detected: dictionary consisting of text fetched from both front and back side.
    """    
    try:
        #initialize google vision client library
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cstr(frappe.local.site) + frappe.local.conf.google_application_credentials
        client = vision.ImageAnnotatorClient()
        
        # Load the Images
        image_files = json.loads(images)

        front_image = upload_image(image_files["front_side"],"image1.png")
        back_image = upload_image(image_files["back_side"],"image2.png")

        front_text = front_side_kuwaiti_civil_id(front_image, client)
        back_text = back_side_kuwaiti_civil_id(back_image, client)

        text_detected = front_text.update(back_text)
        print(text_detected)

        return text_detected
    
    except Exception as e:
        frappe.throw(e)

@frappe.whitelist(allow_guest=True)
def front_side_kuwaiti_civil_id(image_path, client):

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)  # returns TextAnnotation

    texts = response.text_annotations
    
    emp_det = {}
    assemble = {}
    index = 0

    for index in range(1,len(texts)):
        assemble[index] = texts[index].description
    
    emp_det["Civil ID No."] = texts[find_index(assemble,"CARD")+1].description
    emp_det["Nationality"] = texts[find_index(assemble,"Nationality")+1].description
    emp_det["Date Of Birth"] = texts[find_index(assemble,"Birth")+2].description
    emp_det["Expiry Date"] = texts[find_index(assemble,"Birth")+3].description
    if texts[find_index(assemble,"Sex")-1].description == "M" or texts[find_index(assemble,"Sex")-1].description == "F":
        emp_det["Gender"] = texts[find_index(assemble,"Sex")-1].description
    else:
        emp_det["Gender"] = ""

    emp_det["Name"] = ""
    for i in range(find_index(assemble,"Name")+1,find_index(assemble,"Nationality")-2):
        emp_det["Name"] = emp_det["Name"] + texts[i].description + " "
    
    emp_det["Arabic Name"]= ""
    for i in range(find_index(assemble,"No")+1,find_index(assemble,"Name")-1):
        emp_det["Arabic Name"] = emp_det["Arabic Name"] + texts[i].description + " "

    return emp_det

@frappe.whitelist(allow_guest=True)
def back_side_kuwaiti_civil_id(image_path, client):
    
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    response = client.text_detection(image=image)  # returns TextAnnotation

    texts = response.text_annotations
    
    emp_det = {}
    assemble = {}
    index = 0
    
    for index in range(1,len(texts)):
        assemble[index] = texts[index].description
    if find_index(assemble,"منزل"):
        emp_det["PACI No."] = texts[find_index(assemble,"منزل")+1].description
    else:
        emp_det["PACI No."] = " "
    
    return emp_det

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
        [str]: Path to uploaded image
    """
    content = base64.b64decode(image)
    image_path = cstr(frappe.local.site)+"/private/files/user/"+filename

    with open(image_path, "wb") as fh:
        fh.write(content)
    
    return image_path