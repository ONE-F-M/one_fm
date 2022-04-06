$(document).ready(function () {
    //Add service and procedures
    //$("#dayoffformmodal").validate({
    //    errorClass: 'Error',
    //    rules:
    //    {
    //        //txtselectdayoff:
    //        //{
    //        //    required: true,
    //        //}           
    //    },
    //    messages:
    //    {
    //        //This section we need to place our custom validation message for each control. 
    //        //txtselectdayoff:
    //        //{
    //        //    required: "This field is required",
    //        //}
    //    },
    //    highlight: function (element) {
    //        $(element).parent().addClass('error');
    //    },
    //    unhighlight: function (element) {
    //        $(element).parent().removeClass('error');
    //    }
    //});
    $("#leaveabsentformmodal").validate({
        errorClass: 'Error',
        rules:
        {
            txtleaveinput:
            {
                required: true,
            },
            txtleavestartinputdate:
            {
                required: true,
            },
            txtleaveendinputdate:
            {
                required: true,
            }

        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
            txtleaveinput:
            {
                required: "This field is required",
            },
            txtleavestartinputdate:
            {
                required: "This field is required",
            },
            txtleaveendinputdate:
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
    $("#assignformmodal").validate({
        errorClass: 'Error',
        rules:
        {
            txtposttype:
            {
                required: true,
            },
            txtpoststartdate:
            {
                required: true,
            },
            //txtpostenddate:
            //{
            //    required: true,
            //},
            txtsetdayoff:
            {
                required: true,
            },


        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
            txtposttype:
            {
                required: "This field is required",
            },
            txtpoststartdate:
            {
                required: "This field is required",
            },
            //txtpostenddate:
            //{
            //    required: "This field is required",
            //},
            txtsetdayoff:
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
    $("#unassignformmodal").validate({
        errorClass: 'Error',
        rules:
        {
            txtinputunassignstart:
            {
                required: true,
            }
        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
            txtinputunassignstart:
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
    $("#addpostformmodal").validate({
        errorClass: 'Error',
        rules:
        {
            postcalendertype:
            {
                required: true,
            },
            postcalenderrepeatpost:
            {
                required: true,
            },
            postcalenderrepeatday:
            {
                required: true,
            },
            txtpostafterdate:
            {
                required: true,
            },
            txtpostfromdate:
            {
                required: true,
            },
            txtposttodate:
            {
                required: true,
            },
            txtpostfromcanceldate:
            {
                required: true,
            },
            
        },
        messages:
        {
            //This section we need to place our custom validation message for each control. 
          
            postcalendertype:
            {
                required: "This field is required",
            },
            postcalenderrepeatpost:
            {
                required: "This field is required",
            },
            postcalenderrepeatday:
            {
                required: "This field is required",
            },
            txtpostafterdate:
            {
                required: "This field is required",
            },
            txtpostfromdate:
            {
                required: "This field is required",
            },
            txtposttodate:
            {
                required: "This field is required",
            },
            txtpostfromcanceldate:
            {
                required: "This field is required",
            },

        },
        highlight: function (element) {
            $(element).parent().addClass('error');
        },
        unhighlight: function (element) {
            $(element).parent().removeClass('error');
        }
    });

});