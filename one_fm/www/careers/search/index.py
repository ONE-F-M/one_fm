import frappe
from ..utils import get_department_list, remove_html_tags, get_openings, get_openings_keywords

def get_context(context):

    # Get department list
    context.department_list = get_department_list()

    # Get openings
    openings = []
    result_has_keyword = False
    request_has_keyword = False

    keywords = frappe.form_dict.keywords
    if keywords:
        res = get_openings_keywords(keywords)
        
        if len(res):
            openings, request_has_keyword, result_has_keyword = res, True, True

        else:
            # Get all openings if openings with keywords were not found
            openings, request_has_keyword, result_has_keyword = get_openings(), True, False

    else:
        openings, request_has_keyword, result_has_keyword = get_openings(), False, False

    context.openings = openings
    context.request_has_keyword = request_has_keyword
    context.result_has_keyword = result_has_keyword
    context.keywords = keywords