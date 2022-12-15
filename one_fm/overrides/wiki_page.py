import frappe
from one_fm.data import md_to_html


def update_context_(me):
    me.context.doc = me.doc
    me.context.update(me.context.doc.as_dict())
    me.context.update(me.context.doc.get_page_info())
    me.template_path = me.context.template or me.template_path
    if not me.template_path:
        if me.doctype == 'Wiki Page':
            me.template_path = 'one_fm/templates/wiki_page/templates/wiki_page.html'
        else:
            me.template_path = me.context.doc.meta.get_web_template()
    if not me.template_path:
            me.template_path = me.context.doc.meta.get_web_template()
    if hasattr(me.doc, "get_context"):
        ret = me.doc.get_context(me.context)
        if ret:
            me.context.update(ret)
    for prop in ("no_cache", "sitemap"):
        if prop not in me.context:
            me.context[prop] = getattr(me.doc, prop, False)







@frappe.whitelist()
def get_context(doc, context):
    doc.verify_permission("read")
    doc.set_breadcrumbs(context)
    wiki_settings = frappe.get_single("Wiki Settings")
    context.navbar_search = wiki_settings.add_search_bar
    context.banner_image = wiki_settings.logo
    context.script = wiki_settings.javascript
    context.docs_search_scope = doc.get_docs_search_scope()
    context.metatags = {
        "title": doc.title, 
        "description": doc.meta_description,
        "keywords": doc.meta_keywords,
        "image": doc.meta_image,
        "og:image:width": "1200",
        "og:image:height": "630",
        }
    context.last_revision = doc.get_last_revision()
    context.number_of_revisions = frappe.db.count(
        "Wiki Page Revision Item", {"wiki_page": doc.name}
    )
    html = md_to_html(doc.content)
    context.content = html
    context.page_toc_html = html.toc_html
    context.show_sidebar = True
    context.hide_login = True
    context.lang = frappe.local.lang

    context = context.update(
        {
            "post_login": [
                {"label": ("My Account"), "url": "/me"},
                {"label": ("Logout"), "url": "/?cmd=web_logout"},
                {
                    "label": ("Contributions ") + get_open_contributions(),
                    "url": "/contributions",
                },
                {
                    "label": ("My Drafts ") + get_open_drafts(),
                    "url": "/drafts",
                },
            ]
        }
    )
    return context

def get_open_contributions():
	count = len(
		frappe.get_list("Wiki Page Patch", filters=[["status", "=", "Under Review"]],)
	)
	return f'<span class="count">{count}</span>'

def get_open_drafts():
	count = len(
		frappe.get_list("Wiki Page Patch", filters=[["status", "=", "Draft"], ["owner", '=', frappe.session.user]],)
	)
	return f'<span class="count">{count}</span>'

@frappe.whitelist()
def preview(content, name, new, type, diff_css=False):
	html = md_to_html(content)
	if new:
		return {"html": html}
	from ghdiff import diff

	old_content = frappe.db.get_value("Wiki Page", name, "content")
	diff = diff(old_content, content, css=diff_css)
	return {
		"html": html,
		"diff": diff,
		"orignal_preview": md_to_html(old_content),
	}
