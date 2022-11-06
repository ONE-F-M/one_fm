import frappe

def execute():
    # fix employee customizations
    sla_list = frappe.db.get_list("Service Level Agreement",
          {
              "enabled": 1,
              "document_type": "Issue",
          })
    if sla_list:
        frappe.db.sql(f"""
        UPDATE tabIssue SET service_level_agreement = "{sla_list[0].name}"
        """)

    # delete operations post in custom field
    frappe.db.sql("""DELETE FROM `tabCustom Field` WHERE dt="Operations Post" """)

    # delete operations post in custom docper
    frappe.db.sql("""DELETE FROM `tabCustom DocPerm` WHERE parent="Operations Post" """)
    frappe.db.commit()