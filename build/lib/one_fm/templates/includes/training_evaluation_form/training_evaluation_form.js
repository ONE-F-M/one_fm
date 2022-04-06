frappe.ready(function() {
    $('#submit').on('click', function(){
        let args = $('#parent-refs').data() || {}; 
        let rows = $('[name=parent-wrapper]').children().length;
        for(i=1;i<rows;i++){
            args[i] = $(`[name=${i}]:checked`).val();
        }
        args['additional_comments'] = frappe.utils.xss_sanitise($("textarea[name='additional_comments']").val());

        console.log(args);
        frappe.call({
            method: "one_fm.one_fm.doctype.training_evaluation_form.training_evaluation_form.submit_training_feedback", //dotted path to server method
            args: {args},
            freeze: true,
            freeze_message: __("Submitting"),
            callback: function(r) {
                if(!r.exc && r.message){
                    frappe.msgprint(__("Feeback Submitted!"));
                }
            }
        })
    })
})