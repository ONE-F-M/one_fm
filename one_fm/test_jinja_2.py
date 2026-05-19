import frappe

def run():
    doc = frappe.get_doc("Arrival and Deployment", "ARD-2026-00005")
    template = "Dear {{ doc.warehouse }}, Kindly arrange their Uniforms and welcome kit accordingly."
    try:
        res = frappe.render_template(template, doc.as_dict())
        print("Rendered:", res)
    except Exception as e:
        print("Error:", e)
