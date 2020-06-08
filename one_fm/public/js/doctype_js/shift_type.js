frappe.ui.form.on('Shift Type', {
    start_time: function(frm){
        calculate_duration(frm);
    },
    end_time: function(frm){
        calculate_duration(frm);
    },
    validate: function(frm){
        calculate_duration(frm);
    }
});

function calculate_duration(frm){
    let {start_time, end_time} = frm.doc;
    if(start_time !== undefined && end_time !== undefined){
        let start = moment(start_time, 'HH:mm:ss');
        let end = moment(end_time, 'HH:mm:ss');
        let hours = '';
        if(start < end){
            let duration = moment.duration(end.diff(start));
            hours = duration.asHours();
        }else{
            let eod = moment("24:00:00", 'HH:mm:ss');
            let sod = moment("00:00:00", 'HH:mm:ss');
            let duration1 = moment.duration(eod.diff(start)).asHours();
            let duration2 = moment.duration(end.diff(sod)).asHours();
            hours = duration1 + duration2;
        }
        frappe.model.set_value(frm.doctype, frm.doc.name, "duration", hours);    
    }
}