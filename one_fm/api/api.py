import frappe
from frappe import _
import pandas as pd
from frappe.utils import cstr
from frappe.model.rename_doc import rename_doc



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
