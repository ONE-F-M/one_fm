frappe.ready(function() {
    $('#submit').on('click', function(){
        let args = $('#parent-refs').data() || {}; 
        for(i=1;i<10;i++){
            console.log(i, $(`[name=${i}]:checked`).val())
            args[i] = $(`[name=${i}]:checked`).val();
        }
        args['10'] = frappe.utils.xss_sanitise($("textarea[name=10]").val());

        console.log(args);
        frappe.call({
            method: "one_fm.one_fm.doctype.training_evaluation_form.training_evaluation_form.submit_training_feedback", //dotted path to server method
            args: {args},
            callback: function(r) {
                // code snippet
            }
        })
    })
})