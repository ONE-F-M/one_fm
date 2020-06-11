frappe.ready(function () {

    frappe.call({
        method: 'one_fm.templates.pages.gp_letter_request.validate_gp_letter_request_status',
        args:{
            pid: $('#pid').val(),
            gp_status: $('#gp_status').val()
        },
        callback: function(r) {
            if(r){
                if (r.message=='false'){
                    $('#gp_status').prop('disabled', true);
                    $('#submit').prop('disabled', true);
                }
            }
        }
    });


    $("#submit").click(function(e){

        frappe.call({
            method: 'one_fm.templates.pages.gp_letter_request.update_gp_letter_request_status',
            args:{
                pid: $('#pid').val(),
                gp_status: $('#gp_status').val()
            },
            callback: function(r) {
                if(r){
                    $('#gp_status').prop('disabled', true);
                    $('#submit').prop('disabled', true);
                }
            }
        });


    });


});



