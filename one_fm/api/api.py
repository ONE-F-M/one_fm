import frappe, base64
from frappe import _
import pandas as pd
from frappe.utils import cstr
from frappe.model.rename_doc import rename_doc
import requests
import firebase_admin
from firebase_admin import messaging, credentials
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
        for date in pd.date_range(start="2021-03-01", end="2021-03-31"):
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

@frappe.whitelist()
def store_fcm_token(employee_id ,fcm_token,device_os):
    """
    This function stores FCM Token  and Device OS in employee doctype 
    that is fetched from device/app end when user logs in.
    
    Params: Employee ID (Single employee ID), FCM Token and Device OS comes from the client side.
    
    It returns true or false based on the execution.
    
    eg:bench execute --kwargs "{'employee_id':'HR-EMP-00002','fcm_token':'f0_1sEWK7kksiegwCZ7dUm:APA91bHCFXcmXdI7AnI_37dbfjTz5uKf46_kvwIXgmtSoxGCbApo4zFETfbaWaEj8FpKXzJlwUS6CTTCfSX8WStuiFx1oPR4gtH3I46-jNbQkbhfvXI_lR3mKDl6e2ek2nB_5OFTfH9c', 'device_os':'ios'}" one_fm.api.api.store_fcm_token 
    """
    Employee = frappe.get_doc("Employee",{"name":employee_id})
    try:
        if Employee:
            Employee.fcm_token = fcm_token
            Employee.device_os = device_os
            Employee.save()
            frappe.db.commit()
            return True
        else:
            return False
    except Exception as e:
        print(frappe.get_traceback())


@frappe.whitelist()
def push_notification(employee_id, title, body, checkin, arriveLate ,checkout):
    """
    This Function send push notification to group of devices. here, we use 'firebase admin' library to send the message.
    
    Params: employee_id is a list of employee ID's,
    title and body are message string to send it through notification.
    checkin, arriveLate ,checkout are data to enable buttons.
    
    It returns the response received.
    """ 
    # Collect the registration token from employee doctype for the given list of employees
    registration_token = frappe.get_value("Employee", {"name": employee_id}, "fcm_token")
    
    # Create message payload. 
    if registration_token :
        message = messaging.Message(
                data= {
                "title": title,
                "body" : body,
                "showButtonCheckIn": checkin,
                "showButtonCheckOut": checkout,
                "showButtonArrivingLate": arriveLate
                },
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

@frappe.whitelist()
def push_notification_rest_api(employee_id, title, body, checkin, arriveLate ,checkout ):
    """ 
    This function is used to send notification through Firebase CLoud Message. 
    It is a rest API that sends request to "https://fcm.googleapis.com/fcm/send"
    
    Params: employee_id e.g. HR_EMP_00001, , title:"Title of your message", body:"Body of your message"
    test Execution: bench execute --kwargs "{'employee_id':'HR-EMP-00001','title':'Hello','body':'Testing','checkin':'True','arriveLate':'True','checkout':'False'}" one_fm.api.api.push_notification_rest_api

    serverToken is fetched from firebase -> project settings -> Cloud Messaging -> Project credentials
    Device Token and Device OS is store in employee doctype using 'store_fcm_token' on device end.
    """
    serverToken = frappe.get_value("Firebase Cloud Message",filters=None, fieldname=['server_token'])
    token = frappe.get_list("Employee", {"name": employee_id}, "fcm_token, device_os")
    deviceToken = token[0].fcm_token
    device_os = token[0].device_os

    headers = {
            'Content-Type': 'application/json',
            'Authorization': 'key=' + serverToken,
        }

    #Body in json form defining a message payload to send through API. 
    # The parameter defers based on OS. Hence Body is designed based on the OS of the device.
    if device_os == "android":
         body = {       
            "to":deviceToken,
            "data": {
                "title": title,
                "body" : body,
                "showButtonCheckIn": checkin,
                "showButtonCheckOut": checkout,
                "showButtonArrivingLate": arriveLate
                }
            }
    else:
        body = {       
            "to":deviceToken,
            "data": {
                "title": title,
                "body" : body,
                "showButtonCheckIn": checkin,
                "showButtonCheckOut": checkout,
                "showButtonArrivingLate": arriveLate
                },
            "notification": {
                "body": body,
                "title": title,
                "badge": 0,
                "click_action": "oneFmNotificationCategory1"
                },
                "mutable_content": True
            }

    #request is sent through "https://fcm.googleapis.com/fcm/send" along with params above.
    response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body))
    return response