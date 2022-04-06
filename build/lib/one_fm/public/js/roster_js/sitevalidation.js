$(document).ready(function () {
    //Add service and procedures
    $("#siteformmodal").validate({
        errorClass: 'Error',
        rules:
        {
            txtsitename:
            {
                required: true,
            },
            txtsitemanagername:
            {
                required: true,
            }

        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
            txtsitename:
            {
                required: "This field is required",
            },
            txtsitemanagername:
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