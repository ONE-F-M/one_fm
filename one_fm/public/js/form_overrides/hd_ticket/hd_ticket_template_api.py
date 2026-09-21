from typing import Literal

import frappe
from frappe.utils import cint

# from frappe import _
from pypika import JoinType

from helpdesk.helpdesk.doctype.hd_form_script.hd_form_script import get_form_script
from helpdesk.utils import check_permissions

DOCTYPE_TEMPLATE = "HD Ticket Template"
DOCTYPE_TEMPLATE_FIELD = "HD Ticket Template Field"
DOCTYPE_TICKET = "HD Ticket"


@frappe.whitelist()
def get_one(name: str):
    check_permissions(DOCTYPE_TEMPLATE, None)
    found, about, description_template = frappe.get_value(
        DOCTYPE_TEMPLATE, name, ["name", "about", "description_template"]
    ) or [None, None, None]
    if not found:
        return {"about": None, "fields": []}

    fields = get_fields_meta(name)

    return {
        "about": about,
        "fields": fields,
        "description_template": description_template,
        "_form_script": get_form_script(
            "HD Ticket", apply_on_new_page=True, is_customer_portal=False
        ),
    }


def get_fields_meta(template: str):
    fields = get_fields(template, "DocField")
    fields.extend(get_fields(template, "Custom Field"))
    fields = sorted(fields, key=lambda x: x.idx)
    return fields


def get_fields(template: str, fetch: Literal["Custom Field", "DocField"]):
    QBField = frappe.qb.DocType(DOCTYPE_TEMPLATE_FIELD)
    QBFetch = frappe.qb.DocType(fetch)
    fields = (
        frappe.qb.from_(QBField)
        .select(QBField.star)
        .where(QBField.parent == template)
        .where(QBField.parentfield == "fields")
        .where(QBField.parenttype == DOCTYPE_TEMPLATE)
    )
    where_parent = QBFetch.parent == DOCTYPE_TICKET
    if fetch == "Custom Field":
        where_parent = QBFetch.dt == DOCTYPE_TICKET
    result = (
        frappe.qb.from_(fields)
        .select(
            QBFetch.description,
            QBFetch.fieldtype,
            QBFetch.label,
            QBFetch.options,
            QBFetch.link_filters,
            QBFetch.depends_on,
            QBFetch.mandatory_depends_on,
            QBFetch.fetch_from,
            QBFetch.fetch_if_empty,
            QBFetch.read_only,
            fields.fieldname,
            fields.hide_from_customer,
            fields.required,
            fields.url_method,
            fields.placeholder,
            fields.idx,
        )
        .join(QBFetch, JoinType.inner)
        .on(QBFetch.fieldname == fields.fieldname)
        .where(where_parent)
        .orderby(fields.idx)
        .run(as_dict=True)
    )
    apply_property_setters(result)

    return result


# Properties that may be overridden per-field via Customize Form. Kept in sync
# with the columns selected above so a Property Setter wins over the DocField /
# Custom Field value.
OVERRIDABLE_PROPERTIES = (
    "link_filters",
    "depends_on",
    "mandatory_depends_on",
    "fetch_from",
    "fetch_if_empty",
    "read_only",
)

INT_PROPERTIES = ("fetch_if_empty", "read_only")


def apply_property_setters(fields: list):
    """Overlay Property Setter values on the fetched field metadata.

    Done in a single query rather than one exists() + get_value() per
    (field, property) pair.
    """
    if not fields:
        return

    property_setters = frappe.get_all(
        "Property Setter",
        filters={
            "doc_type": DOCTYPE_TICKET,
            "field_name": ["in", [f.fieldname for f in fields]],
            "property": ["in", OVERRIDABLE_PROPERTIES],
        },
        fields=["field_name", "property", "value"],
    )
    if not property_setters:
        return

    overrides = {}
    for ps in property_setters:
        overrides.setdefault(ps.field_name, {})[ps.property] = ps.value

    for field in fields:
        for prop, value in overrides.get(field.fieldname, {}).items():
            field[prop] = cint(value) if prop in INT_PROPERTIES else value
