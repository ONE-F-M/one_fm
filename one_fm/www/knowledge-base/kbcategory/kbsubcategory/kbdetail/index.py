import frappe, random
from ....api import get_categories, remove_html_tags
def get_context(context):
    context.categories = get_categories()
    doc = frappe.get_doc("Help Article", frappe.form_dict.article)
    context.doc = doc
    try:
        related_article = frappe.db.sql(f"""
        SELECT name, title, route, category, subcategory, content
        FROM `tabHelp Article`
        WHERE subcategory="{doc.subcategory}" AND name!="{doc.name}"
        """, as_dict=1)
        if len(related_article)>3:
            related_article = random.sample(related_article, 3)
        for i in related_article:
            i.content = remove_html_tags(i.content)[:100]+'...'
            context.related_article = related_article
    except Exception as e:
        context.related_article = []
    print(context.related_article)
    return context
