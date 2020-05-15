frappe.ui.form.on('Shift Type', {
    start_time: function(frm){
        calculate_duration(frm);
    },
    end_time: function(frm){
        calculate_duration(frm);
    },
});

function calculate_duration(frm){
    let {start_time, end_time} = frm.doc;
    if(start_time !== undefined && end_time !== undefined){
        let duration = moment.duration(moment(end_time, 'HH:mm:ss').diff(moment(start_time, 'HH:mm:ss')));
        let hours = duration.asHours();
        frappe.model.set_value(frm.doctype, frm.doc.name, "duration", hours);
    }
}