frappe.listview_settings['Request for Purchase'] = {
    
    
    get_indicator: function(doc) {
        const status_colors = {
            "Draft": "grey",
            "Draft Request": "grey",
            "Accepted": "blue",
            "Approved": "blue",
            "To Order": "orange",
            "Partially Ordered": "yellow",
            "Ordered": "green",
            "Rejected": "red",
            "Submitted": "blue",
            "Cancelled": "red"
        };
        
        if (doc.status && doc.docstatus === 1) {
            return [__(doc.status), status_colors[doc.status] || "grey", "status,=," + doc.status];
        }

        return ["Draft", "grey", "status,=,Draft"];
    },
    
    hide_name_column: false
};
