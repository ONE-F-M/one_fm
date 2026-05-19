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

js_snippet = """
	refresh: function(frm) {
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
	},
"""

for dt in doctypes:
    js_path = os.path.join(base_path, dt, f"{dt}.js")
    if not os.path.exists(js_path):
        continue
        
    with open(js_path, 'r') as f:
        content = f.read()
        
    if "override dashboard link routing" in content.lower() or "document-link" in content:
        continue
        
    # Find frappe.ui.form.on
    if "frappe.ui.form.on" in content:
        # insert right after frappe.ui.form.on("...", {
        # find the first '{' after frappe.ui.form.on
        parts = content.split("frappe.ui.form.on", 1)
        subparts = parts[1].split("{", 1)
        
        new_content = parts[0] + "frappe.ui.form.on" + subparts[0] + "{\n" + js_snippet + subparts[1]
        
        with open(js_path, 'w') as f:
            f.write(new_content)
            
print("Patched js files!")
