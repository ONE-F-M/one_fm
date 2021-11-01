import frappe, base64
from frappe import _
import pandas as pd
from frappe.utils import cstr
from frappe.model.rename_doc import rename_doc
import requests
import firebase_admin
from firebase_admin import messaging
from firebase_admin import credentials
import requests
import json

import json
from frappe.desk.page.user_profile.user_profile import get_energy_points_heatmap_data, get_user_rank
from frappe.social.doctype.energy_point_log.energy_point_log import get_energy_points, get_user_energy_and_review_points


cred = credentials.Certificate(frappe.utils.cstr(frappe.local.site)+"/private/files/one-fm-70641-firebase-adminsdk-nuf6h-667458c1a5.json")
firebase_admin.initialize_app(cred)

@frappe.whitelist()
def _one_fm():
    print(frappe.local.lang)


def set_posts_active():
    posts = frappe.get_all("Operations Post", {"site": "Head Office"})
    print(posts)
    for post in posts:
        for date in	pd.date_range(start="2021-03-01", end="2021-03-31"):
            sch = frappe.new_doc("Post Schedule")
            sch.post = post.name
            sch.date = cstr(date.date())
            sch.post_status = "Planned"
            sch.save()
    
@frappe.whitelist()
def change_user_profile(image):
    content = base64.b64decode(image)
    filename = frappe.session.user+".png"
    OUTPUT_IMAGE_PATH = frappe.utils.cstr(frappe.local.site)+"/public/files/ProfileImage/"+filename
    fh = open(OUTPUT_IMAGE_PATH, "wb")
    fh.write(content)
    fh.close()
    image_file="/files/ProfileImage/"+filename
    try:
        user = frappe.get_doc("User", frappe.session.user)
        user.user_image = image_file
        user.save()
        frappe.db.commit()
        return {"message": "Success","data_obj": {user},"status_code" : 200}
    except Exception as e:
        print(frappe.get_traceback())
        return {"message": "Some Problem Occured","data_obj": {},"status_code" : 500}

@frappe.whitelist()
def get_user_details():
    try:
        user_id = frappe.session.user
        user= frappe.get_value("User",user_id,"*")
        employee_ID = frappe.get_value("Employee", {"user_id": user_id}, ["name","designation"])
        
        Rank = get_user_rank(user_id)
        energy_Review_Point = get_user_energy_and_review_points(user_id)

        user_details={}
        user_details["Name"]=user.full_name
        user_details["Email"]=user.email
        user_details["Mobile_no"]= user.mobile_no
        user_details["Designation"]= employee_ID[1]
        user_details["EMP_ID"]= employee_ID[0]
        user_details["User_Image"] = user.user_image
        user_details["Monthly_Rank"] = str(Rank["monthly_rank"]).strip('[]') if len(Rank["monthly_rank"])!=0 else "0"
        user_details["Rank"] = str(Rank["all_time_rank"]).strip('[]') if len(Rank["all_time_rank"])!=0 else "0"
        user_details["Energy_Point"] = str(int(energy_Review_Point[user_id]["energy_points"])) if len(energy_Review_Point)!=0 else "0"
        user_details["Review_Point"] = str(int(energy_Review_Point[user_id]["review_points"])) if len(energy_Review_Point)!=0 else "0"
        return user_details
    except Exception as e:
        print(frappe.get_traceback())

@frappe.whitelist()
def get_user_roles():
    user_id = frappe.session.user
    user_roles = frappe.get_roles(user_id)
    return user_roles

def rename_posts():
    sites = frappe.get_all("Operations Site")
    for site in sites:
        print(site)
        posts = frappe.get_all("Operations Post", {"site": site.name}, ["name", "post_name", "gender", "site_shift"])
        print(posts)
        frappe.enqueue(rename_post, posts=posts, is_async=True, queue="long")


def rename_post(posts):
    for post in posts:
        new_name = "{post_name}-{gender}|{site_shift}".format(post_name=post.post_name, gender=post.gender, site_shift=post.site_shift)
        print(new_name)
        try:
            rename_doc("Operations Post", post.name, new_name, force=True)
        except Exception as e:
            print(frappe.get_traceback())

# This function allows you to fetch the details of a given Shift Permission.
# params: Sift Permission name (eg: SP-000001)
# returns: Details of shift Permission as a doc.
@frappe.whitelist()
def shift_permission_details(shift_permission_id):
    try:
        shift_permission = frappe.get_doc("Shift Permission", {'name':shift_permission_id},["*"])
        return shift_permission
    except Exception as e:
        print(frappe.get_traceback())
        return frappe.utils.response.report_error(e.http_status_code)
        
@frappe.whitelist()
def store_fcm_token(employee_id ,fcm_token):
    Employee = frappe.get_doc("Employee",{"name":employee_id})
    try:
        if Employee:
            Employee.fcm_token= fcm_token
            Employee.save()
            frappe.db.commit()
            return True
        else:
            return False
    except Exception as e:
        print(frappe.get_traceback())

@frappe.whitelist()
def push_notification(employee_id, title, body):
    registration_tokens = []
    for emp in employee_id:
        token = frappe.get_all("Employee", {"name": emp}, "fcm_token")
        if token[0].fcm_token:
            registration_tokens.append(token[0].fcm_token)
    # This Device token comes from the client FCM SDKs.

    # See documentation on defining a message payload.
    for registration_token in registration_tokens:
        print(registration_token)
        message = messaging.Message(
                data= {
                "title": title,
                "body": body,
                "showButtonCheckIn": 'True',
                "showButtonCheckOut": 'True',
                "showButtonArrivingLate": 'True'
                },
                android=messaging.AndroidConfig(
                    notification=messaging.AndroidNotification(
                        title=title,
                        body=body,
                        click_action = "oneFmNotificationCategory1",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=0,
                            mutable_content= 1,
                            category = "oneFmNotificationCategory1"
                        ),
                    ),
                ),
                token=registration_token,
            )
        response = messaging.send(message)
    return response
    # See the BatchResponse reference documentation
    # for the contents of response.

# This function is used to send notification through Firebase CLoud Message. 
# It is a rest API that sends request to "https://fcm.googleapis.com/fcm/send"
# Params: employee_id e.g. HR_EMP_00001
@frappe.whitelist()
def push_notification_rest_api(employee_id):
    """
    serverToken is fetched from firebase -> project settings -> Cloud Messaging -> Project credentials
    Device Token is store in employee doctype using 'store_fcm_token' on device end.
    """
    serverToken = frappe.get_value("Firebase Cloud Message",filters=None, fieldname=['server_token'])
    token = frappe.get_all("Employee", {"name": employee_id}, "fcm_token")
    deviceToken = token[0].fcm_token

    headers = {
            'Content-Type': 'application/json',
            'Authorization': 'key=' + serverToken,
        }

    #Body in json form defining a message payload to send through API.
    body = {
             "to":deviceToken,
                "data": {
                "title": "Check in reminder new",
                "body" : "Please click on below button to mark your attendance new",
                "showButtonCheckIn": True,
                "showButtonCheckOut": True,
                "showButtonArrivingLate": True
                },
                "notification": {
                    "body": "body",
                    "title": "title",
                    "badge": 0,
                    "click_action": "oneFmNotificationCategory1"
                },
                "mutable_content": True
            }
    #request is sent through "https://fcm.googleapis.com/fcm/send" along with params above.
     response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body))
    print(response.status_code)

    print(response.json())