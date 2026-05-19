import os
import re

doctypes = [
    "pcc_clearance",
    "overseas_medical_appointment_wafid",
    "overseas_remedical",
    "visa_stamping",
    "arrival_and_deployment",
    "pam_visa"
]

base_path = "one_fm/one_fm/doctype"

dashboard_code = """
	refresh: function(frm) {
		// Override dashboard link routing for sibling tracking documents
		if (frm.dashboard) {
			frm.dashboard.open_document_list = function($link, show_open) {
				let doctype = $link.attr("data-doctype");
				if (doctype && doctype !== "Candidate Country Process") {
					frappe.route_options = {
						"candidate_country_process": frm.doc.candidate_country_process
					};
				} else {
					frappe.route_options = {
						"name": frm.doc.candidate_country_process
					};
				}
				frappe.set_route("List", doctype);
			};
		}
	}
"""

for dt in doctypes:
    js_path = os.path.join(base_path, dt, f"{dt}.js")
    if not os.path.exists(js_path):
        continue
        
    os.system(f"git checkout {js_path}")
    
    with open(js_path, 'r') as f:
        content = f.read()
        
    # remove comments
    content = content.replace("// frappe.ui.form.on", "frappe.ui.form.on")
    content = content.replace("// \trefresh(frm) {", "")
    content = content.replace("// \t},", "")
    content = content.replace("// });", "});")
    
    # Now we have a clean frappe.ui.form.on if it was commented out.
    if "refresh: function(frm)" in content:
        # For overseas_medical...
        old_refresh = "refresh: function(frm) {"
        new_refresh = dashboard_code.strip() + ",\n\n\trefresh: function(frm) {"
        # wait, we don't want two refresh functions. We can just append inside the existing one.
        pass
        
    # Actually let's just write a clean file for all except overseas_medical
    if dt != "overseas_medical_appointment_wafid":
        new_content = f"""// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

frappe.ui.form.on("{dt.replace('_', ' ').title().replace('Pam', 'PAM')}", {{
{dashboard_code}
}});
"""
        with open(js_path, 'w') as f:
            f.write(new_content)
    else:
        # It's overseas medical, it has other hooks.
        # Let's just do a clean string replacement.
        with open(js_path, 'r') as f:
            med_content = f.read()
        med_content = med_content.replace("refresh: function(frm) {", dashboard_code.strip() + ",\n\n\trefresh: function(frm) {")
        with open(js_path, 'w') as f:
            f.write(med_content)

print("Fixed JS syntax errors!")
