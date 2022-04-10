import frappe
from .api import get_categories
def get_context(context):
    context.categories = get_categories()
    return context
