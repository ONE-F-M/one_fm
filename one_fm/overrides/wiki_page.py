import frappe
from one_fm.data import md_to_html

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
def preview(name, new, type, diff_css=False, content=None):
	
	if not content:
		frappe.throw("Content is required for preview generation")
		
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
