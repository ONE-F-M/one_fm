frappe.pages['roster'].on_page_load = function(wrapper) {
	// console.log("[WRAPPER]", wrapper);
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Roster',
		single_column: true
	});
	
	$('.content.page-container').empty().append(frappe.render_template('roster'));

	console.log(page, cur_page);
	$('.content.page-container').find('.redirect_route').on('click', function(e){
		// console.log(e, this);
		let template = $(this).attr('data-route');
		$('.content.page-container').empty().append(frappe.render_template(template));
		load_js(page);
	})
	
	load_js(page);
}

function load_js(page){
	
    window.isMonth = 1;
    window.classgrtw = [];
    window.classgrt = [];

	setup_filters(page);
	setup_staff_filters(page);
	setup_topbar_events(page);
    //postcalendertype
    $("#selRetrive").hide();
    $(this).scrollTop(0);

	$(`a[href="#"]`).click(function (e) {
		console.log(!$(this).hasClass('navbar-brand'), this);
		if(!$(this).hasClass('navbar-brand')){
			e.preventDefault();
		}
    });
    $(".customredropdown .customdropdownheight .dropdown-item").click(function () {
        var text = $(this).html();
        $(this).parent().parent().parent().find(".dropdown-toggle .dropdowncustomres").html(text);
    });

	window.today = new Date();
    today.setHours(0, 0, 0, 0);
	if($('.layoutSidenav_content').attr('data-view') == 'roster'){ 
		page.datepicker = $("#datepicker").flatpickr({inline: true});
		page.datepicker.config.onChange.push(function (selectedDates, dateStr, instance) {
			$("#calenderviewtable th").removeClass("hightlightedtable");
			let evt = new Date(dateStr);
			console.log(evt);
			window.calendarSettings1 = {
				date: moment(new Date(evt.getFullYear(), evt.getMonth(), evt.getDate())),//.set("date", 4),
				today: moment()
			}
			window.weekCalendarSettings = {
				date: moment(new Date(evt.getFullYear(), evt.getMonth(), evt.getDate())).startOf("isoweek"),
				today: moment()
			}
			// displayCalendar(calendarSettingsmain, page);
			let element = get_wrapper_element();
			if(element == '.rosterMonth' || element == '.postMonth'){
				displayCalendar(calendarSettings1, page);
				GetHeaders(1);
				
				element = element.slice(1);
				page[element](page);			
				// $(element).find("#data-day_" + evt.getDate()).addClass("hightlightedtable");
				$(element).find('.rosterViewTH').children().removeClass("hightlightedtable")
				$(element).find('.rosterViewTH').find("#data-day_" + evt.getDate()).addClass("hightlightedtable");
				
			}else{
				displayWeekCalendar(weekCalendarSettings, page);
				GetWeekHeaders(1);
				
				element = element.slice(1);
				page[element](page);			
				$(element).find('.rosterViewTH').children().removeClass("hightlightedtable")
				$(element).find('.rosterViewTH').find("#data-day_" + evt.getDate()).addClass("hightlightedtable");
			}
			// $(this1).parent().children().removeClass("hightlightedtable")
			// $(this1).addClass("hightlightedtable");

		})
		$('.flatpickr-next-month').on('click', function(){
			incrementMonth(page);
		})
		$('.flatpickr-prev-month').on('click', function(){
			decrementMonth(page);
		})
		// partialviewgetMonthviewdata();
		$(".rosterviewclick").click(function () {
			// console.log(this);
			$('.rosterMonth').removeClass("d-none");
			$('.postMonth').addClass("d-none");		
			$('.rosterWeek').addClass("d-none");
			$('.postWeek').addClass("d-none");
			$(".maintabclick").removeClass("active");
			$(this).parent().addClass("active");
			$(".Postfilterhideshow").addClass("d-none");
			$(".filterhideshow").addClass("d-none");
			$(".rosterviewfilterbg").removeClass("d-none");
			$(".postviewfilterbg").addClass("d-none");
			// partialviewgetMonthviewdata();
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".rosterMonth");
			get_roster_data(page);
	
		});
		$(".postviewclick").click(function () {
			// console.log(this);
			$('.rosterMonth').addClass("d-none");
			$('.postMonth').removeClass("d-none");
			$('.rosterWeek').addClass("d-none");
			$('.postWeek').addClass("d-none");
			$(".maintabclick").removeClass("active");
			$(this).parent().addClass("active");
			$(".Postfilterhideshow").addClass("d-none");
			$(".filterhideshow").addClass("d-none");
			$(".rosterviewfilterbg").addClass("d-none");
			$(".postviewfilterbg").removeClass("d-none");
			displayCalendar(calendarSettings1, page);
			GetHeaders(0, ".postMonth");
			get_post_data(page);
			// partialviewgetPostMonthviewdata();
		});
	
	
		
		//week view click jquery
		$('.postweekviewclick').click(function () {
			console.log("SSSSSSSSSSSSs");            
			$('.rosterMonth').addClass("d-none");
			$('.postMonth').addClass("d-none");
			$('.rosterWeek').addClass("d-none");
			$('.postWeek').removeClass("d-none");
			displayWeekCalendar(weekCalendarSettings, page);
			
			GetWeekHeaders(0, ".postWeek");
			get_post_week_data(page);
		});
		//week view click jquery
		$('.postmonthviewclick').click(function () {
			console.log("SSSSSSSSSSSSs");            
			$('.rosterMonth').addClass("d-none");
			$('.postMonth').removeClass("d-none");
			$('.rosterWeek').addClass("d-none");
			$('.postWeek').addClass("d-none");
			displayCalendar(calendarSettings1, page);
			
			GetHeaders(1, ".postMonth");
			get_post_data(page);
		});
		$('.monthviewclick').click(function () {
			console.log("SSSSSSSSSSSSs");            
			$('.rosterMonth').removeClass("d-none");
			$('.postMonth').addClass("d-none");
			$('.rosterWeek').addClass("d-none");
			$('.postWeek').addClass("d-none");
			displayCalendar(calendarSettings1, page);
			
			GetHeaders(1, ".rosterMonth");
			get_roster_data(page);
		});
		//tab click for week view data function call
		$(".weekviewclick").click(function () {
			// partialviewgetWeekviewdata();
			$('.rosterMonth').addClass("d-none");
			$('.postMonth').addClass("d-none");
			$('.rosterWeek').removeClass("d-none");
			$('.postWeek').addClass("d-none");
			// isMonth = 0;
			displayWeekCalendar(weekCalendarSettings, page);
			
			GetWeekHeaders(0, ".rosterWeek");
			get_roster_week_data(page);
		});
		//tab click for week view data function call

		$(".editpostclassclick").click(function () {
			$(".postmodaltitlechange").html("Edit Post");
			let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
			let d = new frappe.ui.Dialog({
				title: 'Edit Post',
				fields: [
					{
						label: 'Post Status',
						fieldname: 'post_status',
						fieldtype: 'Select',
						options: '\nPost Off\nSuspend Post\nCancel Post',
						reqd:1
					},
					{
						fieldname: 'sb1',
						fieldtype: 'Section Break',
						depends_on: "eval:this.get_value('post_status') == 'Cancel Post'",
					},
					{
						label: 'Cancel From Date',
						fieldname: 'cancel_from_date',
						fieldtype: 'Date',
						default: date,
						onchange:function(){
							let cancel_from_date = d.get_value('cancel_from_date');
							if(cancel_from_date && moment(cancel_from_date).isBefore(moment(frappe.datetime.nowdate()))){
								// d.set_value('cancel_from_date', date);
								frappe.throw(__("Cancel From date cannot be before today."));
							}
						}
					},
					{
						fieldname: 'sb3',
						fieldtype: 'Section Break',
						depends_on: "eval:this.get_value('post_status') == 'Post Off'",
					},
					{
						label: 'Paid',
						fieldname: 'post_off_paid',
						fieldtype: 'Check',
						onchange: function(){
							let val = d.get_value('post_off_paid');
							if(val){
								d.set_value('post_off_unpaid', 0);
							}
						}
					},			
					{
						fieldname: 'cb7',
						fieldtype: 'Column Break',
					},
					{
						label: 'Unpaid',
						fieldname: 'post_off_unpaid',
						fieldtype: 'Check',
						onchange: function(){
							let val = d.get_value('post_off_unpaid');
							if(val){
								d.set_value('post_off_paid', 0);
							}
						}
					},
					{
						fieldname: 'sb5',
						fieldtype: 'Section Break',
						depends_on: "eval:this.get_value('post_status') == 'Post Off'",
					},
					{
						label: 'Repeat',
						fieldname: 'repeat',
						fieldtype: 'Select',
						options: '\nDoes not repeat\nDaily\nWeekly\nCustom recurrence',
					},
					{
						fieldname: 'sb2',
						fieldtype: 'Section Break',
						depends_on: "eval:this.get_value('post_status') == 'Suspend Post'",
					},
					{
						label: 'Paid',
						fieldname: 'suspend_paid',
						fieldtype: 'Check',
						onchange: function(){
							let val = d.get_value('suspend_paid');
							if(val){
								d.set_value('suspend_unpaid', 0);
							}
						}
					},	
					{
						label: 'Suspend From Date',
						fieldname: 'suspend_from_date',
						fieldtype: 'Date',
						default: date,
						onchange:function(){
							let suspend_from_date = d.get_value('suspend_from_date');
							if(suspend_from_date && moment(suspend_from_date).isBefore(moment(frappe.datetime.nowdate()))){
								// d.set_value('suspend_from_date', date);
								frappe.throw(__("Suspend From Date cannot be before today."));
							}
						}
						
					},	
					{
						label: 'Never End',
						fieldname: 'never',
						fieldtype: 'Check',
					},			
					{
						fieldname: 'cb1',
						fieldtype: 'Column Break',
					},
					{
						label: 'Unpaid',
						fieldname: 'suspend_unpaid',
						fieldtype: 'Check',
						onchange: function(){
							let val = d.get_value('suspend_unpaid');
							if(val){
								d.set_value('suspend_paid', 0);
							}
						}
					},	
					{
						label: 'Suspend Till Date',
						fieldname: 'suspend_to_date',
						fieldtype: 'Date',
						default: date,
						onchange:function(){
							let suspend_to_date = d.get_value('suspend_to_date');
							if(suspend_to_date && moment(suspend_to_date).isBefore(moment(frappe.datetime.nowdate()))){
								// d.set_value('suspend_to_date', date);
								frappe.throw(__("Suspend To Date cannot be before today."));
							}
						}
					},
				],
				primary_action_label: 'Submit',
				primary_action(values) {
					console.log(values);
					d.hide();
				}
			});
			
			d.show();
		});
		//check schedule staff on load
		$("#chkassgined").prop("checked", true);
		$("#chkassgined").trigger("change");



		$(".select2plg").select2({});
		// console.log(page);
		// get_roster_data(page);
		// Add employee modal
		$("#addemployeeselect").select2({
			placeholder: "Search Employee",
		});
		
		//========================================== Roster Calendar Month View

		//display title of calender ex: Month of Jul 1 - 31, 2020
		window.calendarSettings1 = {
			date: moment().set("date", 4),
			today: moment()
		}
		window.weekCalendarSettings = {
			date: moment().startOf("isoweek"),
			today: moment()
		}
		

		//display title of calender ex: Month of Jul 1 - 31, 2020
		GetHeaders(0);


		
		displayCalendar(calendarSettings1, page);
		//display title of calender ex: Month of Jul 1 - 31, 2020
		//add array on each of data select from calender
		$(".posthoverselectclass").on("click", function () {
			$(this).toggleClass('selectclass');
			// If the id is not already in the array, add it. If it is, remove it

			classgrt.indexOf(this.getAttribute('data-selectid')) === -1 ? classgrt.push(this.getAttribute('data-selectid')) : classgrt.splice(classgrt.indexOf(this.getAttribute('data-selectid')), 1);
			
			if (classgrt.join(",") === '') {
				$('.Postfilterhideshow').addClass('d-none');
			}
			else { 
				$('.Postfilterhideshow').removeClass('d-none');
			}
			// populate the input with the array items separated with a comma
		});
		//add array on each of data select from calender    
		page.rosterMonth = get_roster_data;
		page.rosterWeek = get_roster_week_data;
		page.postWeek = get_post_week_data;
		page.postMonth = get_post_data;
		//function call
		GetTodaySelectedDate();

	}	

    $(".modal").on("hidden.bs.modal", function () {
        $("#dayoffmodal").trigger("reset");
        $("#dayoffmodal").validate().resetForm();
        $("#leaveabsentmodal").trigger("reset");
        $("#leaveabsentmodal").validate().resetForm();
        $("#assignchangemodal").trigger("reset");
        $("#assignchangemodal").validate().resetForm();
        $("#unassignchangemodal").trigger("reset");
        $("#unassignchangemodal").validate().resetForm();
        $("#addpostformmodal").trigger("reset");
        $("#addpostformmodal").validate().resetForm();
        $(".select2plg").val(null).trigger("change");
        $("#addemployeeselect").val(null).trigger("change");
        $(".postoffdiv").addClass("d-none");
        $(".suspendpostdiv").addClass("d-none");
        $(".cancelpostcalenderdiv").addClass("d-none");
    });
    $("#sidebarToggle").on("click", function (e) {
        e.preventDefault();
        $("body").toggleClass("sb-sidenav-toggled");
    });





    $("#dayoffformmodal").on("hidden.bs.modal", function () {
        $("#chkDayOnly").show();
    });
    //let classgrt = [];

    $(`input[name="neverselectallcheckbox"]`).on("change", function () {

        if ($(this).is(":checked")) {
            $("#txtpostenddate").addClass("pointerClass");
            //add values to [] list 

            $(".selectclass").map(function () {
                //console.log($(this).attr("data-selectid"));
                if (($(this).attr("data-selectid") != undefined) && ($(this).attr("data-selectid") != null) && ($(this).attr("data-selectid") != "")) {
                    if (isMonth == 1) {
                        classgrt.push($(this).attr("data-selectid"));
                        // console.log(classgrt);
                    }
                    else {
                        classgrtw.push($(this).attr("data-selectid"));
                        // console.log(classgrtw);
                    }
                }
            });

        }
        else {
            $("#txtpostenddate").removeClass("pointerClass");
            classgrt = [];
            classgrtw = [];
        }
    });
	// Show Active Post value change
    $(`input[name="chkpostActivePost"]`).on("change", function () {

        if ($(this).is(":checked")) {
            $("#calenderviewtable tbody tr td").not(".redboxcolor").parent().removeClass("d-none");
            if ($(`input[name="chkpostCancelPost"]`).is(":checked")) {
                $("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().removeClass("d-none");
            }
            else {
                $("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().addClass("d-none");
            }
        }
        else {
            $("#calenderviewtable tbody tr td").not(".redboxcolor").parent().addClass("d-none");

            if ($(`input[name="chkpostCancelPost"]`).is(":checked")) {
                $("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().removeClass("d-none");
            }
            else {
                $("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().addClass("d-none");
            }
        }

    });
	// Show InActive Post value change
    $(`input[name="chkpostCancelPost"]`).on("change", function () {

        if ($(this).is(":checked")) {
            $("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().removeClass("d-none");
        }
        else {
            $("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().addClass("d-none");
        }
        //chkpostCancelPost
    });


    $(`input[id="chkAllStaff"]`).on("change", function () {
        if ($(this).is(":checked")) {
            $("#chkschedule").prop("checked", true);
            $("#chkunschedule").prop("checked", true);
            $("#chkassgined").prop("checked", true);
            $("#chkunassgined").prop("checked", true);

            $("#scheduledStaff1").removeClass("d-none");
            $("#scheduledStaff2").removeClass("d-none");

            $("#chilldtable1").removeClass("d-none");
            $("#chilldtable2").removeClass("d-none");
            $("#unScheduleStaff").removeClass("d-none");
            $("#chilldtable3").removeClass("d-none");
            $("#rowchilldtable3").removeClass("d-none");
        }
        else {
            $("#chkschedule").prop("checked", false);
            $("#chkunschedule").prop("checked", false);
            $("#chkassgined").prop("checked", false);
            $("#chkunassgined").prop("checked", false);

            $("#scheduledStaff1").addClass("d-none");
            $("#scheduledStaff2").addClass("d-none");

            $("#chilldtable1").addClass("d-none");
            $("#chilldtable2").addClass("d-none");

            $("#rowchilldtable1").addClass("d-none");
            $("#rowchilldtable2").addClass("d-none");

            $("#unScheduleStaff").addClass("d-none");
            $("#chilldtable3").addClass("d-none");
            $("#rowchilldtable3").addClass("d-none");
        }
    });

    $(`input[id="chkassgined"]`).on("change", function () {
        if ($(this).is(":checked")) {
            $("#chkschedule").prop("checked", true);
            $("#chkunschedule").prop("checked", true);
            $("#chkassgined").prop("checked", true);

            $("#chkschedule").prop("disabled", true);
            $("#chkunschedule").prop("disabled", true);

            $("#scheduledStaff1").removeClass("d-none");
            $("#scheduledStaff2").removeClass("d-none");

            $("#chilldtable1").removeClass("d-none");
            $("#chilldtable2").removeClass("d-none");
            $("#unScheduleStaff").removeClass("d-none");
            $("#chilldtable3").removeClass("d-none");
            $("#rowchilldtable3").removeClass("d-none");
        }
        else {
            $("#chkschedule").prop("checked", false);
            $("#chkunschedule").prop("checked", false);
            $("#chkassgined").prop("checked", false);

            $("#chkschedule").prop("disabled", false);
            $("#chkunschedule").prop("disabled", false);

            $("#scheduledStaff1").addClass("d-none");
            $("#scheduledStaff2").addClass("d-none");

            $("#chilldtable1").addClass("d-none");
            $("#chilldtable2").addClass("d-none");

            $("#rowchilldtable1").addClass("d-none");
            $("#rowchilldtable2").addClass("d-none");

            $("#unScheduleStaff").addClass("d-none");
            $("#chilldtable3").addClass("d-none");
            $("#rowchilldtable3").addClass("d-none");
        }
    });

    $(`input[id="chkschedule"]`).on("change", function () {
        if ($(this).is(":checked")) {

            $("#scheduledStaff1").removeClass("d-none");
            $("#scheduledStaff2").removeClass("d-none");

            $("#chilldtable1").removeClass("d-none");
            $("#chilldtable2").removeClass("d-none");


            $("#rowchilldtable1").removeClass("d-none");
            $("#rowchilldtable2").removeClass("d-none");

            $("#unScheduleStaff").addClass("d-none");
            $("#chilldtable3").addClass("d-none");
            $("#rowchilldtable3").addClass("d-none");

            $("#chkunschedule").prop("checked", false);
        }
        else {
            $("#scheduledStaff1").addClass("d-none");
            $("#scheduledStaff2").addClass("d-none");

            $("#chilldtable1").addClass("d-none");
            $("#chilldtable2").addClass("d-none");

            $("#rowchilldtable1").addClass("d-none");
            $("#rowchilldtable2").addClass("d-none");
        }
    });

    $(`input[id="chkunschedule"]`).on("change", function () {
        if ($(this).is(":checked")) {

            $("#unScheduleStaff").removeClass("d-none");
            $("#chilldtable3").removeClass("d-none");
            $("#rowchilldtable3").removeClass("d-none");
            // $("#chilldtable3").css("display","none !important");

            $("#scheduledStaff1").addClass("d-none");
            $("#scheduledStaff2").addClass("d-none");

            $("#chilldtable1").addClass("d-none");
            $("#chilldtable2").addClass("d-none");

            $("#rowchilldtable1").addClass("d-none");
            $("#rowchilldtable2").addClass("d-none");

            $("#chkschedule").prop("checked", false);

        }
        else {
            $("#unScheduleStaff").addClass("d-none");
            $("#chilldtable3").addClass("d-none");
            $("#rowchilldtable3").addClass("d-none");
            // $("#chilldtable3").css("display", "block");

        }
    });

	//table custom accordian click
	$(".clickablerow").click(function () {
		$(this).parent().next().toggleClass("show");

		if ($(this).parent().next().hasClass("show")) {
			$(this).attr("aria-expanded", "true");
		}
		else {
			$(this).attr("aria-expanded", "false");
		}

		$(".clickablerow").not(this).attr("aria-expanded", "false");
		$(".clickablerow").not(this).parent().next().removeClass("show");
	});
	//table custom accordian click

}

function setup_topbar_events(page){
	$('.dayoff').on('click', function(){
		// unschedule_staff
	});

	$('.scheduleleave').on('click', function(){
		schedule_leave(page);		
	});

	$('.changepost').on('click', function(){
		schedule_change_post(page);		
		change_post(page);		
	});

	$('.assignchangemodal').on('click', function(){
		unschedule_staff(page);
	});
}

function bind_events(page){
	//add array on each of data select from calender
	$('.rosterMonth').find(".hoverselectclass").on("click", function () {
		$(this).toggleClass("selectclass");
		// If the id is not already in the array, add it. If it is, remove it  
		classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);

		if (classgrt.join(",") === "") {
			$(".filterhideshow").addClass("d-none");
		}
		else {
			$(".filterhideshow").removeClass("d-none");

			if (classgrt.length >= 1) {
				$("#divStartDate").addClass("d-none");
				$("#divEndDate").addClass("d-none");
				$("#chkDayOnly").hide();
				$("#chkSelectedDayOnly").removeClass("pointerClass");
				$("#divRepeat").removeClass("pointerClass");
				$("#divSetDayOff").hide();
			}
			else {

				$("#divStartDate").removeClass("d-none");
				$("#divEndDate").removeClass("d-none");
				$("#chkDayOnly").show();
				$("#chkSelectedDayOnly").addClass("pointerClass");
				$("#divRepeat").addClass("pointerClass");
				$("#divSetDayOff").show();
			}

		}
		// populate the input with the array items separated with a comma
	});
	//add array on each of data select from calender
	//add array on each of data select from calender
	$('.rosterWeek').find(".hoverselectclass").on("click", function () {
		$(this).toggleClass("selectclass");
		// If the id is not already in the array, add it. If it is, remove it  
		classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);

		if (classgrt.join(",") === "") {
			$(".filterhideshow").addClass("d-none");
		}
		else {
			$(".filterhideshow").removeClass("d-none");

			if (classgrt.length >= 1) {
				$("#divStartDate").addClass("d-none");
				$("#divEndDate").addClass("d-none");
				$("#chkDayOnly").hide();
				$("#chkSelectedDayOnly").removeClass("pointerClass");
				$("#divRepeat").removeClass("pointerClass");
				$("#divSetDayOff").hide();
			}
			else {

				$("#divStartDate").removeClass("d-none");
				$("#divEndDate").removeClass("d-none");
				$("#chkDayOnly").show();
				$("#chkSelectedDayOnly").addClass("pointerClass");
				$("#divRepeat").addClass("pointerClass");
				$("#divSetDayOff").show();
			}

		}
		// populate the input with the array items separated with a comma
	});
	//add array on each of data select from calender

	/*on checkbox select change*/
	$('.postWeek').find(`input[name="selectallcheckbox"]`).on("change", function () {
		if ($(this).is(":checked")) {
			$(this).parent().parent().parent().children("td").children().not("label").each(function(i,v){
				console.log(v);
				let date = $(v).attr('data-date');
				if(moment(date).isAfter(moment())){
					$(v).addClass("selectclass");
				}
			});
			$(this).parent().parent().parent().children("td").children().not("label").removeClass("hoverselectclass");
			// $(this).parent().parent().parent().children("td").children().not("label").addClass("selectclass");
			// $(this).parent().parent().parent().children("td").children().not("label").addClass("disableselectclass");
			$(".Postfilterhideshow").removeClass("d-none");

		}
		else {
			$(this).parent().parent().parent().children("td").children().not("label").addClass("hoverselectclass");
			$(this).closest('tr').children("td").children().not("label").each(function(i,v){
				classgrt.splice(classgrt.indexOf( $(v).attr('data-selectid')), 1)
			})
			$(this).parent().parent().parent().children("td").children().not("label").removeClass("selectclass");
			// $(this).parent().parent().parent().children("td").children().not("label").removeClass("disableselectclass");
			$(".Postfilterhideshow").addClass("d-none");
		}
		$(".selectclass").map(function () {
			if (($(this).attr("data-selectid") != undefined) && ($(this).attr("data-selectid") != null) && ($(this).attr("data-selectid") != "")) {
				if (isMonth == 1) {
					// classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
					classgrt.push($(this).attr("data-selectid"));
				}
				else {
					// classgrtw.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
					classgrtw.push($(this).attr("data-selectid"));
				}
			}
		});
	});
	/*on checkbox select change*/
	/*on checkbox select change*/
	$('.postMonth').find(`input[name="selectallcheckbox"]`).on("change", function () {
		if ($(this).is(":checked")) {
			$(this).parent().parent().parent().children("td").children().not("label").each(function(i,v){
				let date = $(v).attr('data-date');
				if(moment(date).isAfter(moment())){
					$(v).addClass("selectclass");
				}
			});
			$(this).parent().parent().parent().children("td").children().not("label").removeClass("hoverselectclass");
			// $(this).parent().parent().parent().children("td").children().not("label").addClass("selectclass");
			$(".Postfilterhideshow").removeClass("d-none");
		}
		else {
			$(this).parent().parent().parent().children("td").children().not("label").addClass("hoverselectclass");
			$(this).closest('tr').children("td").children().not("label").each(function(i,v){
				classgrt.splice(classgrt.indexOf( $(v).attr('data-selectid')), 1)
			})
			$(this).parent().parent().parent().children("td").children().not("label").removeClass("selectclass");
			$(".Postfilterhideshow").addClass("d-none");
		}
		$(".selectclass").map(function () {
			console.log(($(this).attr("data-selectid")));
			if (($(this).attr("data-selectid") != undefined) && ($(this).attr("data-selectid") != null) && ($(this).attr("data-selectid") != "")) {
				if (isMonth == 1) {
					// classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
					classgrt.push($(this).attr("data-selectid"));
				}
				else {
					// classgrtw.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
					classgrtw.push($(this).attr("data-selectid"));
				}
			}
		});

	});
	/*on checkbox select change*/
	//on checkbox select change
	$('.rosterWeek').find(`input[name="selectallcheckbox"]`).on("change", function () {
		console.log($(this));
		if ($(this).is(":checked")) {

			$(this).closest('tr').children("td").children().not("label").each(function(i,v){
				let [employee, date] = $(v).attr('data-selectid').split('|');
				if(moment(date).isAfter(moment())){
					$(v).addClass("selectclass");
				}
			});
			$(".filterhideshow").removeClass("d-none");

		}
		else {
			$(this).closest('tr').children("td").children().not("label").each(function(i,v){
				classgrt.splice(classgrt.indexOf( $(v).attr('data-selectid')), 1)
			})
			$(this).closest('tr').children("td").children().not("label").removeClass("selectclass");
			$(".filterhideshow").addClass("d-none");
		}
		$(".selectclass").map(function () {
			if (($(this).attr("data-selectid") != undefined) && ($(this).attr("data-selectid") != null) && ($(this).attr("data-selectid") != "")) {
				if (isMonth == 1) {
					// classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
					classgrt.push($(this).attr("data-selectid"));
				}
				else {
					// classgrtw.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
					classgrtw.push($(this).attr("data-selectid"));
				}
			}
		});
	});
	//on checkbox select change
	//on checkbox select change
	$('.rosterMonth').find(`input[name="selectallcheckbox"]`).on("change", function () {
		if ($(this).is(":checked")) {
			$(this).closest('tr').children("td").children().not("label").each(function(i,v){
				let [employee, date] = $(v).attr('data-selectid').split('|');
				if(moment(date).isAfter(moment())){
					$(v).addClass("selectclass");
				}
			})
			$(".filterhideshow").removeClass("d-none");
		}
		else {
			$(this).closest('tr').children("td").children().not("label").each(function(i,v){
				classgrt.splice(classgrt.indexOf( $(v).attr('data-selectid')), 1)
			})
			$(this).closest('tr').children("td").children().not("label").removeClass("selectclass");
			$(".filterhideshow").addClass("d-none");
		}
		console.log($(".selectclass"));
		$(".selectclass").map(function () {
			console.log($(this).attr("data-selectid"));
			if (($(this).attr("data-selectid") != undefined) && ($(this).attr("data-selectid") != null) && ($(this).attr("data-selectid") != "")) {
				if (isMonth == 1) {
					classgrt.push($(this).attr("data-selectid"));
					// classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
				}
				else {
					classgrtw.push($(this).attr("data-selectid"));
					// classgrtw.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
				}
			}
		});
	});
	//on checkbox select change
	//on checkbox select change
	$("input[name='selectallcheckboxes']").on("change", function () {
		
		if ($(this).is(":checked")) {
			
			$(this).parent().parent().parent().children('td').children().not('label').removeClass("posthoverselectclass");
			$(this).parent().parent().parent().children('td').children().not('label').addClass("selectclass");
			$(this).parent().parent().parent().children('td').children().not('label').addClass("disableselectclass");
			$('.Postfilterhideshow').removeClass('d-none');
			
		}
		else {
			$(this).parent().parent().parent().children('td').children().not('label').addClass("posthoverselectclass");
			$(this).parent().parent().parent().children('td').children().not('label').removeClass("selectclass");
			$(this).parent().parent().parent().children('td').children().not('label').removeClass("disableselectclass");
			$('.Postfilterhideshow').addClass('d-none');
		}          
		$('.selectclass').map(function () {
			console.log(classgrt.indexOf($(this).attr('data-selectid')));
			classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);

			// if (($(this).attr('data-selectid') != undefined) && ($(this).attr('data-selectid') != null) && ($(this).attr('data-selectid') != '')) {
			// 	if (isMonth == 1) {
			// 		// classgrt.push($(this).attr('data-selectid'));
			// 		classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
			// 	}
			// 	else {
			// 		// classgrtw.push($(this).attr('data-selectid'));
			// 		classgrtw.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrtw.push(this.getAttribute("data-selectid")) : classgrtw.splice(classgrtw.indexOf(this.getAttribute("data-selectid")), 1);
			// 	}                
			// }
		});            
		if ($(this).parent().parent().parent().children('td').children().hasClass('redboxcolor')) {
			$('#selRetrive').show();
			$('.selPost').hide();
		}
		else {
			$('#selRetrive').hide();
			$('.selPost').show();
		}
			
	});
	//on checkbox select change

}


//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////

function get_roster_data(page){
	classgrt = [];
	classgrtw = [];
	let {start_date, end_date} = page;
	let {project, site, shift, department, post_type} = page.filters;
	console.log(start_date, end_date, project, site, shift, department, post_type);
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_roster_view',{start_date, end_date, project, site, shift, department, post_type})
	.then(res => {
		// console.log(res);
		let {post_types_data, employees_data}= res;
		$('.rosterMonth').find('#calenderviewtable tbody').empty();
		for(post_type_name in post_types_data){
			let pt_row = `
			<tr class="colorclass scheduledStaff" data-name="${post_type_name}">
				<td class="clickablerow">
					<div class="d-flex">
						<div class="font16 paddingdiv cursorpointer orangecolor">
							<i class="fa fa-plus" aria-hidden="true"></i>
						</div>
						<div class="font16 paddingdiv borderleft cursorpointer">
							${post_type_name}
						</div>
					</div>
				</td>
			</tr>
			`;
			$('.rosterMonth').find('#calenderviewtable tbody').append(pt_row);
			let {start_date, end_date} = page;
			start_date = moment(start_date);
			end_date = moment(end_date);	
			let i =0;
			for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
				let {date, post_type, count} = post_types_data[post_type_name][i];	
				let pt_count = `
				<td>
					<div class="text-center" data-selectid="${post_type+"|"+date}">${count}</div>
				</td>`;
				$('.rosterMonth').find(`#calenderviewtable tbody tr[data-name="${post_type}"]`).append(pt_count);
				i++;
			}
			$('.rosterMonth').find(`#calenderviewtable tbody tr[data-name="${post_types_data[post_type_name][i-1]['post_type']}"]`).append(`<td></td>`);
		}
		let emp_row_wrapper = `
		<tr class="collapse tableshowclass show">
			<td colspan="33" class="p-0">
				<table id="rowchildtable" class="table subtable mb-0 text-center" style="width:100%">
					<tbody>
					</tbody>
				</table>
			</td>
		</tr>`;
		$('.rosterMonth').find('#calenderviewtable tbody').append(emp_row_wrapper);
		for(employee_key in employees_data){
			let {employee_name, employee, date} = employees_data[employee_key];
			let emp_row = `
			<tr data-name="${employee_key}">
				<td>
					<label class="checkboxcontainer simplecheckbox">
						<span class="lightgrey font16 customfontweight fontw400 postname">${employee_key}</span>
						<input type="checkbox" name="selectallcheckbox" class="selectallcheckbox">
						<span class="checkmark"></span>
					</label>
				</td>
			</tr>
			`;
			$('.rosterMonth').find('#rowchildtable tbody').append(emp_row);

			let {start_date, end_date} = page;
			start_date = moment(start_date);
			end_date = moment(end_date);				
			let i=0; 
			let j=0;
			for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
				let sch = ``;
				let classmap = {
					'Working': 'bluebox',
					'Day Off': 'greyboxcolor',
					'Sick Leave': 'purplebox',
					'Emergency Leave': 'purplebox',
					'Annual Leave': 'purplebox'
				}
				let leavemap = {
					'Sick Leave': 'SL',
					'Annual Leave': 'AL',
					'Emergency Leave': 'EL'
				}
				let {employee, employee_name, date, post_type, post_abbrv, employee_availability, shift} = employees_data[employee_key][i];
				// console.log(employee, employee_name, date, post_type, post_abbrv, employee_availability, shift);
				
				if(post_abbrv){
					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee+"|"+date+"|"+post_type+"|"+shift+"|"+employee_availability}">${post_abbrv}</div>
					</td>`;	
				} else if(employee_availability && !post_abbrv){
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee+"|"+date+"|"+employee_availability}">${leavemap[employee_availability]}</div>
					</td>`;	
				} else {
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox borderbox d-flex justify-content-center align-items-center so"
							data-selectid="${employee+"|"+date}"></div>
					</td>`;
				}
				i++;
				$('.rosterMonth').find(`#rowchildtable tbody tr[data-name="${employee_name}"]`).append(sch);
			}
			console.log(j, employees_data[employee_key], i);
			$('.rosterMonth').find(`#rowchildtable tbody tr[data-name="${employees_data[employee_key][i-1]['employee_name']}"]`).append(`<td>${j}</td>`);
			// $('.rosterMonth').find(`#rowchildtable tbody tr[data-name="${employee_name}"]`).append(`<td></td>`);
			// let employee_modal = `
			// <tr>
			// 	<td> 
			// 		<a href="#" class="lightbluecolor cursorpointer addpostmodalclick">
			// 			<span class="fa fa-plus" aria-hidden="true"></span>
			// 			<span class="pl-2"> Add Employees</span>
			// 		</a>
			// 	</td>
			// </tr>`;
			// $('.rosterMonth').find(`#rowchildtable tbody"]`).append(employee_modal);
		}
		bind_events(page);
	});
}

function get_roster_week_data(page){
	classgrt = [];
	classgrtw = [];
	let {start_date, end_date} = page;
	let {project, site, shift, department, post_type} = page.filters;
	console.log(start_date, end_date, project, site, shift, department, post_type);
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_roster_view',{start_date, end_date, project, site, shift, department, post_type})
	.then(res => {
		// console.log(res);
		let {post_types_data, employees_data}= res;
		$('.rosterWeek').find('#calenderweekviewtable tbody').empty();
		for(post_type_name in post_types_data){
			let pt_row = `
			<tr class="colorclass scheduledStaff" data-name="${post_type_name}">
				<td class="clickablerow">
					<div class="d-flex">
						<div class="font16 paddingdiv cursorpointer orangecolor">
							<i class="fa fa-plus" aria-hidden="true"></i>
						</div>
						<div class="font16 paddingdiv borderleft cursorpointer">
							${post_type_name}
						</div>
					</div>
				</td>
			</tr>
			`;
			$('.rosterWeek').find('#calenderweekviewtable tbody').append(pt_row);
			let {start_date, end_date} = page;
			start_date = moment(start_date);
			end_date = moment(end_date);	
			let i =0;
			for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
				let {date, post_type, count} = post_types_data[post_type_name][i];	
				let pt_count = `
				<td>
					<div class="text-center" data-selectid="${post_type+"|"+date}">${count}</div>
				</td>`;
				$('.rosterWeek').find(`#calenderweekviewtable tbody tr[data-name="${post_type}"]`).append(pt_count);
				i++;
			}
			$('.rosterWeek').find(`#calenderweekviewtable tbody tr[data-name="${post_types_data[post_type_name][i-1]['post_type']}"]`).append(`<td></td>`);
		}
		let emp_row_wrapper = `
		<tr class="collapse tableshowclass show">
			<td colspan="33" class="p-0">
				<table id="rowchildtable" class="table subcalenderweektable mb-0 text-center" style="width:100%">
					<tbody>
					</tbody>
				</table>
			</td>
		</tr>`;
		$('.rosterWeek').find('#calenderweekviewtable tbody').append(emp_row_wrapper);
		for(employee_key in employees_data){
			let {employee_name, employee, date} = employees_data[employee_key];
			let emp_row = `
			<tr data-name="${employee_key}">
				<td>
					<label class="checkboxcontainer simplecheckbox">
						<span class="lightgrey font16 customfontweight fontw400 postname">${employee_key}</span>
						<input type="checkbox" name="selectallcheckbox" class="selectallcheckbox">
						<span class="checkmark"></span>
					</label>
				</td>
			</tr>
			`;
			$('.rosterWeek').find('#rowchildtable tbody').append(emp_row);

			let {start_date, end_date} = page;
			start_date = moment(start_date);
			end_date = moment(end_date);				
			let i=0; 
			let j=0;
			for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
				let sch = ``;
				let classmap = {
					'Working': 'bluebox',
					'Day Off': 'greyboxcolor',
					'Sick Leave': 'purplebox',
					'Emergency Leave': 'purplebox',
					'Annual Leave': 'purplebox'
				}
				let leavemap = {
					'Sick Leave': 'SL',
					'Annual Leave': 'AL',
					'Emergency Leave': 'EL'
				}
				let {employee, employee_name, date, post_type, post_abbrv, employee_availability, shift} = employees_data[employee_key][i];
				console.log(date, moment().isBefore(moment(date)));
				
				if(employee_availability && post_abbrv){
					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee+"|"+date+"|"+post_type+"|"+shift+"|"+employee_availability}">${post_abbrv}</div>
					</td>`;	
				}else if(employee_availability && !post_abbrv){
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee+"|"+date+"|"+employee_availability}">${leavemap[employee_availability]}</div>
					</td>`;	
				} else {
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox borderbox d-flex justify-content-center align-items-center so"
							data-selectid="${employee+"|"+date}"></div>
					</td>`;
				}
				i++;
				$('.rosterWeek').find(`#rowchildtable tbody tr[data-name="${employee_name}"]`).append(sch);
			}
			$('.rosterWeek').find(`#rowchildtable tbody tr[data-name="${employees_data[employee_key][i-1]['employee_name']}"]`).append(`<td>${j}</td>`);
			// $('.rosterMonth').find(`#rowchildtable tbody tr[data-name="${employee_name}"]`).append(`<td></td>`);
			// let employee_modal = `
			// <tr>
			// 	<td> 
			// 		<a href="#" class="lightbluecolor cursorpointer addpostmodalclick">
			// 			<span class="fa fa-plus" aria-hidden="true"></span>
			// 			<span class="pl-2"> Add Employees</span>
			// 		</a>
			// 	</td>
			// </tr>`;
			// $('.rosterMonth').find(`#rowchildtable tbody"]`).append(employee_modal);
		}
		bind_events(page);
	});	
}

function get_post_data(page){
	classgrt = [];
	classgrtw = [];
	let {start_date, end_date} = page;
	let {project, site, shift, post_type} = page.filters;
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_post_view',{start_date, end_date, project, site, shift, post_type})
	.then(res =>{ 
		$('.postMonth').find('#calenderviewtable tbody').empty();
		for(post_name in res){
			let row = `
			<tr class="colorclass" data-name="${post_name}">
				<td>
					<label class="checkboxcontainer simplecheckbox mx-4">
						<span
							class="lightgrey font16 customfontweight fontw400 postname">
							${post_name}
						</span>
						<span class="tooltiptext">${post_name}</span>
						<input type="checkbox" name="selectallcheckbox"
							class="selectallcheckbox">
						<span class="checkmark"></span>
					</label>
				</td>
			</tr>`;
			$('.postMonth').find('#calenderviewtable tbody').append(row);
			let {start_date, end_date} = page;
			start_date = moment(start_date);
			end_date = moment(end_date);				
			let i =0;
			for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
				let schedule = ``;
				let classmap = {
					'Planned': 'bluebox',
					'Post Off': 'greyboxcolor',
					'Suspended': 'yellowboxcolor',
					'Cancelled': 'redboxcolor'
				}
				
				let {project, site, shift, date, post_status, post_type, post, name} = res[post_name][i];
				if(name){
					schedule = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[post_status]} d-flex justify-content-center align-items-center so"
							data-selectid="${post+'|'+date}"
							data-date="${date}"
							data-project="${project}"
							data-site="${site}"
							data-shift="${shift}"
							data-name="${name}"
							data-post="${post}"
							data-post_status="${post_status}"
							data-post-type="${post_type}">
						</div>
					</td>`;
				}
				else{
					schedule = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox darkblackox d-flex justify-content-center align-items-center so"
							data-selectid="${post_name+'|'+start_date.format('YYYY-MM-DD')}"	
							data-date="${start_date.format('YYYY-MM-DD')}"
							data-post="${post_name}"
						</div>
					</td>`;
				}
				i++;
				$('.postMonth').find(`#calenderviewtable tbody tr[data-name="${post_name}"]`).append(schedule);
			}		
			$('.postMonth').find(`#calenderviewtable tbody tr[data-name="${post_name}"]`).append(`<td></td>`);
		}			
		bind_events(page);
	});
}

function get_post_week_data(page){
	classgrt = [];
	classgrtw = [];
	let {start_date, end_date} = page;
	let {project, site, shift, post_type} = page.filters;
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_post_view',{start_date, end_date, project, site, shift, post_type})
	.then(res =>{ 
		$('.postWeek').find('#calenderweekviewtable tbody').empty();

		for(post_name in res){
			let row = `
			<tr class="colorclass" data-name="${post_name}">
				<td>
					<label class="checkboxcontainer simplecheckbox mx-4">
						<span class="lightgrey font16 customfontweight fontw400 postname">
							${post_name}
						</span>
						<span class="tooltiptext">${post_name}</span>

						<input type="checkbox" name="selectallcheckbox" class="selectallcheckbox">
						<span class="checkmark"></span>
					</label>
				</td>
			</tr>`;
			$('.postWeek').find('#calenderweekviewtable tbody').append(row);
			let {start_date, end_date} = page;
			start_date = moment(start_date);
			end_date = moment(end_date);			
			let i = 0;
			for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
				let schedule = ``;
				let classmap = {
					'Planned': 'blueboxcolor',
					'Post Off': 'greyboxcolor',
					'Suspended': 'yellowboxcolor',
					'Cancelled': 'redboxcolor'
				}
				
				let {project, site, shift, date, post_status, post_type, post, name} = res[post_name][i];
				if(name){
					schedule = `
					<td>
						<div class="hoverselectclass tablebox ${classmap[post_status]} d-flex justify-content-center align-items-center so"
							data-selectid="${post+'|'+date}"
							data-date="${date}"
							data-project="${project}"
							data-site="${site}"
							data-shift="${shift}"
							data-name="${name}"
							data-post="${post}"
							data-post_status="${post_status}"
							data-post-type="${post_type}">
						</div>
					</td>`;
				}
				else{
					schedule = `
					<td>
						<div class="hoverselectclass tablebox darkblackox d-flex justify-content-center align-items-center so"
							data-selectid="${post_name+'|'+start_date.format('YYYY-MM-DD')}"	
							data-date="${start_date.format('YYYY-MM-DD')}"
							data-post="${post_name}"
						</div>
					</td>`;
				}
				i++;
				$('.postWeek').find(`#calenderweekviewtable tbody tr[data-name="${post_name}"]`).append(schedule);
			}
			$('.postWeek').find(`#calenderweekviewtable tbody tr[data-name="${post_name}"]`).append(`<td></td>`);		
		}
		bind_events(page);
	});
}

function setup_filters(page){
	frappe.db.get_value("Employee", {"user_id": "k.sharma@armor-services.com"}, ["name"])
	.then(res => {
		let {name} = res.message;
		page.employee_id = name;
		get_projects(page);
		get_sites(page);
		get_shifts(page);
		get_departments(page);
		get_post_types(page);
	})
	.then(r => {
		get_roster_data(page);
	});
}

function get_projects(page){
	let {employee_id} = page;
	frappe.xcall('one_fm.api.mobile.roster.get_assigned_projects',{employee_id})
	.then(res => {
		// console.log(res);
		let parent = $('#rosteringprojectselect');
		res.forEach(element => {
			let {name} = element;
			parent.append(new Option(name, name));
		});
		$(parent).on('select2:select', function (e) {
			page.filters.project = $(this).val();
			let element = get_wrapper_element().slice(1);
			page[element](page);			
		});
	})
}

function get_sites(page){
	let {employee_id, project} = page;
	frappe.xcall('one_fm.api.mobile.roster.get_assigned_sites',{employee_id, project})
	.then(res => {
		// console.log(res);
		let parent = $('#rosteringsiteselect');
		res.forEach(element => {
			let {name} = element;
			parent.append(new Option(name, name));
		});
		$(parent).on('select2:select', function (e) {
			page.filters.site = $(this).val();
			let element = get_wrapper_element().slice(1);
			page[element](page);
		});
	})
}

function get_shifts(page){
	let {employee_id, site} = page;
	frappe.xcall('one_fm.api.mobile.roster.get_assigned_shifts',{employee_id, site})
	.then(res => {
		// console.log(res);
		let parent = $('#rosteringshiftselect');
		res.forEach(element => {
			let {name} = element;
			parent.append(new Option(name, name));
		});
		$(parent).on('select2:select', function (e) {
			page.filters.shift = $(this).val();
			let element = get_wrapper_element().slice(1);
			page[element](page);
		});
	})
}

function get_post_types(page){
	let {employee_id, shift} = page;
	frappe.xcall('one_fm.api.mobile.roster.get_post_types', {employee_id, shift})
	.then(res => {
		// console.log(res);
		let parent = $('#rosteringpostselect');
		res.forEach(element => {
			let {name} = element;
			parent.append(new Option(name, name));
		});
		$(parent).on('select2:select', function (e) {
			page.filters.post_type = $(this).val();
			let element = get_wrapper_element().slice(1);
			page[element](page);
		});

	})
}

function get_departments(page){
	frappe.xcall('one_fm.api.mobile.roster.get_departments')
	.then(res => {
		// console.log(res);
		let parent = $('#rosteringdepartmentselect');
		res.forEach(element => {
			let {name} = element;
			parent.append(new Option(name, name));
		});
		$(parent).on('select2:select', function (e) {
			page.filters.department = $(this).val();
			let element = get_wrapper_element().slice(1);
			page[element](page);
		});

	})
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////

function highlightDays(date) {
	date.setHours(0, 0, 0, 0);
	var tooltip_text = "New event on " + date;

	if (date == today) {
		return [true, "highlight", tooltip_text];
	}
	return [true, ""];
}
function dayoffmodalclick() {
	//  if ($("#dayoffformmodal").valid()) {

	if (isMonth == 1) {

		if (classgrt.length > 0) {
			$.each(classgrt, function (index, value) {
				$(".selectclass").each(function () {
					// Test if the div element is empty

					if ($(this).attr("data-selectid") == classgrt[index]) {
						$(this).removeClass("selectclass");
						//tablebox greybox d-flex justify-content-center align-items-center SG
						$(this).addClass("tablebox");

						$(this).addClass("d-flex");
						$(this).addClass("justify-content-center");

						$(this).addClass("greybox");

						//remove other classes
						$(this).removeClass("borderbox");
						$(this).removeClass("bluebox");
						$(this).removeClass("purplebox");

						$(this).html("DO");

					}
				});
			});
			classgrt = [];
		}
	}
	else {
		if (classgrtw.length > 0) {
			$.each(classgrtw, function (index, value) {
				$(".selectclass").each(function () {
					// Test if the div element is empty

					if ($(this).attr("data-selectid") == classgrtw[index]) {
						$(this).removeClass("selectclass");
						//tablebox greybox d-flex justify-content-center align-items-center SG
						$(this).addClass("tablebox");

						$(this).addClass("d-flex");
						$(this).addClass("justify-content-center");

						$(this).addClass("greybox");

						//remove other classes
						$(this).removeClass("borderbox");
						$(this).removeClass("bluebox");
						$(this).removeClass("purplebox");

						$(this).html("DO");

					}
				});
			});
			classgrtw = [];
		}
	}
	$("#dayoffmodal").modal("toggle");
	$(`input[name="selectallcheckbox"]`).each(function () {
		$(this).prop("checked", false);
	});

	$(".filterhideshow").addClass("d-none");
	notificationmsg("Success!!", "");

	// }
}
function leaveabsentmodalclick() {
	if ($("#leaveabsentformmodal").valid()) {
		notificationmsg("Success!!", "");
		var leaveType = $("#txtleaveinput option:selected").text();
		if (isMonth == 1) {
			$.each(classgrt, function (index, value) {
				$(".selectclass").each(function () {
					// Test if the div element is empty

					if ($(this).attr("data-selectid") == classgrt[index]) {
						$(this).removeClass("selectclass");
						//tablebox greybox d-flex justify-content-center align-items-center SG
						$(this).addClass("tablebox");

						$(this).addClass("d-flex");
						$(this).addClass("justify-content-center");

						$(this).addClass("purplebox");

						//remove other classes
						$(this).removeClass("borderbox");
						$(this).removeClass("bluebox");
						$(this).removeClass("greybox");

						$(this).html(leaveType);

					}
				});
			});
			classgrt = [];
		}
		else {
			$.each(classgrtw, function (index, value) {
				$(".selectclass").each(function () {
					// Test if the div element is empty

					if ($(this).attr("data-selectid") == classgrt[index]) {
						$(this).removeClass("selectclass");
						//tablebox greybox d-flex justify-content-center align-items-center SG
						$(this).addClass("tablebox");

						$(this).addClass("d-flex");
						$(this).addClass("justify-content-center");

						$(this).addClass("purplebox");

						//remove other classes
						$(this).removeClass("borderbox");
						$(this).removeClass("bluebox");
						$(this).removeClass("greybox");

						$(this).html(leaveType);

					}
				});
			});
			classgrtw = [];
		}
		$("#leaveabsentmodal").modal("hide");


	}
}
function assignchangemodalclick() {
	if ($("#assignformmodal").valid()) {

		//child ni table valus update    

		if (isMonth == 1) {
			$.each(classgrt, function (index, value) {

				$(".selectclass").each(function () {
					// Test if the div element is empty

					if ($(this).attr("data-selectid") == classgrt[index]) {
						$(this).removeClass("selectclass");
						//tablebox greybox d-flex justify-content-center align-items-center SG
						$(this).addClass("tablebox");

						$(this).addClass("d-flex");
						$(this).addClass("justify-content-center");
						var postType = $("#txtposttype").val();

						var hasGreyClass = $(this).hasClass("greybox");
						var hasBlueClass = $(this).hasClass("bluebox");
						// console.log(hasGreyClass + " " + hasBlueClass);
						if (postType != 0 && hasBlueClass == false) {
							$(this).addClass("bluebox");
							$(this).addClass("align-items-center SG");
							$(this).html("SG");
							//remove other classes
							$(this).removeClass("borderbox");
							$(this).removeClass("greybox");
							$(this).removeClass("purplebox");
						}
						else if (postType == 0 && hasGreyClass == false) {
							$(this).addClass("bluebox");
							$(this).addClass("align-items-center so");
							$(this).html("SO");

							//remove other classes
							$(this).removeClass("greybox");
							$(this).removeClass("borderbox");
							$(this).removeClass("purplebox");
						}
					}
				});
			});
			classgrt = [];
		}
		else {
			$.each(classgrtw, function (index, value) {
				$(".selectclass").each(function () {
					// Test if the div element is empty

					if ($(this).attr("data-selectid") == classgrtw[index]) {
						$(this).removeClass("selectclass");
						//tablebox greybox d-flex justify-content-center align-items-center SG
						$(this).addClass("tablebox");

						$(this).addClass("d-flex");
						$(this).addClass("justify-content-center");
						var postType = $("#txtposttype").val();

						var hasGreyClass = $(this).hasClass("greybox");
						var hasBlueClass = $(this).hasClass("bluebox");

						if (postType != 0 && hasBlueClass == false) {
							$(this).addClass("bluebox");
							$(this).addClass("align-items-center SG");
							$(this).html("SG");
							//remove other classes
							$(this).removeClass("borderbox");
							$(this).removeClass("greybox");
							$(this).removeClass("purplebox");
						}
						else if (postType == 0 && hasGreyClass == false) {
							$(this).addClass("bluebox");
							$(this).addClass("align-items-center so");
							$(this).html("SO");

							//remove other classes
							$(this).removeClass("greybox");
							$(this).removeClass("borderbox");
							$(this).removeClass("purplebox");
						}
					}
				});
			});
			classgrtw = [];
		}
		$(`input[name="selectallcheckbox"]`).each(function () {
			$(this).prop("checked", false);
		});

		$(`input[name="neverselectallcheckbox"]`).prop("checked", false);
		$(".filterhideshow").addClass("d-none");
		notificationmsg("Success!!", "");
		$(".modal").modal("hide");
	}
}
function unassignchangemodalclick() {
	if ($("#unassignformmodal").valid()) {

		if (isMonth == 1) {
			$.each(classgrt, function (index, value) {
				$(".selectclass").each(function () {
					// Test if the div element is empty

					if ($(this).attr("data-selectid") == classgrt[index]) {
						$(this).removeClass("selectclass");
						//tablebox greybox d-flex justify-content-center align-items-center SG
						$(this).addClass("tablebox");

						$(this).addClass("d-flex");
						$(this).addClass("justify-content-center");

						$(this).addClass("borderbox");

						//remove other classes
						$(this).removeClass("greybox");
						$(this).removeClass("bluebox");
						$(this).removeClass("purplebox");

						$(this).html("");

					}
				});
			});
			classgrt = [];
		}
		else {
			$.each(classgrtw, function (index, value) {
				$(".selectclass").each(function () {
					// Test if the div element is empty

					if ($(this).attr("data-selectid") == classgrtw[index]) {
						$(this).removeClass("selectclass");
						//tablebox greybox d-flex justify-content-center align-items-center SG
						$(this).addClass("tablebox");

						$(this).addClass("d-flex");
						$(this).addClass("justify-content-center");

						$(this).addClass("borderbox");

						//remove other classes
						$(this).removeClass("greybox");
						$(this).removeClass("bluebox");
						$(this).removeClass("purplebox");

						$(this).html("");

					}
				});
			});
			classgrtw = [];
		}
		$("#unassignchangemodal").modal("hide");
		notificationmsg("Success!!", "");

	}
}
// function addpostmodalclick() {
// 	if ($("#addpostformmodal").valid()) {
// 		notificationmsg("Success!!", "");
// 		var postType = $("#postcalendertype option:selected").val();

// 		if (isMonth == 1) {

// 			if (classgrt.length > 0) {
// 				$.each(classgrt, function (index, value) {
// 					$(".selectclass").each(function () {
// 						// Test if the div element is empty

// 						if ($(this).attr("data-selectid") == classgrt[index]) {
// 							$(this).removeClass("selectclass");
// 							//tablebox greybox d-flex justify-content-center align-items-center SG
// 							$(this).addClass("tablebox");

// 							$(this).addClass("d-flex");
// 							$(this).addClass("justify-content-center");
// 							//this code is shifted to indvidual postype as there is date selection, 
// 							//so dates lying in them can only apply the class and remove other class maining 
// 							//remove other classes
// 							//$(this).removeClass("greybox");
// 							//$(this).removeClass("bluebox");
// 							//$(this).removeClass("yellowboxcolor");
// 							//$(this).removeClass("redboxcolor");
// 							if (postType == "0") {
// 								$(this).removeClass("greybox");
// 								$(this).removeClass("bluebox");
// 								$(this).removeClass("yellowboxcolor");
// 								$(this).removeClass("redboxcolor");
// 								$(this).addClass("greybox");

// 							}
// 							else if (postType == "1") {
// 								$(this).removeClass("greybox");
// 								$(this).removeClass("bluebox");
// 								$(this).removeClass("yellowboxcolor");
// 								$(this).removeClass("redboxcolor");
// 								$(this).addClass("yellowboxcolor");
// 							}
// 							else if (postType == "2") {


// 								var frmcancelDate = $("#txtpostfromcanceldate").val();

// 								var datepart = frmcancelDate.split("/");
// 								var startdate = datepart[0];
// 								var date = new Date();
// 								var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
// 								var lastdate = lastDay.getDate();
// 								var dataselectid = $(this).attr("data-selectid")
// 								var dateselected = data-selectid.match(/\d+/);

// 								if ((parseInt(dateselected[0]) >= parseInt(startdate)) && (dateselected <= lastdate)) {
// 									$(this).removeClass("greybox");
// 									$(this).removeClass("bluebox");
// 									$(this).removeClass("yellowboxcolor");
// 									$(this).removeClass("redboxcolor");
// 									$(this).addClass("redboxcolor");
// 								}
// 							}
// 							else if (postType == "3") {
// 								var frmretriveDate = $("#txtpostfromcanceldate").val();

// 								var datepart = frmretriveDate.split("/");
// 								var startdate = datepart[0];
// 								var date = new Date();
// 								var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
// 								var lastdate = lastDay.getDate();
// 								var dataselectid = $(this).attr("data-selectid")
// 								var dateselected = dataselectid.match(/\d+/);

// 								if ((parseInt(dateselected[0]) >= parseInt(startdate)) && (dateselected <= lastdate)) {
// 									$(this).removeClass("greybox");
// 									$(this).removeClass("bluebox");
// 									$(this).removeClass("yellowboxcolor");
// 									$(this).removeClass("redboxcolor");
// 									$(this).addClass("bluebox");
// 								}

// 							}

// 							//  $(this).html("DO");

// 						}
// 					});
// 				});
// 				classgrt = [];
// 			}
// 		}
// 		else {
// 			if (classgrtw.length > 0) {
// 				$.each(classgrtw, function (index, value) {
// 					$(".selectclass").each(function () {
// 						// Test if the div element is empty

// 						if ($(this).attr("data-selectid") == classgrtw[index]) {
// 							$(this).removeClass("selectclass");
// 							//tablebox greybox d-flex justify-content-center align-items-center SG
// 							$(this).addClass("tablebox");

// 							$(this).addClass("d-flex");
// 							$(this).addClass("justify-content-center");
// 							//remove other classes
// 							//$(this).removeClass("greybox");
// 							//$(this).removeClass("bluebox");
// 							//$(this).removeClass("yellowboxcolor");
// 							//$(this).removeClass("redboxcolor");
// 							if (postType == "0") {
// 								$(this).removeClass("greybox");
// 								$(this).removeClass("bluebox");
// 								$(this).removeClass("yellowboxcolor");
// 								$(this).removeClass("redboxcolor");
// 								$(this).addClass("greybox");

// 							}
// 							else if (postType == "1") {

// 								$(this).removeClass("greybox");
// 								$(this).removeClass("bluebox");
// 								$(this).removeClass("yellowboxcolor");
// 								$(this).removeClass("redboxcolor");
// 								$(this).addClass("yellowboxcolor");
// 							}
// 							else if (postType == "2") {
// 								//var frmcancelDate = $("#txtpostfromcanceldate").val();

// 								//var datepart = frmcancelDate.split("/");
// 								//var startdate = datepart[0];
// 								//var date = new Date();
// 								//var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
// 								//var lastdate = lastDay.getDate();
// 								//var data-selectid = $(this).attr("data-selectid")
// 								//var dateselected = data-selectid.match(/\d+/);

// 								//if ((parseInt(dateselected[0]) >= parseInt(startdate)) && (dateselected <= lastdate)) {
// 								$(this).removeClass("greybox");
// 								$(this).removeClass("bluebox");
// 								$(this).removeClass("yellowboxcolor");
// 								$(this).removeClass("redboxcolor");
// 								$(this).addClass("redboxcolor");
// 								// } 
// 							}
// 							else if (postType == "3") {

// 								//var frmretriveDate = $("#txtpostfromcanceldate").val();

// 								//var datepart = frmretriveDate.split("/");
// 								//var startdate = datepart[0];
// 								//var date = new Date();
// 								//var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
// 								//var lastdate = lastDay.getDate();
// 								//var data-selectid = $(this).attr("data-selectid")
// 								//var dateselected = data-selectid.match(/\d+/);

// 								//if ((parseInt(dateselected[0]) >= parseInt(startdate)) && (dateselected <= lastdate)) {
// 								$(this).removeClass("greybox");
// 								$(this).removeClass("bluebox");
// 								$(this).removeClass("yellowboxcolor");
// 								$(this).removeClass("redboxcolor");
// 								$(this).addClass("bluebox");
// 								// }
// 							}

// 							//remove other classes
// 							//$(this).removeClass("borderbox");
// 							//$(this).removeClass("bluebox");
// 							//$(this).removeClass("purplebox");

// 							// $(this).html("DO");

// 						}
// 					});
// 				});
// 				classgrtw = [];
// 			}
// 		}
// 		$(`input[name="selectallcheckbox"]`).each(function () {
// 			//debugger;
// 			//if (postType == "2") { $(this).addClass("InActivePost"); }
// 			$(this).prop("checked", false);
// 		});
// 		ShowProperPost();
// 		$(".Postfilterhideshow").addClass("d-none");
// 		$(".modal").modal("hide");
// 	}
// }
function addpostdeletemodalclick() {
	notificationmsg("Success!!", "Delete successfully.");
	$(".modal").modal("hide");

}
function notificationmsg(title, message) {

	var titletxt = title;
	var messagetxt = message;
	$.notify({
		// options
		title: "<strong>" + titletxt + "</strong>",
		message: messagetxt,
		icon: "far fa-check-circle notifycolor",
		target: "_blank"
	},
		{
			element: "body",
			type: "success",
			showProgressbar: false,
			placement: {
				from: "top",
				align: "right"
			},
			offset: 20,
			spacing: 10,
			z_index: 1080,
			delay: 3300,
			timer: 500,
			url_target: "_blank",
			mouse_over: null,
			animate: {
				enter: "animated fadeInDown",
				exit: "animated fadeOutRight"
			},
			onShow: null,
			onShown: null,
			onClose: null,
			onClosed: null,
			icon_type: "class",
		});
}

function ShowProperPost() {

	if ($("#chkpostActivePost").is(":checked")) {
		$("#calenderviewtable tbody tr td").not(".redboxcolor").parent().removeClass("d-none");

		//$("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().addClass("InActivePost");
		//$("#calenderviewtable tbody tr td").not(".redboxcolor").parent().addClass("ActivePost");

	}
	else {
		//$("#calenderviewtable tbody tr td").not(".redboxcolor").parent().removeClass("InActivePost");
		//$("#calenderviewtable tbody tr td").not(".redboxcolor").parent().addClass("ActivePost");
		//$("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().removeClass("InActivePost");

		$("#calenderviewtable tbody tr td").not(".redboxcolor").parent().addClass("d-none");
	}



	if ($("#chkpostCancelPost").is(":checked")) {
		//   $("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().removeClass("InActivePost");
		$("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().removeClass("d-none");


	}
	else if ($("#chkpostCancelPost").is(":checked") == false) {
		//$("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().addClass("InActivePost");
		$("#calenderviewtable tbody tr td").find(".redboxcolor").parent().parent().addClass("d-none");

	}
	//chkpostCancelPost

}	

//==========================================================================
//==========================================================================
//==========================================================================
//==========================================================================
//==========================================================================
//==========================================================================
//==========================================================================


 //on next month title display on arrow click
 function incrementMonth(page) {
	if(!page){
		page = cur_page.page.page;
	}
	calendarSettings1.date.add(1, "Months");

	let element = get_wrapper_element();
	if(element == '.rosterMonth' || element == '.postMonth'){
		GetHeaders(1);
		displayCalendar(calendarSettings1);
		
		element = element.slice(1);
		page[element](page);			
		
	}else{
		GetWeekHeaders(1);
		displayWeekCalendar(calendarSettings1);
		
		element = element.slice(1);
		page[element](page);			
	}
}
//on next month title display on arrow click

//on previous month title display on arrow click
function decrementMonth(page) {
	if(!page){
		page = cur_page.page.page;
	}
	calendarSettings1.date.subtract(1, "Months");
	let element = get_wrapper_element();
	if(element == '.rosterMonth' || element == '.postMonth'){
		GetHeaders(1);
		displayCalendar(calendarSettings1);
		element = element.slice(1);
		page[element](page);	
	}else{
		GetWeekHeaders(1);
		displayWeekCalendar(calendarSettings1);
		element = element.slice(1);
		page[element](page);	
	}
}
//on previous month title display on arrow click


function displayCalendar(calendarSettings1, page) {
	if(!page){
		page = cur_page.page.page;
	}
	let element = get_wrapper_element();
	const calendar = $(element).find('.calendertitlechange')[0];
	console.log(element, calendar);
	const calendarTitle = calendarSettings1.date.format("MMM");
	const calendaryear = calendarSettings1.date.format("YYYY");
	const daysInMonth = calendarSettings1.date.endOf("Month").date();
	console.log(calendarSettings1.date, calendarSettings1.date.endOf("Month").date());
	page.start_date = calendarSettings1.date.startOf("Month").format('YYYY-MM-DD');
	page.end_date = calendarSettings1.date.endOf("Month").format('YYYY-MM-DD');

	// let start_date = moment()
	// page.start_date = '';
	// page.end_date = 
	// end_date = '';
	calendar.innerHTML = "";
	calendar.innerHTML = "Month of <span> " + calendarTitle + " </span> 1 - <span>" + daysInMonth + "</span>, " + calendaryear + "";

}


//function for changing roster date
function ChangeRosteringDate(seldate, this1) {
	console.log(seldate, this1);
	var date = calendarSettings1.today.format("DD");
	var month = calendarSettings1.date.format("MM") - 1;
	var year = calendarSettings1.date.format("YYYY");
	var d1 = new Date(year, month, date);
	console.log(d1);
	$(this1).parent().children().removeClass("hightlightedtable")
	$(this1).addClass("hightlightedtable");
	// $("#datepicker").datepicker("update", new Date(year, month, seldate));
	cur_page.page.page.datepicker.set('defaultDate', d1);
}
//function for changing roster date

//Get the visible roster/post view parent
function get_wrapper_element(element){
	if(element) return element;
	let roster_element = $(".rosterMonth").attr("class").split(/\s+/).includes("d-none");
	let roster_week_element = $(".rosterWeek").attr("class").split(/\s+/).includes("d-none");
	let post_element = $(".postMonth").attr("class").split(/\s+/).includes("d-none");
	let post_week_element = $(".postWeek").attr("class").split(/\s+/).includes("d-none");
	// let roster_week_element = $(".rosterWeek").attr("class").split(/\s+/);
	console.log(element, post_week_element);


	if(roster_element && roster_week_element && !post_element && post_week_element){
		element = '.postMonth';
		console.log(element);
		return element;
	}else if(!roster_element && roster_week_element && post_element && post_week_element){
		element = '.rosterMonth';
		console.log(element);
		return element;
	}else if(roster_element && roster_week_element && post_element && !post_week_element){
		element = '.postWeek';
		console.log(element);
		return element;
	}else if(roster_element && !roster_week_element && post_element && post_week_element){
		element = '.rosterWeek';
		console.log(element);
		return element;
	}
}


//function for dynamic set calender header data on right calender
function GetHeaders(IsMonthSet, element) {

	var thHTML = "";
	var thStartHTML = `<th class="">Post Type / Days</th>`;
	var thEndHTML = "<th>Total</th>";
	element = get_wrapper_element(element);
	console.log(element);
	var selectedMonth;
	if (IsMonthSet == 0) {
		var today = new Date();

		var firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
		var lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
		var lastDate = moment(lastDay);
		var getdateres = moment(new Date()).format("DD");

		var dataHTML = "";
		for (var i = 1; i <= lastDate.format("DD"); i++) {

			var calDate = moment(new Date(today.getFullYear(), today.getMonth(), i));
			var todayDay = calDate.format("ddd");
			var todayDaydate = calDate.format("DD");
			var th = "";// "<th id="data-day_" + i + "" onclick="ChangeRosteringDate(" + i + ",this)">" + calDate.format("ddd") + " " + calDate.format("DD") + "</th>";
			console.log(todayDaydate === getdateres);
			if (todayDay == 'Fri' || todayDay == 'Sat') {
				th = '<th id="data-day_' + i + '" class="greytablebg"  onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			}else if (todayDaydate === getdateres){
				th = '<th id="data-day_' + i + '" class="hightlightedtable"  onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			}else {
				th = '<th id="data-day_' + i + '" onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			}
			dataHTML = dataHTML + th;
		}
		thHTML = thStartHTML + dataHTML + thEndHTML;

		selectedMonth = today.getMonth();
		console.log(element, lastDate.format("DD"), $(element).find('.rosterViewTH'));
		$(element).find('.rosterViewTH').html("");
		$(element).find('.rosterViewTH').html(thHTML);
	}
	else {
		var today = new Date(calendarSettings1.date);
		var firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
		var lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
		var lastDate = moment(lastDay);
		var dataHTML = "";
		for (var i = 1; i <= lastDate.format("DD"); i++) {
			var calDate = moment(new Date(today.getFullYear(), today.getMonth(), i));
			var todayDay = calDate.format("ddd");

			var th = "";// "<th id="data-day_" + i + "" onclick="ChangeRosteringDate(" + i + ",this)">" + calDate.format("ddd") + " " + calDate.format("DD") + "</th>";
			if (todayDay == 'Fri' || todayDay == 'Sat') {
				th = '<th id="data-day_' + i + '" class="greytablebg"  onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			}
			else {
				th = '<th id="data-day_' + i + '" onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			}
			dataHTML = dataHTML + th;

		}
		
		thHTML = thStartHTML + dataHTML + thEndHTML;
		//GetTodaySelectedDate()
		selectedMonth = today.getMonth();
		console.log(element, lastDate.format("DD"), $(element).find('.rosterViewTH'));
		$(element).find('.rosterViewTH').html("");
		$(element).find('.rosterViewTH').html(thHTML);


	}

	var month = moment(new Date()).format("MM");
	var month1 = calendarSettings1.date.format("MM");
	if (month == month1) { GetTodaySelectedDate(); }

}
//function for dynamic set calender header data on right calender


//function for highlight today calender date in header
// function GetTodaySelectedDate() {
// 	var tdate = calendarSettings1.today.format("DD");
// 	$("#data-day_" + tdate).addClass("hightlightedtable");
// }
 //function for highlight today calender date in header


//on next month title display on arrow click
// function rosterweekincrement() {

// 	calendarSettings1.date.add(1, 'Weeks').subtract(6,'days');     
	
// 	GetHeaders(1);
// 	displayCalendar(calendarSettings1);
// }
// 	//on next month title display on arrow click

// 	//on previous month title display on arrow click
// function rosterweekdecrement() {       
// 	calendarSettings1.date.subtract(1, 'Weeks').subtract(7, 'days');        
// 	GetHeaders(1);
// 	displayCalendar(calendarSettings1);
// }
	//on previous month title display on arrow click

//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////


// edit project notification
function editproject() {
	if ($("#editformmodal").valid()) {
		$(".modal").modal("hide");
		notificationmsg("Success!!", "");
	}
}
// edit project notification

//datatable function call for staff
function staffmanagement() {
	let table;
	if($.fn.dataTable.isDataTable('#staffdatatable')){
		table = $('#staffdatatable').DataTable();
		table.clear();
		table.destroy();
		// table.rows().invalidate().draw();
	} 
	// else {
	table = $('#staffdatatable').on('processing.dt', function (e, settings, processing) { 
		$('.dataTables_processing')
		.css('display', processing ? 'flex' : 'none'); })
		.on('preXhrpreXhr.dt', function (e, settings, data) {
	}).DataTable({
		"dom": '<"top"fl><"position-relative table-responsive customtableborder"tr><"bottom"ip><"clear">',
		"paging": true,
		"processing": true,
		"ordering": true,
		"info": true,
		"autowidth": true,

		"language": {
			"loadingRecords": "Loading...",
			"processing": "Processing...",
			"search": '<i class="fas fa-search"></i>',
			"searchPlaceholder": "Search",
			"paginate": {
				"previous": "<",
				"next": ">"
			},
		},
		"lengthMenu": [[50, 100, 500, -1], [50, 100, 500, "All"]],
		// "pageLength": 50,
		order: [],
		columnDefs: [{ orderable: false, targets: [0] }]

	}).columns.adjust();
	// }
}
//datatable function call for staff

//function for assign dropdown filter
function assignedfilter(value1) {
	var filtervale = $("#desktopview.filtertextget").text().trim();
	var functionmainvalue = value1;

	if (filtervale == "Assigned" && functionmainvalue == 0) {
		$(".unassignedbtn").removeClass("d-none");
		$(".assignedbtn").addClass("d-none");
		$(".editbtn").removeClass("d-none");
		$(".mainclassfilter").removeClass("d-none");
		$(".allfilters").addClass("d-none");
	}
	else if (filtervale == "Unassigned" && functionmainvalue == 0) {
		$(".unassignedbtn").addClass("d-none");
		$(".assignedbtn").removeClass("d-none");
		$(".editbtn").removeClass("d-none");
		$(".mainclassfilter").removeClass("d-none");
		$(".allfilters").addClass("d-none");
	}
	else {
		$(".unassignedbtn").addClass("d-none");
		$(".assignedbtn").addClass("d-none");
		$(".editbtn").addClass("d-none");
	}
}
//function for assign dropdown filter

//function for assign dropdown clear button filter
function clearassignfilter() {
	$(".assigneddrpval").html("");
	$(".assigneddrpval").html("Assigned");
	cur_page.page.page.filters.assigned = 1;
	render_staff($(".layoutSidenav_content").attr("data-view"));
}
//function for assign dropdown clear button filter

//show (Assign to all) button on unassign option click on assign dropdown
function filteassignget() {
	$(".allfilters").removeClass("d-none");

}
//show (Assign to all) button on unassign option click on assign dropdown

//clear dropdown value
function clearallfilter() {
	setup_staff_filters()
	$(".allfilters").removeClass("d-none");
	$(".allfilters").addClass("d-none");
	$(".assigneddrpval").html("");
	$(".assigneddrpval").html("Assigned");
	$(".hideshowprjname").addClass("d-none");
	$(".btnunassignonclick").removeClass("d-block").addClass("d-none");
	$(".rostercustomstafftab").removeClass("d-none").addClass("d-flex");
	render_staff($(".layoutSidenav_content").attr("data-view"));
}
//clear dropdown value

//function for notification call and pass parameter
function notificationmsg(title, message) {

	var titletxt = title;
	var messagetxt = message;
	$.notify({
		// options
		title: "<strong>" + titletxt + "</strong>",
		message: messagetxt,
		icon: "far fa-check-circle notifycolor",
		target: "_blank"
	},
		{
			element: "body",
			type: "success",
			showProgressbar: false,
			placement: {
				from: "top",
				align: "right"
			},
			offset: 20,
			spacing: 10,
			z_index: 1080,
			delay: 3300,
			timer: 500,
			url_target: "_blank",
			mouse_over: null,
			animate: {
				enter: "animated fadeInDown",
				exit: "animated fadeOutRight"
			},
			onShow: null,
			onShown: null,
			onClose: null,
			onClosed: null,
			icon_type: "class",
		});
}


///////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////


	
function render_staff(view){
	let filters = cur_page.page.page.filters;
	console.log(filters);
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_staff', filters)
	.then(res => {
		console.log(res, view);
		if(res){
			let data = res;
			if(view == "list"){
				render_staff_list_view(data);
			}else if(view == "card"){
				render_staff_card_view(data);
			}
		}
	})
}

function render_staff_list_view(data){
	// $('#staffdatatable tbody').empty();
	if($.fn.dataTable.isDataTable('#staffdatatable')){
		table = $('#staffdatatable').DataTable();
		table.clear();
		table.destroy();
		// table.rows().invalidate().draw();
	} 
	console.log("Called");
	data.forEach(function(employee){
		let {employee_id, employee_name, nationality, mobile_no, email, designation, project, site, shift, department} = employee;
		let row = `
		<tr>
			<td>
				<label class="checkboxcontainer">
					<span class="text-white"></span>
					<input type="checkbox" name="datatableckeckbox" class="datatablecjeckbox" data-employee-id="${employee_id}">
					<span class="checkmark"></span>
				</label>
			</td>
			<td>
				<a href="#"
					class="themecolor text-decorationunderline customgetposition d-none d-md-block">${employee_id}</a>
				<!--for mobile modal id strat-->
				<a href="#" data-target="#staffcardmodal" data-toggle="modal"
					class="themecolor text-decorationunderline d-block d-md-none">${employee_id}</a>
				<!--for mobile modal id end-->
			</td>
			<td>
				${employee_name || 'N/A'}
			</td>
			<td>
				${nationality || 'N/A'}
			</td>
			<td>
				${mobile_no || 'N/A'}
			</td>
			<td>
				${email || 'N/A'}					
			</td>
			<td>
				${designation || 'N/A'}
			</td>
			<td>
				${project || 'N/A'}
			</td>
			<td>
				${site || 'N/A'}
			</td>
			<td>
				${shift || 'N/A'}
			</td>
			<td>
				${department || 'N/A'}
			</td>
		</tr>`;
		$('#staffdatatable tbody').append(row);	
	
	});
	staffmanagement();
}

function render_staff_card_view(data){
	$('.staff-card-wrapper').empty();
	console.log("Called");
	data.forEach(function(employee, i){
		let {employee_id, employee_name, nationality, mobile_no, email, designation, project, site, shift, department, image} = employee;
		let row = `
		<div class="col-xs-12 col-sm-12 col-md-6 col-lg-4 mb30">
			<div class="card h-100">
				<div class="card-body p-0">
					<div class="card-body pl12 pt12 pb12 pr-0">
						<div class="media align-items-start">
							<div class="img-block justify-content-between justify-content-md-start flex-row flex-md-column custommobrescard"
								style="">
								<div class="">
									<span class="img_block_responsive">
										<img src="${image ? image: 'images/userfill.svg'}" class="img_responsive">
									</span>
									<span class="text-md-center font16 cardidcolor d-block">Id: ${employee_id}</span>
								</div>
								<div class="d-md-none pr12">
									<label class="checkboxcontainer"><span class="text-white"></span><input
											type="checkbox" name="cardviewcheckbox"
											class="cardviewcheckbox"><span
											class="checkmark rightcheckbox"></span></label>
								</div>
							</div>
							<div class="media-body pl20 w-100 plsm-0 overflow-hidden">
								<div class="topportion">
									<div class="pb8 pr12">
										<div
											class="d-flex w-100 justify-content-between align-items-center show-read-more">
											<div class="show-read-more cardtitlecolor font20 ">${employee_name || 'N/A'}</div>
											<label class="checkboxcontainer d-none d-md-block"><span
													class="text-white"></span><input type="checkbox"
													name="cardviewcheckbox" class="cardviewcheckbox"><span
													class="checkmark rightcheckbox"></span></label>
										</div>
									</div>
									<div class="font16 pb8 lightgrey show-read-more">
										<span class="">${designation || 'N/A'}</span>
									</div>
									<div class="font16 pb8 lightgrey show-read-more">
										<span class="">${department || 'N/A'}</span>
									</div>
									<div class="font16 pb8 lightgrey show-read-more ">
										<!--<span><img src="images/icon/calendar.svg" class="responiconfont"></span>-->
										<span class="pl6">${nationality || 'N/A'}</span>
									</div>
									<div class="font16 pb8 lightgrey show-read-more ">
										<span><img src="images/icon/phone.svg" class="responiconfont"></span>
										<span class="pl6">${mobile_no || 'N/A'}</span>
									</div>
									<div class="font16 pb8 lightgrey show-read-more ">
										<span><img src="images/icon/Email.svg" class="responiconfont"></span>
										<span class="pl6">${email || 'N/A'}</span>
									</div>
								</div>
								<div class="topportion bordertopdotted">
									<div class="d-flex justify-content-between pr12">
										<div class="pt8 w-100 overflow-hidden">
											<div class="font16 pb8 show-read-more">
												<span class="lightgrey customwidthcard">Project: </span>
												<span class="cardidcolor font-medium">
												${project || 'N/A'}</span>
											</div>
											<div class="font16 pb8 show-read-more">
												<span class="lightgrey customwidthcard">Site: </span>
												<span class="cardidcolor font-medium">${site || 'N/A'}</span>
											</div>
											<div class="font16 pb8 show-read-more">
												<span class="lightgrey customwidthcard">Shift: </span>
												<span class="cardidcolor font-medium">${shift || 'N/A'}</span>
											</div>
										</div>
										<!--<div class="pt8">
											<a class="iconfont text-decoration-none" href="#"
												data-target="#cardeditusermodal" data-toggle="modal">
												<i class="fas fa-pencil-alt lightgrey"></i>
											</a>
										</div>-->
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>`;
		$('.staff-card-wrapper').append(row);
	});
}

function setup_staff_filters(page){
	let filters = {
		assigned: 1,
		company: '',
		project: '',
		site: '',
		shift: '',
		department: '',
		designation: '',
		post_type: ''
	};
	if(page){
		page.filters = filters;
	}else{
		cur_page.page.page.filters = filters;
	}
}

function setup_staff_filters_data(){
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_staff_filters_data')
	.then(res => {
		cur_page.page.page.staff_filters_data = res;
		let {company, projects, sites, shifts, departments, designations} = res;
		company.forEach(function(element){
			let companies = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
			$('.company-dropdown').append(companies);
		});
		projects.forEach(function(element){
			let project = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
			$('.project-dropdown').append(project);
		});
		sites.forEach(function(element){
			let site = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
			$('.site-dropdown').append(site);
		});
		shifts.forEach(function(element){
			let shift = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
			$('.shift-dropdown').append(shift);
		});
		departments.forEach(function(element){
			let department = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
			$('.department-dropdown').append(department);
		});
		designations.forEach(function(element){
			let designation = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
			$('.designation-dropdown').append(designation);
		});

		/*dropdown for assign set text on hide show clear filter text*/
		$(".customredropdown .customdropdownheight .dropdown-item").click(function () {
			let text = $(this).html();
			let filter_type = $(this).parent().attr('data-filter-type');
			console.log($(this), text, filter_type);
			/*$(this).parent().parent().parent().find(".dropdown-toggle .dropdowncustomres").html(text);*/
			$(this).closest(".btn-group").find(".dropdown-toggle .dropdowncustomres").html(text);
			if(filter_type == "assigned"){
				// text == "Assigned" ? 1 : 0
				cur_page.page.page.filters[filter_type] = text == "Assigned" ? 1 : 0 ;
			}else{
				cur_page.page.page.filters[filter_type] = text;
			}
			if (text === "Assigned") {

				$(".hideshowprjname").addClass("d-none");
				$(".btnunassignonclick").removeClass("d-block").addClass("d-none");
				$(".rostercustomstafftab").removeClass("d-none").addClass("d-flex");
			}
			else {

				$(".hideshowprjname").removeClass("d-none");
				$(".btnunassignonclick").removeClass("d-none").addClass("d-block");
				$(".rostercustomstafftab").addClass("d-none").removeClass("d-flex");
			}
			render_staff($(".layoutSidenav_content").attr("data-view"));
		});
		/*dropdown for assign set text on hide show clear filter text*/
	})
}

function ClearServiceBoard(e){
	console.log($(e).attr('data-filter-type'));
	let filter_type = $(e).attr('data-filter-type');
	let filter_text = filter_type.charAt(0).toUpperCase() + filter_type.slice(1)
	$(e).closest(".btn-group").find(".dropdown-toggle .dropdowncustomres").html(filter_text);
	cur_page.page.page.filters[filter_type] = '';
	render_staff($(".layoutSidenav_content").attr("data-view"));
}

function staff_edit_dialog(){
	let employees = $(".datatablecjeckbox:checked").map(function () {
		return $(this).attr("data-employee-id");
	}).get();
	console.log(employees);

	let d = new frappe.ui.Dialog({
		'title': 'Edit',
		'fields': [
			{'label': 'Project', 'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', get_query: function(){
					return {
						"filters": { 
							"project_type": "External"							
						},
						"page_len": 9999
					};
				}
			},
			{'label': 'Site', 'fieldname': 'site', 'fieldtype': 'Link', 'options': 'Operations Site', get_query: function(){
				console.log(d, this);
				let project = d.get_value('project')
				if(project){
					return {
						"filters": { project },
						"page_len": 9999
					};
				}
			}},
			{'label': 'Shift', 'fieldname': 'shift', 'fieldtype': 'Link', 'options': 'Operations Shift',  get_query: function(){
				console.log(d, this);
				let site = d.get_value('site')
				if(site){
					return {
						"filters": { site },
						"page_len": 9999
					};
				}
			}},
			{'fieldtype': 'Section Break'},
			{'label': 'Assign from','fieldname': 'assign_from', 'fieldtype': 'Select', 'options': '\nDate\nImmediately'},
			{'fieldtype': 'Column Break'},
			{'fieldname': 'assign_date', 'fieldtype': 'Date', 'default': frappe.datetime.add_days(frappe.datetime.nowdate(), '1'), 'depends_on': "eval:this.get_value('assign_from') == 'Date'"}
		],
		primary_action: function(){
			d.hide();
			show_alert(d.get_values());
		}
	});
	d.show();
}

//
//
//
//
// Week View Post

//function for dynamic set calender header data on right calender
function GetWeekHeaders(IsMonthSet, element) {
	var thHTML = "";
	var thStartHTML = `<th class="">Post Type / Days</th>`;
	var thEndHTML = "<th>Total</th>";
	var selectedMonth;
	element = get_wrapper_element(element);
	console.log(element);
	if (IsMonthSet == 0) {
		var today = new Date();
		// var firstDay = weekCalendarSettings.date.startOf("week").date();
		// var endofday = weekCalendarSettings.date.endOf("week").date();
		// console.log(firstDay, endofday);
		var firstDay = new Date(startOfWeek(today));
		var lastDay = new Date(today.getFullYear(), today.getMonth() + 1, today.getDate() + 6);
		var lastDate = moment(lastDay);
		var getdateres = moment(new Date()).format("DD");

		//console.log(lastDate.format("DD"));
		var dataHTML = "";
		var calDate = moment(new Date(firstDay));//moment(new Date(firstDay.getFullYear(), firstDay.getMonth(), i));
		for (var i = 1; i <= 7; i++) {

			// var calDate = moment(new Date(firstDay.getFullYear(), firstDay.getMonth(), i));
			var todayDay = calDate.format("ddd");
			var weekNumber = getWeekOfMonth(calDate.toDate());
			var todayDaydate = calDate.format("DD");

			var th = "";
			if (todayDay == 'Fri' || todayDay == 'Sat') {
				th = `<th id="data-day_${i}" class="greytablebg"  onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			else if (todayDaydate === getdateres) {
				th = `<th id="data-day_${i}" class="hightlightedtable"  onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			else {
				th = `<th id="data-day_${i}"  onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			dataHTML = dataHTML + th;
			calDate = calDate.add(1, "Days");
		}
		thHTML = thStartHTML + dataHTML + thEndHTML;

		selectedMonth = today.getMonth();

		$(element).find('.rosterViewTH').html("");
		$(element).find('.rosterViewTH').html(thHTML);
	}
	else {

		var strcalDate = weekCalendarSettings.date;
		var today = new Date(startOfWeek(strcalDate.toDate()));

		var firstDay = new Date(startOfWeek(weekCalendarSettings.date.toDate()));
		var lastDay = new Date(firstDay.getFullYear(), firstDay.getMonth() + 1, firstDay.getDate() + 7);
		var lastDate = moment(lastDay);
		var dataHTML = "";
		var calDate = moment(new Date(firstDay));
		for (var i = 1; i <= 7; i++) {

			var todayDay = calDate.format("ddd");
			var weekNumber = getWeekOfMonth(calDate.toDate());
			var th = "";
			if (todayDay == 'Fri' || todayDay == 'Sat') {
				th = `<th id="data-day_${i}" class="greytablebg"  onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			else {
				th = `<th id="data-day_${i}"  onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			dataHTML = dataHTML + th;

			calDate = calDate.add(1, "Days");
		}
		thHTML = thStartHTML + dataHTML + thEndHTML;
		selectedMonth = today.getMonth();
		// console.log(dataHTML);
		$(element).find('.rosterViewTH').html("");
		$(element).find('.rosterViewTH').html(thHTML);

	}
	var month = moment(new Date()).format("MM");
	var month1 = weekCalendarSettings.date.format("MM");
	if (month == month1) { GetTodaySelectedDate(); }

}
//function for dynamic set calender header data on right calender


//function for start week of month
function startOfWeek(date) {
	var diff = date.getDate() - date.getDay() + (date.getDay() === 0 ? -6 : 0);

	return new Date(date.setDate(diff));

}
//function for start week of month


//function for get week of month
function getWeekOfMonth(date) {
	let adjustedDate = date.getDate() + date.getDay();
	let prefixes = ["0", "1", "2", "3", "4", "5"];
	return (parseInt(prefixes[0 | adjustedDate / 7]) + 1);
}
//function for get week of month



//function for get selected date
function GetTodaySelectedDate() {
	var tdate = weekCalendarSettings.today.format("DD");
	//$("#calenderviewtable th").removeClass("hightlightedtable");
	let element = get_wrapper_element().slice(1);
	$(element).find("#data-day_" + tdate).addClass("hightlightedtable");
}
//function for get selected date

//on next month title display on arrow click
function rosterweekincrement() {
	weekCalendarSettings.date.add(1, "Weeks"); //.subtract(6, "days");
	console.log(weekCalendarSettings.date);
	GetWeekHeaders(1);
	displayWeekCalendar(weekCalendarSettings);
	let element = get_wrapper_element().slice(1);
	if(element == "rosterWeek"){
		get_roster_week_data(cur_page.page.page);
	}else{
		get_post_week_data(cur_page.page.page);
	}
}
//on next month title display on arrow click

//on previous month title display on arrow click
function rosterweekdecrement() {
	weekCalendarSettings.date.subtract(1, "Weeks"); //.subtract(7, "days");
	console.log(weekCalendarSettings.date);
	GetWeekHeaders(1);
	displayWeekCalendar(weekCalendarSettings);	
	let element = get_wrapper_element().slice(1);
	if(element == "rosterWeek"){
		get_roster_week_data(cur_page.page.page);
	}else{
		get_post_week_data(cur_page.page.page);
	}
}
//on previous month title display on arrow click

//display title of calender ex: Month of Jul 1 - 31, 2020


function displayWeekCalendar(weekCalendarSettings, page) {
	if (!page) {
		page = cur_page.page.page;
	}
	let element = get_wrapper_element();
	const weekcalendar = $(element).find('.calenderweektitlechange')[0];
	const startcalendarmonth = weekCalendarSettings.date.startOf("week").format("MMM");
	const endcalendarmonth = weekCalendarSettings.date.endOf("week").format("MMM");
	const calendaryear = weekCalendarSettings.date.format("YYYY");
	const startofday = weekCalendarSettings.date.startOf("week").date();
	const endofday = weekCalendarSettings.date.endOf("week").date();
	page.start_date =  weekCalendarSettings.date.startOf("week").format('YYYY-MM-DD');
	page.end_date = weekCalendarSettings.date.endOf("week").format('YYYY-MM-DD');
	weekcalendar.innerHTML = ""
	weekcalendar.innerHTML = "Month of <span> " + startcalendarmonth + "</span> <span> " + startofday + "</span> - <span> " + endcalendarmonth + " </span> <span> " + endofday + "</span>, " + calendaryear + "";

}

function unschedule_staff(page){
	let employees =  [];
	let selected = [... new Set(classgrt)];
	selected.forEach(function(i){
		let [employee, date] = i.split("|");
		employees.push({employee, date}) 
	})
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let d = new frappe.ui.Dialog({
		'title': 'Unschedule Staff',
		'fields': [
			{'label': 'Start Date','fieldname': 'start_date', 'fieldtype': 'Date', 'reqd': 1,'default': date, onchange:function(){
				let start_date = d.get_value('start_date');
				if(start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))){
					// d.set_value('start_date', frappe.datetime.add_days(moment(frappe.datetime.nowdate()), '1'));
					frappe.throw(__("Start Date cannot be before today."));
				}
			}},
			{'fieldtype': 'Section Break'},
			{'label': 'Never End','fieldname': 'never_end', 'fieldtype': 'Check', onchange: function(){
				let val = d.get_value('never_end');
				if(val){
					d.set_value('select_end', 0);
				}
			}},
			{'fieldtype': 'Column Break'},
			{'label': 'Select End Date','fieldname': 'select_end', 'fieldtype': 'Check',onchange: function(){
				let val = d.get_value('select_end');
				if(val){
					d.set_value('never_end', 0);
				}
			}},
			{'fieldtype': 'Section Break', 'depends_on': "eval:this.get_value('select_end') == 1"},
			{'label': 'End Date','fieldname': 'end_date', 'fieldtype': 'Date', 'default': date,  onchange:function(){
				let end_date = d.get_value('end_date');
				let start_date = d.get_value('start_date')
				if(end_date && moment(end_date).isSameOrBefore(moment(frappe.datetime.nowdate()))){
					// d.set_value('end_date', undefined);
					frappe.throw(__("End Date cannot be before today."));
				}
				if(start_date && end_date && moment(end_date).isBefore(moment(frappe.datetime.nowdate()))){
					// d.set_value('end_date', undefined);
					frappe.throw(__("End Date cannot be before Start Date."));
				}
			}}
		],
		primary_action: function(){
			let {start_date, end_date, never_end} = d.get_values();
			frappe.xcall('one_fm.one_fm.page.roster.roster.unschedule_staff',
			{employees, start_date, end_date, never_end})
			.then(res => {
				console.log(res)
				d.hide();
				let element = get_wrapper_element().slice(1);
				page[element](page);
			});
		}
	});
	d.show();
}

function schedule_leave(page){
	let employees =  [];
	let selected = [... new Set(classgrt)];
	selected.forEach(function(i){
		let [employee, date] = i.split("|");
		employees.push({employee, date}) 
	})
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let d = new frappe.ui.Dialog({
		'title': 'Leaves',
		'fields': [
			{'label': 'Type of Leave', 'fieldname': 'leave_type', 'fieldtype': 'Select', 'reqd': 1,'options': '\nSick Leave\nAnnual Leave\nEmergency Leave'},
			{'label': 'Start Date','fieldname': 'start_date', 'fieldtype': 'Date', 'reqd': 1, 'default': date, onchange:function(){
				let start_date = d.get_value('start_date');
				if(start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))){
					// d.set_value('start_date', frappe.datetime.add_days(moment(frappe.datetime.nowdate()), '1'));
					frappe.throw(__("Start Date cannot be before today."));
				}
			}},
			{'label': 'End Date','fieldname': 'end_date', 'fieldtype': 'Date','reqd': 1, 'default': date, onchange:function(){
				let end_date = d.get_value('end_date');
				let start_date = d.get_value('start_date')
				if(end_date && moment(end_date).isSameOrBefore(moment(frappe.datetime.nowdate()))){
					// d.set_value('end_date', undefined);
					frappe.throw(__("End Date cannot be before today."));
				}
				if(start_date && end_date && moment(end_date).isBefore(moment(frappe.datetime.nowdate()))){
					// d.set_value('end_date', undefined);
					frappe.throw(__("End Date cannot be before Start Date."));
				}
			}}
		],
		primary_action: function(){
			let {leave_type, start_date, end_date} = d.get_values();
			frappe.xcall('one_fm.one_fm.page.roster.roster.schedule_leave',
			{employees, leave_type, start_date, end_date})
			.then(res => {
				console.log(res)
				d.hide();
				let element = get_wrapper_element().slice(1);
				page[element](page);
			});
		}
	});
	d.show();
}

function change_post(page){
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let d = new frappe.ui.Dialog({
		'title': 'Change Post',
		'fields': [
			{'label': 'Choose Post Type', 'fieldname': 'post_type', 'fieldtype': 'Link', 'options': 'Post Type', 'reqd': 1, get_query: function(){
				// return {
				// 	// "filters": { 
				// 	// 	"project_type": "External"							
				// 	// },
				// 	"page_len": 9999
				// };
			}},	
		],
		primary_action: function(){
			d.hide();			
			let element = get_wrapper_element().slice(1);
			page[element](page);

		}
	});
	d.show();
}

function schedule_change_post(page){
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	// let employee = "HR-EMP-00002";	
	let employees =  [];
	let selected = [... new Set(classgrt)];
	selected.forEach(function(i){
		let [employee, date] = i.split("|");
		employees.push({employee, date}) 
	})
	let d = new frappe.ui.Dialog({
		'title': 'Schedule/Change Post',
		'fields': [
			{'label': 'Shift', 'fieldname': 'shift', 'fieldtype': 'Link', 'options': 'Operations Shift', 'reqd': 1, onchange:function(){
				let name = d.get_value('shift');
				if(name){
					frappe.db.get_value("Operations Shift",name,["site", "project"])
					.then(res => {
						console.log(res);
						let {site, project} = res.message;
						d.set_value('site', site);
						d.set_value('project', project);
					})
				}
			}},
			{'label': 'Site', 'fieldname': 'site', 'fieldtype': 'Link', 'options': 'Operations Site', 'read_only': 1},
			{'label': 'Project', 'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', 'read_only': 1},
			{'label': 'Choose Post Type', 'fieldname': 'post_type', 'fieldtype': 'Link','reqd': 1,  'options': 'Post Type', get_query: function(){
				return {
					query: "one_fm.one_fm.page.roster.roster.get_filtered_post_types",
					filters: {"shift": d.get_value('shift')}
				};
			}},
			// {'label': 'Start Date','fieldname': 'start_date', 'fieldtype': 'Date', 'reqd': 1, 'default': date, 
			// 	onchange:function(){
			// 		let start_date = moment(d.get_value('start_date'));
			// 		console.log(start_date, frappe.datetime.nowdate());
			// 		if(start_date && start_date.isSameOrBefore(moment(frappe.datetime.nowdate()))){
			// 			frappe.throw(__("Start Date cannot be before today."));
			// 		}
			// 	}
			// },
			// {'label': 'End Date','fieldname': 'end_date', 'fieldtype': 'Date', 'reqd': 1, 'default': date,  
			// 	onchange:function(){
			// 		let start_date = d.get_value('start_date');
			// 		let end_date = d.get_value('end_date');
			// 		if(end_date && moment(end_date).isBefore(moment(frappe.datetime.nowdate()))){
			// 			frappe.throw(__("End Date cannot be before today."));
			// 		}
			// 		if(start_date && end_date && moment(end_date).isBefore(start_date)){
			// 			frappe.throw(__("End Date cannot be before Start date."));
			// 		}
			// 	}
			// }	
		],
		primary_action: function(){
			let {shift, site, post_type, project} = d.get_values();
			frappe.xcall('one_fm.one_fm.page.roster.roster.schedule_staff',
			{employees, shift, post_type})
			.then(res => {
				console.log(res)
				d.hide();
				let element = get_wrapper_element().slice(1);
				page[element](page);
			});
		}
	});
	d.show();
}
