import re
import frappe
from frappe.utils import getdate


def get_department_list():
    return frappe.db.get_list("Department", pluck='name', ignore_permissions=True)

def remove_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    filtered = re.sub(clean, ' ', text)
    return re.sub(' +', ' ', filtered)

def get_openings(keywords=None, department=None):
    """This method gets all job openings that are valid/open and have the keywords in the designation of the opening.

    Returns:
        List : list of job opening objects
    """
    openings = []

    filters = {
        'publish': 1,
        'status': 'Open'
    }
    if keywords:
        filters.update({'designation': ['like', f"%{keywords}%"]})

    if department:
        filters.update({'department': department})

    openings_raw_format = frappe.db.get_list("Job Opening", filters,
                                ["name", "designation", "description", "one_fm_job_opening_created", "department"],
                                order_by="one_fm_job_opening_created desc")

    for opening in openings_raw_format:
        data = {
            'name': opening.name,
            'designation': opening.designation,
            'description': ((remove_html_tags(opening.description)[0:250] + "...") if opening.description else ""),
            'department': opening.department,
            'posting_date': str(opening.one_fm_job_opening_created)
        }

        openings.append(data)

    return openings
