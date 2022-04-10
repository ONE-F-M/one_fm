import frappe
from ..api import get_categories, remove_html_tags
def get_context(context):
    print(frappe.form_dict)
    context.categories = get_categories()
    context.search_data = search_article(text=frappe.form_dict.q, page=frappe.form_dict.page)
    print(context)
    return context


def search_article(text=None, page=None):
    if not text:
        return {}
    # check if search request
    pagination = paginate(text, page) #pass to pagination

    # query = frappe.db.sql(f"""
    #     SELECT name, title, content, creation FROM `tabHelp Article`
    #     WHERE title LIKE "%{text}%" OR content LIKE "{text}"
    # """, as_dict=1)
    # query = frappe.db.get_list('Help Article',
    #     filters=[
    #         ['title', 'LIKE', f"%{text}%"],
    #         ['content', 'LIKE', f"%tes%"]
    #     ],
    #     fields=['name', 'title', 'content'],
    #     # start=10,
    #     # page_length=20,
    #     as_list=False
    # )
    return pagination



def paginate(text, page=0, paginate_by=5):
    prev, next, search = 0, 0, False
    query = f"""
        SELECT name, title, content, creation, category, subcategory, route
        FROM `tabHelp Article`
        WHERE published=1 AND title LIKE "%{text}%" OR content LIKE "%{text}%"
        GROUP BY title
    """

    if(page):
        page = int(page)
        results = frappe.db.sql(query+f"""LIMIT {(page*paginate_by)-paginate_by}, {paginate_by};""", as_dict=True)
        next_set = frappe.db.sql(query+f"""LIMIT {page*paginate_by}, {paginate_by};""", as_dict=True)
        if(next_set):
            prev, next = page-1, page+1
        else:
            prev, next = page-1, 0
    else:
        count = frappe.db.sql(f"""
            SELECT COUNT(name) as count, title, content, creation FROM `tabHelp Article`
            WHERE published=1 AND title LIKE "%{text}%" OR content LIKE "%{text}%"
            """,
            as_dict=True)[0].count
        if(count>paginate_by):
            prev, next = 0, 2
        results = frappe.db.sql(f"""{query} LIMIT {paginate_by};""", as_dict=True)


    if(text):
        search=True
    # strip html
    for i in results:
        i.creation = i.creation.date()
        i.content = remove_html_tags(i.content)[:200]+'...'
        if text in i.content:
            i.content = i.content.replace(text, f'<i class="text-warning">{text}</i>')
        if text in i.title:
            i.title = i.title.replace(text, f'<i class="text-warning">{text}</i>')

    return frappe._dict({
        'results': results,
        'prev': prev,
        'next': next,
        'search':search,
        'q':text
    })
