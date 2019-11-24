
frappe.ready(function () {
    get_website_info_count();
});








function get_website_info_count(){
    $("#project_count").empty();
    $("#employee_count").empty();
    $("#sites_count").empty();
    $("#clients_count").empty();

    frappe.call({
        method: 'one_fm.templates.pages.homepage.get_website_info_count',
        callback: function(r) {
            if(r){
                $("#project_count").html(r.message[0]);
                $("#employee_count").html(r.message[1]);
                $("#sites_count").html(r.message[2]);
                $("#clients_count").html(r.message[3]);
            }
        }
    });
}





// function get_project_phases(project_name){
//     $("#project_phases").empty();

//     frappe.call({
//         method: "one_fm.templates.pages.projects_dashboard.get_project_phases",
//         args: {
//             project: project_name
//         },
//         callback: function (r) {
//             if (r.message) {
//                 $("#project_phases").empty();
//                 var content = ""
//                 var max_output_length = 3
//                 var phase_number = 0
//                 var task_number = 0
//                 // console.log(r.message)

//                 for (let phase = 0; phase < r.message.length; phase++) {
//                     phase_number = phase + 1
//                     content += "<div class='mt-3' style='border:1px solid #E6E6E6;vertical-align: middle'><h6 class='stages s3'>" + r.message[phase][0] + "</h6><div class='d-md-flex justify-content-between'><div class='' style='max-width: 25%;'><h1 class='stage-number'>" + phase_number + "</h1></div><div class='flex-fill p-4' style='max-width: 25%'><h6 class='s3' style='text-align: right;color:#00BDCD'>" + r.message[phase][9] + "</h6><p class='b3' style='text-align: left;color: #B3B3B3'>" + r.message[phase][8] + "</p></div><div class='flex-fill p-4' style='max-width: 25%;'><h6 style='text-align: right;color:#07074E'>حالة اكتمال المرحلة</h6><div class='progress' style='margin-top: auto;'><div class='progress-bar' style='width:" + r.message[phase][4] + "%;background: #00BDCD;'></div></div><h5 style='direction: ltr'>" + r.message[phase][4] + "%</h5><div><table class='table mytable b4'><tr><td rowspan='2' style='vertical-align : middle;text-align:center;'><span style='color:#00BDCD'>" + r.message[phase][1] + "</span><br><span>اجمالي المهام</span></td><td><span style='color:#00BDCD'>" + r.message[phase][15] + "</span><br><span>تحت الإنجاز</span></td><td><span style='color:#00BDCD'>" + r.message[phase][3] + "</span><br><span>المهام المكتملة</span></td></tr><tr><td><span style='color:#00BDCD'>" + r.message[phase][2] + "</span><br><span>معلقة</span></td><td><span style='color:#00BDCD'>" + r.message[phase][14] + "</span><br><span>تم البدء بها</span></td></tr><tr><td colspan='3'>جدول المهام <br><i class='fas fa-caret-down clickable' id='task-arrow-down-"+phase_number+"' onclick='task_arrow_down("+phase_number+")' style='font-size: 19px;color:#07074E'></i><i class='fas fa-caret-up clickable hidden' id='task-arrow-up-"+phase_number+"' onclick='task_arrow_up("+phase_number+")' style='font-size: 19px;color:#07074E'></i></td></tr></table></div></div><div class='flex-fill p-4' style='max-width: 25%'><h6 style='text-align: right'>مخرجات المرحلة</h6><table class='table mytable b3' style='color: #B3B3B3'>";

//                     if(r.message[phase][5].length<3){
//                         max_output_length = r.message[phase][5].length
//                     }
//                     for (let output = 0; output < max_output_length; output++) {
//                         content += "<tr><td><img src='assets/dashboard/assets-fixtag1/img/file-icon-img-blue.png'></td><td><a href='" + r.message[phase][7][output] + "' target='_blank' style='color: #B3B3B3;text-decoration: none;'>" + r.message[phase][5][output] + "</td><td class='left-to-right-direction'>" + r.message[phase][6][output] + "</td></tr>";
//                     }
//                     content += "<tr></tr><tr><td colspan='3' style='color:#07074E;'>المزيد <br><i class='fas fa-caret-down clickable' id='show-outputs-down-"+phase_number+"' onclick='show_outputs_down("+phase_number+")' style='font-size: 19px;color:#07074E'></i><i class='fas fa-caret-up clickable hidden' id='show-outputs-up-"+phase_number+"' onclick='show_outputs_up("+phase_number+")' style='font-size: 19px;color:#07074E'></i></td></tr></table></div></div>";


//                     content += "<div id='task-table-stage-"+phase_number+"' class='hidden' style='margin-left: 6%;margin-right:6% ;background-color: #F7F7F7;vertical-align: middle'><table class='table myTable output-table'><tr><th>رقم المهمة</th><th>مهمة</th><th>تاريخ البدء</th><th>الحالة</th><th>تاريخ الإنجاز</th><th>مرجع المهمة</th><th>تعليق</th></tr>";
//                     for (let output = 0; output < r.message[phase][10].length; output++) {
//                         task_number = output + 1
//                         content += "<tr><td>" + task_number + "</td><td>" + r.message[phase][10][output] + "</td><td>" + r.message[phase][11][output] + "</td><td>" + r.message[phase][12][output] + "</td><td>" + r.message[phase][13][output] + "</td><td>مرجع المهمة</td><td><i id='add-comment-output-stage-1-1' class='fa fa-plus-square clickable' style='font-size:15px;color:#00BDCD'></i></td></tr>";
//                     }
//                     content += "</table></div>";                    


//                     content += "<div id='output-table-stage-"+phase_number+"' class='hidden' style='margin-left: 6%;margin-right:6% ;background-color: #F7F7F7;vertical-align: middle'><table class='table myTable output-table'><tr><th>اسم المخرج</th><th>التاريخ</th><th>الملف</th><th>حالة المخرج</th><th>قبول/رفص المخرج</th><th>تعليق</th></tr>";
//                     for (let output = 0; output < r.message[phase][5].length; output++) {
//                         content += "<tr><td>" + r.message[phase][5][output] + "</td><td>" + r.message[phase][6][output] + "</td><td><a href='" + r.message[phase][7][output] + "' target='_blank'><i class='fa fa-file' style='font-size: 13px;'></i></a></td><td>Approved</td><td><i class='fa fa-circle clickable' style='color: #00BDCD;font-size: 15px;'></i><i class='fa fa-circle clickable' style='color: #F86464;font-size: 15px'></i></td><td><i id='add-comment-output-stage-1-1' class='fa fa-plus-square clickable' style='font-size:15px;color:#00BDCD'></i></td></tr>";
//                     }
//                     content += "</table></div></div>";

//                 }


//                 $("#project_phases").append(content)

//             }
//         }
//     })

// }






function send_contact_email(){
    frappe.call({
        method: 'one_fm.templates.pages.homepage.send_contact_email',
        callback: function(r) {
            if(r){
                console.log(r.message)
            }
        }
    });
}



