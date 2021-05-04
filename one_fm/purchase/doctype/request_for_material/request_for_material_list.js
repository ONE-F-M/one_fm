frappe.listview_settings['Request for Material'] = {
	add_fields: ["type", "status", "per_ordered"],
	get_indicator: function(doc) {
		if(doc.status=="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} else if(doc.docstatus==1 && flt(doc.per_ordered, 2) == 0) {
			return [__("Pending"), "orange", "per_ordered,=,0"];
		}  else if(doc.docstatus==1 && flt(doc.per_ordered, 2) < 100) {
			return [__("Partially ordered"), "yellow", "per_ordered,<,100"];
		} else if(doc.docstatus==1 && flt(doc.per_ordered, 2) == 100) {
			if (doc.type == "Individual" || doc.type == "Onboarding") {
				return [__("Issued"), "green", "per_ordered,=,100"];
			} else if (doc.type == "Project" || doc.type == "Project Mobilization" || doc.type == "Stock") {
				return [__("Transferred"), "green", "per_ordered,=,100"];
			}
		}
	}
};