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

old_dashboard_code = """		// Override dashboard link routing for sibling tracking documents
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
		}, 1000);"""

new_dashboard_code = """		// Override dashboard link routing for sibling tracking documents
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
		}"""

for dt in doctypes:
    js_path = os.path.join(base_path, dt, f"{dt}.js")
    if not os.path.exists(js_path):
        continue
        
    with open(js_path, 'r') as f:
        content = f.read()
        
    if old_dashboard_code in content:
        new_content = content.replace(old_dashboard_code, new_dashboard_code)
        with open(js_path, 'w') as f:
            f.write(new_content)
        print(f"Patched {dt}.js")
            
print("Fixed JS duplicates 2!")
