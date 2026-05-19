import frappe

def run():
    doc = frappe.get_doc("Arrival and Deployment", "ARD-2026-00005")
    doc.warehouse = None
    template = "Dear {{ doc.warehouse }}, Kindly arrange their Uniforms and welcome kit accordingly."
    try:
        res = frappe.render_template(template, {"doc": doc})
        print("Rendered:", res)
    except Exception as e:
        print("Error:", e)
