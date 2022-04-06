$(document).ready(function () {
    //Add service and procedures
    $("#shiftformmodal").validate({
        errorClass: 'Error',
        rules:
        {
            txtshiftname:
            {
                required: true,
            },
            txtselectmanagername:
            {
                required: true,
            },
            txtstarttime:
            {
                required: true,
            },
            txtendtime:
            {
                required: true,
            },


        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
            txtshiftname:
            {
                required: "This field is required",
            },
            txtselectmanagername:
            {
                required: "This field is required",
            },
            txtstarttime:
            {
                required: "This field is required",
            },
            txtendtime:
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