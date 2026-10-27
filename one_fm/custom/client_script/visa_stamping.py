def get_visa_stamping_client_scripts():
	return [
		{
			"name": "Test Visa Stamping",
			"dt": "Visa Stamping",
			"view": "Form",
			"enabled": 1,
			"script": "frappe.ui.form.on('Visa Stamping', {\n\trefresh(frm) {\n\t\t// your code here\n\t}\n})",
		},
	]
