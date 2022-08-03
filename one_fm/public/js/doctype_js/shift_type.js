frappe.ui.form.on('Shift Type', {
    start_time: function(frm){
        fill_spilt_shift_time(frm)
        calculate_duration(frm);
    },
    end_time: function(frm){
        fill_spilt_shift_time(frm)
        calculate_duration(frm);
    },
    validate: function(frm){
        calculate_duration(frm);
    },
    has_split_shift: function(frm){
        // fill_spilt_shift_time(frm)
        calculate_duration(frm);
    },
    first_shift_end_time:function(frm){
        calculate_duration(frm);
    },
    second_shift_start_time:function(frm){
        calculate_duration(frm);
    }
});
function fill_spilt_shift_time(frm){
    if(frm.doc.start_time){
        frappe.model.set_value(frm.doctype, frm.doc.name, "first_shift_start_time", frm.doc.start_time);    
    }
    if(frm.doc.end_time){
        frappe.model.set_value(frm.doctype, frm.doc.name, "second_shift_end_time", frm.doc.end_time);    
    }
}
function calculate_duration(frm){
    let {start_time, end_time, first_shift_end_time , second_shift_start_time} = frm.doc;
    let hours = ''
    if(frm.doc.has_split_shift == 1){
        if( start_time !== undefined && end_time !== undefined && first_shift_end_time !== undefined && second_shift_start_time !== undefined){
            hours = time_duration(moment(start_time, 'HH:mm:ss'),moment(first_shift_end_time, 'HH:mm:ss')) + time_duration(moment(second_shift_start_time, 'HH:mm:ss'),moment(end_time, 'HH:mm:ss'))
        }
    }
    else if(start_time !== undefined && end_time !== undefined){
        hours = time_duration(moment(start_time, 'HH:mm:ss'),moment(end_time, 'HH:mm:ss'))
    }
            
    frappe.model.set_value(frm.doctype, frm.doc.name, "duration", hours);    
     
}

function time_duration(start, end){
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
    return hours
}