import frappe
from frappe import _
import pandas as pd
from frappe.utils import cstr
from frappe.model.rename_doc import rename_doc
import requests
import json


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
    
def change_user_profile(image):
    try:
        user = frappe.get_doc("User", "s.shaikh@armor-services.com")
        user.user_image = image
        user.save()
        frappe.db.commit()
        return user
    except Exception as e:
        print(frappe.get_traceback())


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
def final_reminder_notification(serverToken,deviceToken):
    # This Device token comes from the client FCM SDKs.

    # See documentation on defining a message payload.
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'key=' + serverToken,
    }

    body = {
            'notification': {'title': 'Sending push form python script',
                            'body': 'New Message'
                            },
            'to':deviceToken,
            'priority': 'high',
            #   'data': dataPayLoad,
        }

    # Send a message to the device corresponding to the provided
    # registration token.
    response = requests.post("https://fcm.googleapis.com/fcm/send",headers = headers, data=json.dumps(body))
    print(response.status_code)
    print(response.json())