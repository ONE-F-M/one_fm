import os, io
from google.cloud import vision
import pandas as pd
import frappe
import json
import base64


@frappe.whitelist(allow_guest=True)
def fetch_text(image):
    print("Here")
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = frappe.utils.cstr(frappe.local.site)+'/private/files/inbound-theory-254808-c1818ddd7f9e.json'

    client = vision.ImageAnnotatorClient()
    
    print(image)
    image_files = json.loads(image)
    print(image_files)
    image_path_1 = upload_image(image_files["Image1"],"image1.png")
    image_path_2 = upload_image(image_files["Image2"],"image2.png")

    print(image_path_1)

    """
    # or we can pass the image url
    image = vision.types.Image()
    image.source.image_uri = 'https://edu.pngfacts.com/uploads/1/1/3/2/11320972/grade-10-english_orig.png'
    """

    front_text = front_side_kuwaiti_civil_id(image_path_1, client)
    print(front_text)
    back_text = back_side_kuwaiti_civil_id(image_path_2, client)
    print(back_text)
    if front_text:
        return front_text
    else:
        return "Error"

@frappe.whitelist()
def upload_image(image, filename):
    content = base64.b64decode(image)
    OUTPUT_IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/private/files/user/"+filename

    with open(OUTPUT_IMAGE_PATH, "wb") as fh:
        fh.write(content)
    return OUTPUT_IMAGE_PATH

@frappe.whitelist(allow_guest=True)
def front_side_kuwaiti_civil_id(image_path, client):

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    # construct an iamge instanceimage = vision.Image(content=content) 
    image = vision.Image(content=content)

    # annotate Image Response
    response = client.text_detection(image=image)  # returns TextAnnotation
    df = pd.DataFrame(columns=['locale', 'description'])

    texts = response.text_annotations
    
    emp_det = {}
    assemble = {}
    index = 0
    keyword_index = {}
    #print(emp_det)
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
    #print(emp_det)
    return emp_det

@frappe.whitelist(allow_guest=True)
def back_side_kuwaiti_civil_id(image_path, client):
    
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    # construct an iamge instanceimage = vision.Image(content=content) 
    image = vision.Image(content=content)

    # annotate Image Response
    response = client.text_detection(image=image)  # returns TextAnnotation
    df = pd.DataFrame(columns=['locale', 'description'])

    texts = response.text_annotations
    
    emp_det = {}
    assemble = {}
    index = 0
    keyword_index = {}
    #print(emp_det)
    
    for index in range(1,len(texts)):
        assemble[index] = texts[index].description
    if find_index(assemble,"منزل"):
        emp_det["PACI No."] = texts[find_index(assemble,"منزل")+1].description
    else:
        emp_det["PACI No."] = ""
    
    return emp_det
    
    """
    for text in texts:
        print('\n"{}"'.format(text.description))

        vertices = (['({},{})'.format(vertex.x, vertex.y)
                    for vertex in text.bounding_poly.vertices])

        print('bounds: {}'.format(','.join(vertices)))

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))
    """

def find_index(dictionary, word):
    for d in dictionary:
        if dictionary[d] == word:
            return d