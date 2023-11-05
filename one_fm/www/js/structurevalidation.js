$(document).ready(function () {
    //Add service and procedures
    $("#structuremodalform").validate({
        errorClass: 'Error',
        rules:
        {
            txtstructurename:
            {
                required: true,
            },
            txtcompanyid:
            {
                required: true,
            },
            txtmanagername:
            {
                required: true,
            }
          

        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
            txtstructurename:
            {
                required: "This field is required",
            },
            txtcompanyid:
            {
                required: "This field is required",
            },
            txtmanagername:
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