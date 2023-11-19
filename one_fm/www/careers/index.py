import frappe
from frappe.utils import getdate
from .utils import remove_html_tags, get_department_list

def get_context(context):
    context.no_cache = 1
    # Get recent openings
    context.recent_openings = get_recent_openings()

    # Get departments list
    context.department_list = get_department_list()
    context.lang = 'en' if not frappe.cache().get_value("job_opening_lang") else frappe.cache().get_value("job_opening_lang")


def get_recent_openings():
    """ Gets last 10 valid/open job openings ordered by posting date.
        Job description is truncated to get only 250 charctaters to display in card view

    Returns:
        list : recent job openings objects
    """
    recent_openings = []
    recent_openings_raw_format = frappe.db.get_list("Job Opening",
                                {
                                    'publish': 1,
                                    'status': 'Open'
                                },
                                ["name","job_title_in_arabic","designation", "description", "description_in_arabic","one_fm_job_opening_created", "department", "job_title"],
                                order_by="one_fm_job_opening_created desc",
                                )
    for opening in recent_openings_raw_format:
        data = {
            'name': opening.name,
            'name_ar': opening.job_title_in_arabic,
            'job_title': opening.job_title,
            'designation': opening.designation,
            'description': ((remove_html_tags(opening.description)[0:250] + "...") if opening.description else ""),
            'description_ar': ((remove_html_tags(opening.description_in_arabic)[0:250] + "...") if opening.description_in_arabic else ""),
            'department': opening.department,
            'posting_date': str(opening.one_fm_job_opening_created)
        }

        recent_openings.append(data)

    return recent_openings

@frappe.whitelist(allow_guest=True)
def change_language(lang):
    old_lang = frappe.cache().get_value("job_opening_lang")
    frappe.cache().set_value("job_opening_lang", lang)
    if old_lang != lang:
        return True
    else:
        return False