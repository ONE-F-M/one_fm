import frappe
from frappe.utils import getdate
from .utils import remove_html_tags, get_department_list

def get_context(context):
    no_cache = 1
    # Get recent openings
    context.recent_openings = get_recent_openings()

    # Get departments list
    context.department_list = get_department_list()


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
                                ["name", "designation", "description", "one_fm_job_opening_created", "department"],
                                order_by="one_fm_job_opening_created desc",
                                )

    for opening in recent_openings_raw_format:
        data = {
            'name': opening.name,
            'designation': opening.designation,
            'description': ((remove_html_tags(opening.description)[0:250] + "...") if opening.description else ""),
            'department': opening.department,
            'posting_date': str(opening.one_fm_job_opening_created)
        }

        recent_openings.append(data)

    return recent_openings
