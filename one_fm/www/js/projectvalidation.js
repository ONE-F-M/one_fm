$(document).ready(function () {
    //Add service and procedures
    $("#editformmodal").validate({
        errorClass: 'Error',
        rules:
        {
            txtproject:
            {
                required: true,
            },
            txtsite:
            {
                required: true,
            },
            txtshift:
            {
                required: true,
            },
            txtinputdate:
            {
                required: true,
            },
           

        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
            txtproject:
            {
                required: "This field is required",
            },
            txtsite:
            {
                required: "This field is required",
            },
            txtshift:
            {
                required: "This field is required",
            },
            txtinputdate:
            {
                required: "This field is required",
            }
           
        },
        highlight: function (element) {
            $(element).parent().addClass('error');
        },
        unhighlight: function (element) {
            $(element).parent().removeClass('error');
        }
    });

});