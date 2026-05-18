"""Workspace sidebar override to sort workspaces and children alphabetically."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.desktop import Workspace


@frappe.whitelist()
def get_workspace_sidebar_items():
    has_access = "Workspace Manager" in frappe.get_roles()

    blocked_modules = frappe.get_cached_doc("User", frappe.session.user).get_blocked_modules()
    blocked_modules.append("Dummy Module")
    allowed_domains = [None, *frappe.get_active_domains()]

    filters = {
        "restrict_to_domain": ["in", allowed_domains],
        "module": ["not in", blocked_modules],
    }

    if has_access:
        filters = []

    fields = [
        "name",
        "title",
        "for_user",
        "parent_page",
        "content",
        "public",
        "module",
        "icon",
        "indicator_color",
        "is_hidden",
    ]
    all_pages = frappe.get_all(
        "Workspace", fields=fields, filters=filters, order_by="title asc", ignore_permissions=True
    )

    pages = []
    private_pages = []

    for page in all_pages:
        try:
            workspace = Workspace(page, True)
            if has_access or workspace.is_permitted():
                page["label"] = _(page.get("title") or page.get("name"))
                if page.public and (has_access or not page.is_hidden) and page.title != "Welcome Workspace":
                    pages.append(page)
                elif page.for_user == frappe.session.user:
                    private_pages.append(page)
        except frappe.PermissionError:
            pass

    pages = _sort_workspace_tree(pages)
    private_pages = _sort_workspace_tree(private_pages)

    if private_pages:
        pages.extend(private_pages)

    if len(pages) == 0:
        pages = [frappe.get_doc("Workspace", "Welcome Workspace").as_dict()]
        pages[0]["label"] = _("Welcome Workspace")

    return {
        "pages": pages,
        "has_access": has_access,
        "has_create_access": frappe.has_permission(doctype="Workspace", ptype="create"),
    }


def _sort_workspace_tree(pages):
    by_parent = {}
    roots = []
    for page in pages:
        parent = page.get("parent_page")
        by_parent.setdefault(parent, []).append(page)
        if not parent:
            roots.append(page)

    for siblings in by_parent.values():
        siblings.sort(key=lambda d: (d.get("title") or d.get("name") or "").lower())

    ordered = []

    def visit(node):
        ordered.append(node)
        for child in by_parent.get(node.get("name"), []):
            visit(child)

    for root in sorted(roots, key=lambda d: (d.get("title") or d.get("name") or "").lower()):
        visit(root)

    return ordered
