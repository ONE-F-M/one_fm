import os

js_path = "one_fm/one_fm/doctype/overseas_medical_appointment_wafid/overseas_medical_appointment_wafid.js"

with open(js_path, "r") as f:
    content = f.read()
    
# Remove duplicate refresh
content = content.replace("refresh: function(frm) {\n\t\t// Override dashboard", "// Override dashboard")

# Inject it inside the original refresh
if "update_actual_medical_status(frm);" in content:
    content = content.replace(
        "update_actual_medical_status(frm);", 
        "update_actual_medical_status(frm);\n\t\tif (frm.dashboard) {\n\t\t\tfrm.dashboard.open_document_list = function($link, show_open) {\n\t\t\t\tlet doctype = $link.attr(\"data-doctype\");\n\t\t\t\tif (doctype && doctype !== \"Candidate Country Process\") {\n\t\t\t\t\tfrappe.route_options = {\n\t\t\t\t\t\t\"candidate_country_process\": frm.doc.candidate_country_process\n\t\t\t\t\t};\n\t\t\t\t} else {\n\t\t\t\t\tfrappe.route_options = {\n\t\t\t\t\t\t\"name\": frm.doc.candidate_country_process\n\t\t\t\t\t};\n\t\t\t\t}\n\t\t\t\tfrappe.set_route(\"List\", doctype);\n\t\t\t};\n\t\t}"
    )

with open(js_path, "w") as f:
    f.write(content)
print("Fixed duplicate refresh key!")
