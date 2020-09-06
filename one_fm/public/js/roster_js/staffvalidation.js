$(document).ready(function () {
    //Add service and procedures
    $("#staffformmodal").validate({
        errorClass: 'Error',
        rules:
        {
            txtstaffname:
            {
                required: true,
            },
            txtnameposition:
            {
                required: true,
            }


        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
            txtstaffname:
            {
                required: "This field is required",
            },
            txtnameposition:
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