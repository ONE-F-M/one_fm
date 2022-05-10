import frappe, re


def get_categories():
    """
        Get all categories and sub categories
    """
    if frappe.session.user=='Guest':
        raise  frappe.exceptions.PermissionError('Please login to continue')
    query = frappe.db.sql("""
        SELECT name, category_name, is_subcategory, category, route, category_description
        FROM `tabHelp Category`
        WHERE published=1
    """, as_dict=1)

    # sort and group
    categories = {}
    subcats_remove = []
    for i in query:
        if(i.category_description):
            i.category_description = remove_html_tags(i.category_description)[:50]+'...'
        else:
            i.category_description = ''
        if(not i.is_subcategory):
            if(not categories.get(i.name)):
                categories[i.name] = {'info': i, 'subcat':[]}
        else:
            subcats_remove.append(i)

    for i in subcats_remove:
        categories[i.category]['subcat'].append(i)

    return categories

def remove_html_tags(text):
    """Remove html tags from a string"""
    clean = re.compile('<.*?>')
    filtered = re.sub(clean, ' ', text)
    return re.sub(' +', ' ', filtered)
