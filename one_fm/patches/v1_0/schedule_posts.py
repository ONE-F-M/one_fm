from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, getdate, add_to_date
import pandas as pd


def execute():
	#set all posts under site Airport Terminal T4 to planned
	frappe.enqueue(set_posts_planned_for_t4, is_async=True, queue='long')

def set_posts_planned_for_t4():
	start_date = cstr(getdate())
	end_date = add_to_date(start_date, months=18)
	for post in frappe.db.get_list("Operations Post", {'project': 'Airport', 'site': 'Airport Terminal 4'}, "name"):
		for date in pd.date_range(start=start_date, end=end_date):
			if frappe.db.exists("Post Schedule", {"date": cstr(date.date()), "post": post.name}):
				doc = frappe.get_doc("Post Schedule", {"date": cstr(date.date()), "post": post.name})
			else: 
				doc = frappe.new_doc("Post Schedule")
				doc.post = post.name
				doc.date = cstr(date.date())
			doc.post_status = "Planned"
			doc.save()	
	frappe.db.commit()
