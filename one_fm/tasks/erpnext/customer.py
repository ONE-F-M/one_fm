from PIL import Image
from urllib.request import urlretrieve
import frappe




def on_update(doc, event=None):
    """
        Validate customer entry.
    """

    # validate image
    if doc.image:
        path = frappe.utils.get_site_path()
        if (doc.image.startswith('http://') or doc.image.startswith('https://')):
            image_name = doc.image.split('/')[-1]
            image_link = f"{path}/public/website_image_{image_name}"
            try:
                image = Image.open("website_image_"+image_link)
            except Exception as e:
                urlretrieve(doc.image, image_name)
                image = Image.open(image_name)
                image = image.resize((73, 72))
                image.save(f"{path}/public/files/website_image_{image_name}")
                doc.db_set("website_image", f"/files/website_image_{image_name}")
        else:
            image_link = f"{path}/public{doc.image}"
            try:
                image = Image.open("website_image_"+image_link)
            except Exception as e:
                image = Image.open(image_link)
                image = image.resize((73, 72))
                image.save(f"{path}/public/{doc.image.replace('/files/', '/files/website_image_')}")
                doc.db_set("website_image", doc.image.replace('/files/', '/files/website_image_'))
