frappe.ready(function () {

    frappe.msgprint("Please select an option!")


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



