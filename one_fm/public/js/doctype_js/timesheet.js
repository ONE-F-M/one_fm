frappe.ui.form.on("Timesheet", {
	onload: function(frm){
        if(frm.doc.employee == "HR-EMP-01207"){
            let notes_template = "<p>*1 Setting up systems.</p><p>*2</p><p><br></p><p><strong>End of the day review:</strong></p><p><br></p><p><strong>Tomorrow&apos;s plan:</strong></p><p><br></p>";
            frm.set_value('note', notes_template);
        }        

	},
});