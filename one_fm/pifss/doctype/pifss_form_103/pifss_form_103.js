frappe.ui.form.on('PIFSS Form 103', {
	onload: function(frm){
		frm.set_query("employee", function() {
			return {
				"filters": {
					"one_fm_nationality": "Kuwaiti",
				}
			};
		});
		if(frm.doc.__islocal){
			frappe.db.get_value("Company", {"name": frappe.user_defaults.company} ,["company_name_arabic", "pifss_registration_no"], 
			function(res){
				console.log(res)
				let {company_name_arabic, pifss_registration_no} = res;
				frm.set_value("company_name_arabic", company_name_arabic);
				frm.set_value("company_pifss_registration_no", pifss_registration_no);
			})

		}		
	},
	refresh: function(frm){
		if(!frm.doc.__islocal){
			frm.set_df_property("request_type","read_only", 1);
		}
	},
	employee: function(frm) {
		let {employee, request_type} = frm.doc;
		if(employee && request_type === "Registration"){
			frappe.db.get_doc("Employee", employee)
			.then(res => {
				let {one_fm_employee_documents} = res;
				one_fm_employee_documents.forEach(function(i, v){
					if(i.document_name == "Birth Certificate"){
						frm.set_value("date_of_birth_certificate", i.attach);
					}else if(i.document_name == "Nationality Proof"){
						frm.set_value("nationality_proof", i.attach);	
					}else if(i.document_name == "Civil ID"){
						frm.set_value("civil_id_copy", i.attach);
					}
				})
			})
		}
	},
	request_type: function(frm) {
		let {request_type} = frm.doc;
		if(request_type === "Registration"){
			frm.set_value("naming_series", "REG-.{employee}.-");
		}else if(request_type === "End of Service"){
			frm.set_value("naming_series", "END-.{employee}.-");
		}
	}
});
