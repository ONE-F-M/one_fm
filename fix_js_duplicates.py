import os

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
		// Override dashboard link routing for sibling tracking documents
		setTimeout(() => {
			if (frm.dashboard && frm.dashboard.wrapper) {
				frm.dashboard.wrapper.find('.document-link').off('click').on('click', function(e) {
					e.preventDefault();
					e.stopPropagation();
					let doctype = $(this).attr('data-doctype');
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
				});
			}
		}, 1000);
"""

for dt in doctypes:
    js_path = os.path.join(base_path, dt, f"{dt}.js")
    if not os.path.exists(js_path):
        continue
        
    with open(js_path, 'r') as f:
        content = f.read()
        
    # We will rewrite the file cleanly.
    # We can use git checkout to reset it first.
    os.system(f"git checkout {js_path}")
    
    with open(js_path, 'r') as f:
        clean_content = f.read()
        
    # If it has a refresh block:
    if "refresh: function(frm) {" in clean_content:
        new_content = clean_content.replace("refresh: function(frm) {", "refresh: function(frm) {\n" + dashboard_code)
    elif "refresh(frm) {" in clean_content:
        new_content = clean_content.replace("refresh(frm) {", "refresh(frm) {\n" + dashboard_code)
    elif "frappe.ui.form.on" in clean_content:
        # just add the refresh block
        parts = clean_content.split("frappe.ui.form.on", 1)
        subparts = parts[1].split("{", 1)
        new_content = parts[0] + "frappe.ui.form.on" + subparts[0] + "{\n\trefresh: function(frm) {" + dashboard_code + "\t},\n" + subparts[1]
    
    with open(js_path, 'w') as f:
        f.write(new_content)
        
print("Fixed JS duplicates!")
