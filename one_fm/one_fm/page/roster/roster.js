// Frappe Init function to render Roster
frappe.pages['roster'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Roster',
		single_column: true
	});
	$('#page-roster').empty().append(frappe.render_template('roster'));

	load_js(page);
};

// Initializes the page with default values 
function load_js(page) {
	$(this).scrollTop(0);

	window.isMonth = 1;
	window.classgrtw = [];
	window.classgrt = [];
	setup_staff_filters(page);
	setup_topbar_events(page);

	$(`a[href="#"]`).click(function (e) {
		if (!$(this).hasClass('navbar-brand')) {
			e.preventDefault();
		}
	});
	$(".customredropdown .customdropdownheight .dropdown-item").click(function () {
		var text = $(this).html();
		$(this).parent().parent().parent().find(".dropdown-toggle .dropdowncustomres").html(text);
	});
	window.today = new Date();
	today.setHours(0, 0, 0, 0);
	if ($('.layoutSidenav_content').attr('data-view') == 'roster') {
		setup_filters(page);
		page.datepicker = $(`[data-page-route="roster"] #datepicker`).flatpickr({ inline: true });
		page.datepicker.config.onChange.push(function (selectedDates, dateStr, instance) {
			$("#calenderviewtable th").removeClass("hightlightedtable");
			let evt = new Date(dateStr);
			window.calendarSettings1 = {
				date: moment(new Date(evt.getFullYear(), evt.getMonth(), evt.getDate())),//.set("date", 4),
				today: moment()
			};
			window.weekCalendarSettings = {
				date: moment(new Date(evt.getFullYear(), evt.getMonth(), evt.getDate())).startOf("isoweek"),
				today: moment()
			};
			let element = get_wrapper_element();
			if (element == '.rosterMonth' || element == '.rosterOtMonth' || element == '.postMonth') {
				displayCalendar(calendarSettings1, page);
				GetHeaders(0);

				element = element.slice(1);
				page[element](page);
				$(element).find('.rosterViewTH').children().removeClass("hightlightedtable");
				$(element).find('.rosterViewTH').find("#data-day_" + evt.getDate()).addClass("hightlightedtable");

			} else {
				displayWeekCalendar(weekCalendarSettings, page);
				GetWeekHeaders(0);
				element = element.slice(1);
				page[element](page);
				$(element).find('.rosterViewTH').children().removeClass("hightlightedtable");
				$(element).find('.rosterViewTH').find("#data-day_" + evt.getDate()).addClass("hightlightedtable");
			}
		});
		$('.flatpickr-next-month').on('click', function () {
			incrementMonth(page);
		});
		$('.flatpickr-prev-month').on('click', function () {
			decrementMonth(page);
		});
		$rosterMonth = $('.rosterMonth');
		$rosterOtMonth = $('.rosterOtMonth');
		$postMonth = $('.postMonth');
		$rosterWeek = $('.rosterWeek');
		$rosterOtWeek = $('.rosterOtWeek');
		$postWeek = $('.postWeek');
		function basicRosterClick() {
			$(".rosterClick").removeClass("active");
			$rosterMonth.removeClass("d-none");
			$rosterOtMonth.addClass("d-none");
			$rosterWeek.addClass("d-none");
			$rosterOtWeek.addClass("d-none");
			$(".switch-container").removeClass("d-none");
			$(this).parent().addClass("active");
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".rosterMonth");
			get_roster_data(page);
		};
		function otRosterClick() {
			$(".rosterClick").removeClass("active");
			$(".filterhideshow").addClass("d-none");
			$rosterMonth.addClass("d-none");
			$rosterOtMonth.removeClass("d-none");
			$rosterWeek.addClass("d-none");
			$rosterOtWeek.addClass("d-none");
			$(".switch-container").removeClass("d-none");
			$(this).parent().addClass("active");
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".rosterOtMonth");
			let wrapper_element = get_wrapper_element();
			if (page.employee_search_name) {
				$(wrapper_element).find(".search-employee-name").val(page.employee_search_name);
			}
			if (page.employee_search_id) {
				$(wrapper_element).find(".search-employee-id").val(page.employee_search_id);
			}
			get_roster_data(page, true);

		};
		$(".rosterviewclick").click(function () {
			$rosterMonth.removeClass("d-none");
			$rosterOtMonth.addClass("d-none");
			$postMonth.addClass("d-none");
			$rosterWeek.addClass("d-none");
			$rosterOtWeek.addClass("d-none");
			$postWeek.addClass("d-none");
			$(".maintabclick").removeClass("active");
			$(".switch-container").removeClass("d-none");
			$(this).parent().addClass("active");
			$(".Postfilterhideshow").addClass("d-none");
			$(".filterhideshow").addClass("d-none");
			$(".rosterviewfilterbg").removeClass("d-none");
			$(".postviewfilterbg").addClass("d-none");
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".rosterMonth");
			$(".basicRosterClick").click(basicRosterClick);
			$(".otRosterClick").click(otRosterClick);
			get_roster_data(page);
		});
		$(".postviewclick").click(function () {
			$(".basicRosterClick").off('click');
			$(".otRosterClick").off('click');
			$rosterMonth.addClass("d-none");
			$rosterOtMonth.addClass("d-none");
			$postMonth.removeClass("d-none");
			$rosterWeek.addClass("d-none");
			$rosterOtWeek.addClass("d-none");
			$postWeek.addClass("d-none");
			$(".maintabclick").removeClass("active");
			$(".switch-container").addClass("d-none");
			$(this).parent().addClass("active");
			$(".Postfilterhideshow").addClass("d-none");
			$(".filterhideshow").addClass("d-none");
			$(".rosterviewfilterbg").addClass("d-none");
			$(".postviewfilterbg").removeClass("d-none");
			displayCalendar(calendarSettings1, page);
			GetHeaders(0, ".postMonth");
			get_post_data(page);
		});
		$(".basicRosterClick").click(basicRosterClick);
		$(".otRosterClick").click(otRosterClick);

		//week view click jquery
		$('.postmonthviewclick').click(function () {
			$rosterMonth.addClass("d-none");
			$postMonth.removeClass("d-none");
			$rosterWeek.addClass("d-none");
			$postWeek.addClass("d-none");
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".postMonth");
			get_post_data(page);
		});
		$('.monthviewclick').click(function () {
			$rosterMonth.removeClass("d-none");
			$postMonth.addClass("d-none");
			$rosterWeek.addClass("d-none");
			$postWeek.addClass("d-none");
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".rosterMonth");
			let wrapper_element = get_wrapper_element();
			if (page.employee_search_name) {
				$(wrapper_element).find(".search-employee-name").val(page.employee_search_name);
			}
			if (page.employee_search_id) {
				$(wrapper_element).find(".search-employee-id").val(page.employee_search_id);
			}
			get_roster_data(page);
		});

		//tab click for week view data function call

		$(".editpostclassclick").click(function () {
			if (["Operations Manager", "Projects Manager"].some(i => frappe.user_roles.includes(i))) {
				let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
				let posts = [];
				let selected = [... new Set(classgrt)];

				selected.forEach(function (i) {
					let [post, date] = i.split("_");
					posts.push({ post, date });
				});
				posts = [... new Set(posts)];
				let d = new frappe.ui.Dialog({
					title: 'Edit Post',
					fields: [
						{
							label: 'Post Status',
							fieldname: 'post_status',
							fieldtype: 'Select',
							options: '\nPlan Post\nPost Off\nSuspend Post\nCancel Post',
							reqd: 1
						},
						{
							fieldname: 'sb4',
							fieldtype: 'Section Break',
							depends_on: "eval:this.get_value('post_status') == 'Plan Post'",
						},
						{
							label: 'Plan From Date',
							fieldname: 'plan_from_date',
							fieldtype: 'Date',
							default: date,
							onchange: function () {
								let plan_from_date = d.get_value('plan_from_date');
								if (plan_from_date && moment(plan_from_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Plan From Date cannot be before today."));
								}
							}
						},
						{
							label: 'Plan Till Date',
							fieldname: 'plan_end_date',
							fieldtype: 'Date',
							depends_upon: 'eval:this.get_value("project_end_date")==0',
							onchange: function () {
								let plan_end_date = d.get_value('plan_end_date');
								if (plan_end_date && moment(plan_end_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Plan Till Date cannot be before today."));
								}
							}
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
							onchange: function () {
								let cancel_from_date = d.get_value('cancel_from_date');
								if (cancel_from_date && moment(cancel_from_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Cancel From date cannot be before today."));
								}
							}
						},
						{
							label: 'Cancel Till Date',
							fieldname: 'cancel_end_date',
							fieldtype: 'Date',
							depends_upon: 'eval:this.get_value("project_end_date")==0',
							onchange: function () {
								let plan_end_date = d.get_value('cancel_end_date');
								if (plan_end_date && moment(plan_end_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Cancel Till Date cannot be before today."));
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
							onchange: function () {
								let val = d.get_value('post_off_paid');
								if (val) {
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
							onchange: function () {
								let val = d.get_value('post_off_unpaid');
								if (val) {
									d.set_value('post_off_paid', 0);
								}
							}
						},
						{
							fieldname: 'sb5',
							fieldtype: 'Section Break',
							depends_on: "eval:this.get_value('post_status') == 'Post Off'",
						},
						{ label: 'Repeat', fieldname: 'repeat', fieldtype: 'Select', options: 'Does not repeat\nDaily\nWeekly\nMonthly\nYearly' },
						{ 'fieldtype': 'Section Break', 'fieldname': 'sb1', 'depends_on': 'eval:this.get_value("post_status")=="Post Off" && this.get_value("repeat")=="Weekly"' },
						{ 'label': 'Sunday', 'fieldname': 'sunday', 'fieldtype': 'Check' },
						{ 'label': 'Wednesday', 'fieldname': 'wednesday', 'fieldtype': 'Check' },
						{ 'label': 'Saturday', 'fieldname': 'saturday', 'fieldtype': 'Check' },
						{ 'fieldtype': 'Column Break', 'fieldname': 'cb1' },
						{ 'label': 'Monday', 'fieldname': 'monday', 'fieldtype': 'Check' },
						{ 'label': 'Thursday', 'fieldname': 'thursday', 'fieldtype': 'Check' },
						{ 'fieldtype': 'Column Break', 'fieldname': 'cb2' },
						{ 'label': 'Tuesday', 'fieldname': 'tuesday', 'fieldtype': 'Check' },
						{ 'label': 'Friday', 'fieldname': 'friday', 'fieldtype': 'Check' },
						{ 'fieldtype': 'Section Break', 'fieldname': 'sb2', 'depends_on': 'eval:this.get_value("post_status")=="Post Off" && this.get_value("repeat")!= "Does not repeat"' },
						{ 'label': 'Repeat Till', 'fieldtype': 'Date', 'fieldname': 'repeat_till', 'depends_upon': 'eval:this.get_value("project_end_date")==0' },
						{
							fieldname: 'sb2',
							fieldtype: 'Section Break',
							depends_on: "eval:this.get_value('post_status') == 'Suspend Post'",
						},
						{
							label: 'Paid',
							fieldname: 'suspend_paid',
							fieldtype: 'Check',
							onchange: function () {
								let val = d.get_value('suspend_paid');
								if (val) {
									d.set_value('suspend_unpaid', 0);
								}
							}
						},
						{
							label: 'Suspend From Date',
							fieldname: 'suspend_from_date',
							fieldtype: 'Date',
							default: date,
							onchange: function () {
								let suspend_from_date = d.get_value('suspend_from_date');
								if (suspend_from_date && moment(suspend_from_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Suspend From Date cannot be before today."));
								}
							}
						},
						{
							label: 'Never End',
							fieldname: 'suspend_never_end',
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
							onchange: function () {
								let val = d.get_value('suspend_unpaid');
								if (val) {
									d.set_value('suspend_paid', 0);
								}
							}
						},
						{
							label: 'Suspend Till Date',
							fieldname: 'suspend_to_date',
							fieldtype: 'Date',
							depends_on: 'eval:this.get_value("project_end_date")==0',
							onchange: function () {
								let suspend_to_date = d.get_value('suspend_to_date');
								if (suspend_to_date && moment(suspend_to_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Suspend To Date cannot be before today."));
								}
							}
						},
						{
							fieldname: 'sb_project_end_date',
							fieldtype: 'Section Break'
						},
						{
							label: 'Project end date',
							fieldname: 'project_end_date',
							fieldtype: 'Check',
						},
					],
					primary_action_label: 'Submit',
					primary_action(values) {
						$('#cover-spin').show(0);
						frappe.call({
							method: 'one_fm.one_fm.page.roster.roster.edit_post',
							args: { posts, values },
							callback: function (r) {
								d.hide();
								$('#cover-spin').hide();
								let element = get_wrapper_element().slice(1);
								page[element](page);
							},
							freeze: true,
							freeze_message: __('Editing Post....')
						});
					}
				});

				d.show();
			}
			else{
				frappe.throw(_("Insufficient permissions to Edit Post."));
			}
		});


		//check schedule staff on load
		$("#chkassgined").prop("checked", true);
		$("#chkassgined").trigger("change");

		//Not being used right now
		// Add employee modal
		$("#addemployeeselect").select2({
			placeholder: "Search Employee",
		});

		//========================================== Roster Calendar Month View

		//display title of calender ex: Month of Jul 1 - 31, 2020
		window.calendarSettings1 = {
			date: moment().set("date", 4),
			today: moment()
		};
		window.weekCalendarSettings = {
			date: moment().startOf("isoweek"),
			today: moment()
		};

		//display title of calender ex: Month of Jul 1 - 31, 2020
		GetHeaders(0);
		displayCalendar(calendarSettings1, page);
		GetTodaySelectedDate();

		page.rosterMonth = get_roster_data;
		page.rosterOtMonth = get_roster_data;
		page.rosterWeek = get_roster_week_data;
		page.postWeek = get_post_week_data;
		page.postMonth = get_post_data;

	}


	$(`input[name="neverselectallcheckbox"]`).on("change", function () {

		if ($(this).is(":checked")) {
			$("#txtpostenddate").addClass("pointerClass");
			//add values to [] list 

			$(".selectclass").map(function () {
				if (($(this).attr("data-selectid") != undefined) && ($(this).attr("data-selectid") != null) && ($(this).attr("data-selectid") != "")) {
					if (isMonth == 1) {
						classgrt.push($(this).attr("data-selectid"));
					}
					else {
						classgrtw.push($(this).attr("data-selectid"));
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

// Show popups on clicking edit options in Roster view
function setup_topbar_events(page) {
	$('.scheduleleave').on('click', function () {
		schedule_leave(page);
	});

	$('.changepost').on('click', function () {
		schedule_change_post(page);
	});

	$('.assignchangemodal').on('click', function () {
		unschedule_staff(page);
	});
	$('.dayoff').on('click', function () {
		dayoff(page);
	});
}

//Bind events to Edit options in Roster/Post view
function bind_events(page) {
	let d1 = performance.now();
	let wrapper_element = $(get_wrapper_element());
	paginateTable(page);
	// console.log(wrapper_element.find('#paginate-parent'));
	wrapper_element.find('#paginate-parent').pageMe({ pagerSelector: '#myPager', showPrevNext: false, hidePageNumbers: false, perPage: 100 });
	if (["Operations Manager", "Site Supervisor", "Shift Manager", "Projects Manager"].some(i => frappe.user_roles.includes(i))) {
		let $rosterMonth = $('.rosterMonth');
		let $rosterOtMonth = $('.rosterOtMonth');
		let $postMonth = $('.postMonth');
		let $rosterWeek = $('.rosterWeek');
		let $postWeek = $('.postWeek');
		$postMonth.find(".hoverselectclass").on("click", function () {
			$(this).toggleClass("selectclass");
			// If the id is not already in the array, add it. If it is, remove it  
			classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);

			if (classgrt.join(",") === "") {
				$(".Postfilterhideshow").addClass("d-none");
			}
			else {
				$(".Postfilterhideshow").removeClass("d-none");
			}
		});

		$postWeek.find(".hoverselectclass").on("click", function () {
			$(this).toggleClass("selectclass");
			// If the id is not already in the array, add it. If it is, remove it  
			classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);

			if (classgrt.join(",") === "") {
				$(".Postfilterhideshow").addClass("d-none");
			}
			else {
				$(".Postfilterhideshow").removeClass("d-none");
			}
		});

		//add array on each of data select from calender
		$rosterMonth.find(".hoverselectclass").on("click", function () {
			$(this).toggleClass("selectclass");

			//Show Day Off and Schedule Leave button if hidden for basic roster
			if ($(".dayoff").is(":hidden")) {
				$(".dayoff").show();
			}
			if ($(".scheduleleave").is(":hidden")) {
				$(".scheduleleave").show();
			}

			// If the id is not already in the array, add it. If it is, remove it  
			classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);

			if (classgrt.join(",") === "") {
				$(".filterhideshow").addClass("d-none");
			}
			else {
				$(".filterhideshow").removeClass("d-none");
			}
		});

		$rosterOtMonth.find(".hoverselectclass").on("click", function () {
			$(this).toggleClass("selectclass");

			//Hide Day Off and schedule leave button for OT Roster
			$(".dayoff").hide();
			$(".scheduleleave").hide();

			// If the id is not already in the array, add it. If it is, remove it  
			classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);

			if (classgrt.join(",") === "") {
				$(".filterhideshow").addClass("d-none");
			}
			else {
				$(".filterhideshow").removeClass("d-none");
			}
		});

		//add array on each of data select from calender
		$rosterWeek.find(".hoverselectclass").on("click", function () {
			$(this).toggleClass("selectclass");
			// If the id is not already in the array, add it. If it is, remove it  
			classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);

			if (classgrt.join(",") === "") {
				$(".filterhideshow").addClass("d-none");
			}
			else {
				$(".filterhideshow").removeClass("d-none");
			}
		});

		/*on checkbox select change*/
		$postWeek.find(`input[name="selectallcheckbox"]`).on("change", function () {
			if ($(this).is(":checked")) {
				$(this).parent().parent().parent().children("td").children().not("label").each(function (i, v) {
					let date = $(v).attr('data-date');
					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
					}
				});
				$(this).parent().parent().parent().children("td").children().not("label").removeClass("hoverselectclass");
				$(".Postfilterhideshow").removeClass("d-none");

			}
			else {
				$(this).parent().parent().parent().children("td").children().not("label").addClass("hoverselectclass");
				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr('data-selectid')), 1);
				});
				$(this).parent().parent().parent().children("td").children().not("label").removeClass("selectclass");
				$(".Postfilterhideshow").addClass("d-none");
			}
			$(".selectclass").map(function () {
				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];

			});
		});
		/*on checkbox select change*/
		$postMonth.find(`input[name="selectallcheckbox"]`).on("change", function () {
			if ($(this).is(":checked")) {
				$(this).parent().parent().parent().children("td").children().not("label").each(function (i, v) {
					let date = $(v).attr('data-date');
					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
					}
				});
				$(this).parent().parent().parent().children("td").children().not("label").removeClass("hoverselectclass");
				$(".Postfilterhideshow").removeClass("d-none");
			}
			else {
				$(this).parent().parent().parent().children("td").children().not("label").addClass("hoverselectclass");
				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr('data-selectid')), 1);
				});
				$(this).parent().parent().parent().children("td").children().not("label").removeClass("selectclass");
				$(".Postfilterhideshow").addClass("d-none");
			}
			$(".selectclass").map(function () {
				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];

			});

		});
		//on checkbox select change
		$rosterWeek.find(`input[name="selectallcheckbox"]`).on("change", function () {
			if ($(this).is(":checked")) {

				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {
					let [employee, date] = $(v).attr('data-selectid').split('|');
					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
					}
				});
				$(".filterhideshow").removeClass("d-none");

			}
			else {
				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr('data-selectid')), 1);
				});
				$(this).closest('tr').children("td").children().not("label").removeClass("selectclass");
				$(".filterhideshow").addClass("d-none");
			}
			$(".selectclass").map(function () {
				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];
				// if (($(this).attr("data-selectid") != undefined) && ($(this).attr("data-selectid") != null) && ($(this).attr("data-selectid") != "")) {
				// 	if (isMonth == 1) {
				// 		// classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
				// 		classgrt.push($(this).attr("data-selectid"));
				// 	}
				// 	else {
				// 		// classgrtw.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
				// 		classgrtw.push($(this).attr("data-selectid"));
				// 	}
				// }
			});
		});
		//on checkbox select change
		$rosterMonth.find(`input[name="selectallcheckbox"]`).on("change", function () {

			//Show Day Off and Schedule Leave button if hidden for basic roster
			if ($(".dayoff").is(":hidden")) {
				$(".dayoff").show();
			}
			if ($(".scheduleleave").is(":hidden")) {
				$(".scheduleleave").show();
			}

			if ($(this).is(":checked")) {
				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {
					let [employee, date] = $(v).attr('data-selectid').split('|');
					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
					}
				});
				$(".filterhideshow").removeClass("d-none");
			}
			else {
				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr('data-selectid')), 1);
				});
				$(this).closest('tr').children("td").children().not("label").removeClass("selectclass");
				$(".filterhideshow").addClass("d-none");
			}
			$(".selectclass").map(function () {
				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];
				// if (($(this).attr("data-selectid") != undefined) && ($(this).attr("data-selectid") != null) && ($(this).attr("data-selectid") != "")) {
				// 	if (isMonth == 1) {
				// 		// classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
				// 		classgrt.push($(this).attr("data-selectid"));
				// 	}
				// 	else {
				// 		classgrtw.push($(this).attr("data-selectid"));
				// 		// classgrtw.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrtw.push(this.getAttribute("data-selectid")) : classgrtw.splice(classgrtw.indexOf(this.getAttribute("data-selectid")), 1);
				// 	}
				// }
			});
		});
		$rosterOtMonth.find(`input[name="selectallcheckbox"]`).on("change", function () {

			//Hide Day Off and schedule leave button for OT Roster
			$(".dayoff").hide();
			$(".scheduleleave").hide();
			if ($(this).is(":checked")) {
				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {
					let [employee, date] = $(v).attr('data-selectid').split('|');
					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
					}
				});
				$(".filterhideshow").removeClass("d-none");
			}
			else {
				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr('data-selectid')), 1);
				});
				$(this).closest('tr').children("td").children().not("label").removeClass("selectclass");
				$(".filterhideshow").addClass("d-none");
			}
			$(".selectclass").map(function () {
				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];
			});
		});
		//on checkbox select change
		$("input[name='selectallcheckboxes']").on("change", function () {

			if ($(this).is(":checked")) {

				$(this).parent().parent().parent().children('td').children().not('label').removeClass("hoverselectclass");
				$(this).parent().parent().parent().children('td').children().not('label').addClass("selectclass");
				$(this).parent().parent().parent().children('td').children().not('label').addClass("disableselectclass");
				$('.Postfilterhideshow').removeClass('d-none');

			}
			else {
				$(this).parent().parent().parent().children('td').children().not('label').addClass("hoverselectclass");
				$(this).parent().parent().parent().children('td').children().not('label').removeClass("selectclass");
				$(this).parent().parent().parent().children('td').children().not('label').removeClass("disableselectclass");
				$('.Postfilterhideshow').addClass('d-none');
			}
			$('.selectclass').map(function () {
				classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
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
	let d2 = performance.now();
	console.log("EVENTS TIME", d2 - d1);
	bind_search_bar_event(page);
}

function bind_search_bar_event(page) {
	let wrapper_element = get_wrapper_element();
	$(wrapper_element).find(".search-employee-name").keypress(function (event) {
		if (event.which == 13) {
			// alert("You pressed enter");
			page.employee_search_name = frappe.utils.xss_sanitise($(wrapper_element).find(".search-employee-name").val());
			if (wrapper_element == ".rosterMonth") {
				get_roster_data(page);
			} else if (wrapper_element == ".rosterWeek") {
				get_roster_week_data(page);
			} else if (wrapper_element == ".rosterOtMonth") {
				get_roster_data(page, true);
			} else if (wrapper_element == ".rosterOtWeek") {
				get_roster_week_data(page, true);
			}
		}
	});
	$('.closed').on('click', function (event) {
		$(wrapper_element).find(".search-employee-name").val('');
		page.employee_search_name = '';
		if (wrapper_element == ".rosterMonth") {
			get_roster_data(page);
		} else if (wrapper_element == ".rosterWeek") {
			get_roster_week_data(page);
		} else if (wrapper_element == ".rosterOtMonth") {
			get_roster_data(page, true);
		} else if (wrapper_element == ".rosterOtWeek") {
			get_roster_week_data(page, true);
		}
	});
	$(wrapper_element).find(".search-employee-id").keypress(function (event) {
		if (event.which == 13) {
			// alert("You pressed enter");
			page.employee_search_id = frappe.utils.xss_sanitise($(wrapper_element).find(".search-employee-id").val());
			if (wrapper_element == ".rosterMonth") {
				get_roster_data(page);
			} else if (wrapper_element == ".rosterWeek") {
				get_roster_week_data(page);
			} else if (wrapper_element == ".rosterOtMonth") {
				get_roster_data(page, true);
			} else if (wrapper_element == ".rosterOtWeek") {
				get_roster_week_data(page, true);
			}
		}
	});
	$('.closed').on('click', function (event) {
		$(wrapper_element).find(".search-employee-id").val('');
		page.employee_search_id = '';
		if (wrapper_element == ".rosterMonth") {
			get_roster_data(page);
		} else if (wrapper_element == ".rosterWeek") {
			get_roster_week_data(page);
		} else if (wrapper_element == ".rosterOtMonth") {
			get_roster_data(page, true);
		} else if (wrapper_element == ".rosterOtWeek") {
			get_roster_week_data(page, true);
		}
	});
}


// Get data for Roster monthly view and render it
// isOt Parms is passed for Roster OT
function get_roster_data(page, isOt) {
	let a1 = performance.now();
	classgrt = [];
	classgrtw = [];
	let employee_search_name = '';
	let employee_search_id = ''
	if (page.employee_search_name) {
		employee_search_name = page.employee_search_name;
	}
	if (page.employee_search_id) {
		employee_search_id = page.employee_search_id;
	}
	let {start_date, end_date} = page;
	let { project, site, shift, department, post_type } = page.filters;
	let { limit_start, limit_page_length } = page.pagination;
	if (project || site || shift || department || post_type){
		$('#cover-spin').show(0);
		frappe.xcall('one_fm.one_fm.page.roster.roster.get_roster_view', { start_date, end_date, employee_search_id, employee_search_name, project, site, shift, department, post_type, isOt, limit_start, limit_page_length })
			.then(res => {
				let a2 = performance.now();
				console.log("REQ TIME", a2 - a1);
				$('#cover-spin').hide();
				render_roster(res, page, isOt);
			});
	}else{
		let $rosterMonthbody = isOt ? $('.rosterOtMonth').find('#calenderviewtable tbody') : $('.rosterMonth').find('#calenderviewtable tbody');
		let pt_row = `
		<div class="lightgrey font30 paddingdiv borderleft bordertop">
		Select atleast one filter to view roster data
		</div>
		`;
		$rosterMonthbody.empty();
		$rosterMonthbody.append(pt_row);
	}	
}
// Function responsible for Rendering the Table
// Renders on get_roster_data function
function render_roster(res, page, isOt) {
	let { post_types_data, employees_data, total } = res;
	page.pagination.total = total;

	let b1 = performance.now();
	let $rosterMonth = isOt ? $('.rosterOtMonth') : $('.rosterMonth');
	let $rosterMonthbody = isOt ? $('.rosterOtMonth').find('#calenderviewtable tbody') : $('.rosterMonth').find('#calenderviewtable tbody');
	$rosterMonthbody.empty();
	for (post_type_name in post_types_data) {
		let pt_row = `
		<tr class="colorclass scheduledStaff" data-name="${post_type_name}">
			<td class="sticky">
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
		$rosterMonthbody.append(pt_row);
		let { start_date, end_date } = page;
		start_date = moment(start_date);
		end_date = moment(end_date);
		let i = 0;
		let day = start_date;
		while (day <= end_date) {
			// for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
			let { date, post_type, count, highlight } = post_types_data[post_type_name][i];
			let pt_count = `
			<td class="${highlight}">
				<div class="text-center" data-selectid="${post_type + "|" + date}">${count}</div>
			</td>`;
			$rosterMonth.find(`#calenderviewtable tbody tr[data-name='${escape_values(post_type)}']`).append(pt_count);
			i++;
			start_date.add(1, 'days');
		}
		$rosterMonth.find(`#calenderviewtable tbody tr[data-name='${escape_values(post_types_data[post_type_name][i - 1]["post_type"])}']`).append(`<td></td>`);
	}
	let b2 = performance.now();
	console.log("POST TYPE TIME", b2 - b1);

	let c1 = performance.now();

	let emp_row_wrapper = `
	<tr class="collapse tableshowclass show">
		<td colspan="33" class="p-0">
			<table id="rowchildtable" class="table subtable mb-0 text-center" style="width:100%">
				<tbody id="paginate-parent">
				</tbody>
			</table>
		</td>
	</tr>`;
	$rosterMonthbody.append(emp_row_wrapper);
	for (employee_key in Object.keys(employees_data).sort().reduce((a, c) => (a[c] = employees_data[c], a), {})) {
		let { employee_name, employee, date } = employees_data[employee_key];
		let emp_row = `
		<tr data-name="${employee_key}">
			<td class="sticky">
				<label class="checkboxcontainer simplecheckbox">
					<span class="lightgrey font16 customfontweight fontw400 postname">${employee_key}</span>
					<input type="checkbox" name="selectallcheckbox" class="selectallcheckbox">
					<span class="checkmark"></span>
				</label>
			</td>
		</tr>
		`;
		$rosterMonth.find('#rowchildtable tbody').append(emp_row);

		let { start_date, end_date } = page;
		start_date = moment(start_date);
		end_date = moment(end_date);
		let i = 0;
		let j = 0;
		let day = start_date;
		while (day <= end_date) {
			// for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
			let sch = ``;
			let classmap = {
				'Working': 'bluebox',
				'Day Off': 'greyboxcolor',
				'Sick Leave': 'purplebox',
				'Emergency Leave': 'purplebox',
				'Annual Leave': 'purplebox',
				'ASA': 'pinkboxcolor'
			};
			let leavemap = {
				'Day Off': 'DO',
				'Sick Leave': 'SL',
				'Annual Leave': 'AL',
				'Emergency Leave': 'EL'
			};
			let attendancemap = {
				'Present': 'greenboxcolor',
				'Absent': 'redboxcolor',
				'Work From Home': 'greenboxcolor',
				'Half Day': 'greenboxcolor',
				'On Leave': 'redboxcolor'
			};
			let attendance_abbr_map = {
				'Present': 'P',
				'Absent': 'A',
				'Work From Home': 'WFH',
				'Half Day': 'HD',
				'On Leave': 'OL'
			};
			let { employee, employee_name, date, post_type, post_abbrv, employee_availability, shift, roster_type, attendance, asa } = employees_data[employee_key][i];
			//OT schedule view
			if (isOt) {
				if (post_abbrv && roster_type == 'Over-Time') {
					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date + "|" + post_type + "|" + shift + "|" + employee_availability}">${post_abbrv}</div>
					</td>`;
				}else if (employee_availability && !post_abbrv) {
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date + "|" + employee_availability}">${leavemap[employee_availability]}</div>
					</td>`;
				} else {
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox borderbox d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date}"></div>
					</td>`;
				}
				i++;
				start_date.add(1, 'days');
				$rosterMonth.find(`#rowchildtable tbody tr[data-name="${employee_name}"]`).append(sch);
			} 
			//Basic schedule view
			else {
				if (post_abbrv && roster_type == 'Basic' && !asa) {
					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so customtooltip"
							data-selectid="${employee + "|" + date + "|" + post_type + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${shift}</span></div>
					</td>`;
				}else if(post_abbrv && roster_type == 'Basic' && asa ){
					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap['ASA']} d-flex justify-content-center align-items-center so customtooltip"
							data-selectid="${employee + "|" + date + "|" + post_type + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${"Scheduled: <br>" + shift + "<br>" + "Assigned: <br>" + asa}</span></div>
					</td>`;
				}  
				else if (employee_availability && !post_abbrv) {
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date + "|" + employee_availability}">${leavemap[employee_availability]}</div>
					</td>`;
				} else if (attendance && !employee_availability) {
					if (attendance == 'P') { j++; }
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${attendancemap[attendance]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date + "|" + attendance}">${attendance_abbr_map[attendance]}</div>
					</td>`;
				} else {
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox borderbox d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date}"></div>
					</td>`;
				}
				i++;
				start_date.add(1, 'days');
				$rosterMonth.find(`#rowchildtable tbody tr[data-name="${employee_name}"]`).append(sch);

			}
		}
		$rosterMonth.find(`#rowchildtable tbody tr[data-name="${employees_data[employee_key][i - 1]['employee_name']}"]`).append(`<td>${j}</td>`);

	}
	let c2 = performance.now();
	console.log("EMPLOYEES TIME", c2 - c1);

	// frappe.show_alert({message:__("Roster updated"), indicator:'green'});
	bind_events(page);

}


// setTimeout(() => {
// 	hideSideBar();
// }, 10000);

// Get data for Roster weekly view and render it
function get_roster_week_data(page, isOt) {
	classgrt = [];
	classgrtw = [];
	let employee_search_name = '';
	if (page.employee_search_name) {
		employee_search_name = page.employee_search_name;
	}
	let { start_date, end_date } = page;
	let { project, site, shift, department, post_type } = page.filters;
	let { limit_start, limit_page_length } = page.pagination;
	console.log(limit_start, limit_page_length);
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_roster_view', { start_date, end_date, employee_search_name, project, site, shift, department, post_type, isOt, limit_start, limit_page_length })
		.then(res => {
			let { post_types_data, employees_data, total } = res;
			page.pagination.total = total;
			// $('.rosterWeek').find('#calenderweekviewtable tbody').empty();
			let $rosterWeek;
			if (isOt) $rosterWeek = $('.rosterOtWeek');
			else $rosterWeek = $('.rosterWeek');
			let $rosterWeekbody = $rosterWeek.find('#calenderweekviewtable tbody');
			$rosterWeekbody.empty();
			for (post_type_name in post_types_data) {
				let pt_row = `
			<tr class="colorclass scheduledStaff" data-name="${post_type_name}">
				<td class="sticky">
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
				$rosterWeekbody.append(pt_row);
				let { start_date, end_date } = page;
				start_date = moment(start_date);
				end_date = moment(end_date);
				let i = 0;
				let day = start_date;
				while (day <= end_date) {
					// for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
					let { date, post_type, count, highlight } = post_types_data[post_type_name][i];
					console.log(count, typeof (count));
					let pt_count = `
				<td class="${highlight}">
					<div class="text-center" data-selectid="${post_type + "|" + date}">${count}</div>
				</td>`;
					$rosterWeek.find(`#calenderweekviewtable tbody tr[data-name="${escape_values(post_type)}"]`).append(pt_count);
					i++;
					start_date.add(1, 'days');
				}
				$rosterWeek.find(`#calenderweekviewtable tbody tr[data-name="${escape_values(post_types_data[post_type_name][i - 1]['post_type'])}"]`).append(`<td></td>`);
			}
			let emp_row_wrapper = `
		<tr class="collapse tableshowclass show">
			<td colspan="33" class="p-0">
				<table id="rowchildtable" class="table subcalenderweektable mb-0 text-center" style="width:100%">
					<tbody id="paginate-parent">
					</tbody>
				</table>
			</td>
		</tr>`;
			$rosterWeekbody.append(emp_row_wrapper);

			for (employee_key in Object.keys(employees_data).sort().reduce((a, c) => (a[c] = employees_data[c], a), {})) {
				let { employee_name, employee, date } = employees_data[employee_key];
				let emp_row = `
			<tr data-name="${employee_key}">
				<td class="sticky">
					<label class="checkboxcontainer simplecheckbox">
						<span class="lightgrey font16 customfontweight fontw400 postname">${employee_key}</span>
						<input type="checkbox" name="selectallcheckbox" class="selectallcheckbox">
						<span class="checkmark"></span>
					</label>
				</td>
			</tr>
			`;
				$rosterWeek.find('#rowchildtable tbody').append(emp_row);

				let { start_date, end_date } = page;
				start_date = moment(start_date);
				end_date = moment(end_date);
				let i = 0;
				let j = 0;
				let day = start_date;
				while (day <= end_date) {
					// for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
					let sch = ``;
					let classmap = {
						'Working': 'bluebox',
						'Day Off': 'greyboxcolor',
						'Sick Leave': 'purplebox',
						'Emergency Leave': 'purplebox',
						'Annual Leave': 'purplebox'
					};
					let leavemap = {
						'Day Off': 'DO',
						'Sick Leave': 'SL',
						'Annual Leave': 'AL',
						'Emergency Leave': 'EL'
					};
					let { employee, employee_name, date, post_type, post_abbrv, employee_availability, shift } = employees_data[employee_key][i];

					if (employee_availability && post_abbrv) {
						j++;
						sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date + "|" + post_type + "|" + shift + "|" + employee_availability}">${post_abbrv}</div>
					</td>`;
					} else if (employee_availability && !post_abbrv) {
						sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date + "|" + employee_availability}">${leavemap[employee_availability]}</div>
					</td>`;
					} else {
						sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox borderbox d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date}"></div>
					</td>`;
					}
					i++;
					start_date.add(1, 'days');
					$rosterWeek.find(`#rowchildtable tbody tr[data-name="${employee_name}"]`).append(sch);
				}
				$rosterWeek.find(`#rowchildtable tbody tr[data-name="${employees_data[employee_key][i - 1]['employee_name']}"]`).append(`<td>${j}</td>`);
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
			// frappe.show_alert({message:__("Roster updated"), indicator:'green'});
			bind_events(page);
		});
}

// Get data for Post view monthly and render it
function get_post_data(page) {
	classgrt = [];
	classgrtw = [];
	let { start_date, end_date } = page;
	let { project, site, shift, department, post_type } = page.filters;
	let { limit_start, limit_page_length } = page.pagination;
	if (project || site || shift || department || post_type){
		$('#cover-spin').show(0);
		// console.log(start_date, end_date, project, site, shift, post_type,limit_start, limit_page_length);
		frappe.xcall('one_fm.one_fm.page.roster.roster.get_post_view', { start_date, end_date, project, site, shift, post_type, limit_start, limit_page_length })
			.then(res => {
				// console.log(res);
				$('#cover-spin').hide();
				page.pagination.total = res.total;
				let $postMonth = $('.postMonth');
				let $postMonthbody = $('.postMonth').find('#calenderviewtable tbody');
				$postMonthbody.empty();
				for (post_name in res.post_data) {
					let row = `
				<tr class="colorclass" data-name="${post_name}">
					<td class="sticky">
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
					$postMonthbody.append(row);
					let { start_date, end_date } = page;
					start_date = moment(start_date);
					end_date = moment(end_date);
					let i = 0;
					let day = start_date;
					while (day <= end_date) {
						// for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
						let schedule = ``;
						let classmap = {
							'Planned': 'bluebox',
							'Post Off': 'greyboxcolor',
							'Suspended': 'yellowboxcolor',
							'Cancelled': 'redboxcolor'
						};

						let { project, site, shift, date, post_status, post_type, post, name } = res["post_data"][post_name][i];
						if (name) {
							schedule = `
						<td>
							<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[post_status]} d-flex justify-content-center align-items-center so"
								data-selectid="${post + '_' + date}"
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
						else {
							schedule = `
						<td>
							<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox darkblackox d-flex justify-content-center align-items-center so"
								data-selectid="${post_name + '_' + start_date.format('YYYY-MM-DD')}"	
								data-date="${start_date.format('YYYY-MM-DD')}"
								data-post="${post_name}"
							</div>
						</td>`;
						}
						i++;
						start_date.add(1, 'days');
						$postMonth.find(`#calenderviewtable tbody tr[data-name='${escape_values(post_name)}']`).append(schedule);
					}
					$postMonth.find(`#calenderviewtable tbody tr[data-name='${escape_values(post_name)}']`).append(`<td></td>`);
				}
				// frappe.show_alert({message:__("Postview updated"), indicator:'green'});
				bind_events(page);
			}).catch(e =>{
				console.log(e);
			});
	}else{
		let $postMonthbody = $('.postMonth').find('#calenderviewtable tbody');
		let pt_row = `
		<div class="lightgrey font30 paddingdiv borderleft bordertop">
		Select a filter to view the Post data
		</div>
		`;
		$postMonthbody.empty();
		$postMonthbody.append(pt_row);
	}	
}

// Get data for Post view weekly and render it
function get_post_week_data(page) {
	classgrt = [];
	classgrtw = [];
	let { start_date, end_date } = page;
	let { project, site, shift, post_type } = page.filters;
	// console.log(page.start_date, page.end_date);
	let { limit_start, limit_page_length } = page.pagination;
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_post_view', { start_date, end_date, project, site, shift, post_type, limit_start, limit_page_length })
		.then(res => {
			// console.log(res);
			page.pagination.total = res.total;
			let $postWeek = $('.postWeek');
			let $postWeekbody = $('.postWeek').find('#calenderweekviewtable tbody');
			$postWeekbody.empty();

			for (post_name in res.post_data) {
				let row = `
			<tr class="colorclass" data-name="${post_name}">
				<td class="sticky">
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
				$postWeekbody.append(row);
				let { start_date, end_date } = page;
				start_date = moment(start_date);
				end_date = moment(end_date);
				let i = 0;
				let day = start_date;
				while (day <= end_date) {
					// for(let day = start_date; day <= end_date; start_date.add(1, 'days')){
					let schedule = ``;
					let classmap = {
						'Planned': 'blueboxcolor',
						'Post Off': 'greyboxcolor',
						'Suspended': 'yellowboxcolor',
						'Cancelled': 'redboxcolor'
					};

					let { project, site, shift, date, post_status, post_type, post, name } = res["post_data"][post_name][i];
					if (name) {
						schedule = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} hoverselectclass tablebox ${classmap[post_status]} d-flex justify-content-center align-items-center so"
							data-selectid="${post + '_' + date}"
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
					else {
						schedule = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} hoverselectclass tablebox darkblackox d-flex justify-content-center align-items-center so"
							data-selectid="${post_name + '_' + start_date.format('YYYY-MM-DD')}"	
							data-date="${start_date.format('YYYY-MM-DD')}"
							data-post="${post_name}"
						</div>
					</td>`;
					}
					i++;
					start_date.add(1, 'days');
					$postWeek.find(`#calenderweekviewtable tbody tr[data-name="${escape_values(post_name)}"]`).append(schedule);
				}
				$postWeek.find(`#calenderweekviewtable tbody tr[data-name="${escape_values(post_name)}"]`).append(`<td></td>`);
			}
			// frappe.show_alert({message:__("Postview updated"), indicator:'green'});
			bind_events(page);
		});
}
///////////////////////////////////////////////////////////////////////////////////////////////
function escape_values(string) {
	if (string && string.includes("'")) {
		string.replace(/'/g, "\'");
	}
	if (string && string.includes('"')) {
		string.replace(/"/g, "\"");
	}
	return string;
}

// Setup filters data on left sidebar
function setup_filters(page) {
	frappe.db.get_value("Employee", { "user_id": frappe.session.user }, ["name"])
		.then(res => {
			let { name } = res.message;
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

function get_projects(page) {
	let { employee_id } = page;
	frappe.xcall('one_fm.api.mobile.roster.get_assigned_projects', { employee_id })
		.then(res => {
			let parent = $('[data-page-route="roster"] #rosteringprojectselect');
			let project_data = [{ 'id': '', 'text': 'Select Project' }];
			res.forEach(element => {
				let { name } = element;
				project_data.push({ 'id': name, 'text': name });
			});
			parent.empty().trigger("change");
			parent.select2({ data: project_data });

			$(parent).on('select2:select', function (e) {
				page.filters.project = $(this).val();
				get_sites(page);
				get_shifts(page);
				let element = get_wrapper_element().slice(1);
				console.log("1");
				page[element](page);
			});
		});
}

function get_sites(page) {
	let { employee_id } = page;
	let { project } = page.filters;
	frappe.xcall('one_fm.api.mobile.roster.get_assigned_sites', { employee_id, project })
		.then(res => {
			let parent = $('[data-page-route="roster"] #rosteringsiteselect');
			let site_data = [{ 'id': '', 'text': 'Select Site' }];
			res.forEach(element => {
				let { name } = element;
				site_data.push({ 'id': name, 'text': name });
			});
			parent.empty().trigger("change");
			parent.select2({ data: site_data });

			$(parent).on('select2:select', function (e) {
				page.filters.site = $(this).val();
				get_shifts(page);
				let element = get_wrapper_element().slice(1);
				console.log("2");

				page[element](page);
			});
		});
}

function get_shifts(page) {
	let { employee_id } = page;
	let { project, site } = page.filters;
	frappe.xcall('one_fm.api.mobile.roster.get_assigned_shifts', { employee_id, project, site })
		.then(res => {
			let parent = $('[data-page-route="roster"] #rosteringshiftselect');
			let shift_data = [{ 'id': '', 'text': 'Select Shift' }];
			res.forEach(element => {
				let { name } = element;
				shift_data.push({ 'id': name, 'text': name });
			});
			parent.empty().trigger("change");
			parent.select2({ data: shift_data });

			$(parent).on('select2:select', function (e) {
				page.filters.shift = $(this).val();
				let element = get_wrapper_element().slice(1);
				console.log("3");

				page[element](page);
			});
		});
}

function get_post_types(page) {
	let { employee_id, shift } = page;
	frappe.xcall('one_fm.api.mobile.roster.get_post_types', { employee_id, shift })
		.then(res => {
			let parent = $('[data-page-route="roster"] #rosteringpostselect');
			let post_type_data = [];
			res.forEach(element => {
				let { name } = element;
				post_type_data.push({ 'id': name, 'text': name });
			});
			parent.select2({ data: post_type_data });
			$(parent).on('select2:select', function (e) {
				page.filters.post_type = $(this).val();
				let element = get_wrapper_element().slice(1);
				console.log("4");

				page[element](page);
			});

		});
}

function get_departments(page) {
	frappe.xcall('one_fm.api.mobile.roster.get_departments')
		.then(res => {
			let parent = $('[data-page-route="roster"] #rosteringdepartmentselect');
			let department_data = [];
			res.forEach(element => {
				let { name } = element;
				department_data.push({ 'id': name, 'text': name });
			});
			parent.select2({ data: department_data });
			$(parent).on('select2:select', function (e) {
				page.filters.department = $(this).val();
				let element = get_wrapper_element().slice(1);
				console.log("5");

				page[element](page);
			});

		});
}

//////////////////////////////////////////////////////////////////////////////////////////////////////////////////

//Increment month post/roster view
function incrementMonth(page) {
	if (!page) {
		page = cur_page.page.page;
	}
	calendarSettings1.date.add(1, "Months");

	let element = get_wrapper_element();
	if (element == '.rosterMonth' || element == '.rosterOtMonth' || element == '.postMonth') {
		GetHeaders(1);
		displayCalendar(calendarSettings1);
		element = element.slice(1);
		page[element](page);
	} else {
		GetWeekHeaders(1);
		displayWeekCalendar(calendarSettings1);
		element = element.slice(1);
		page[element](page);
	}
}
//Increment month post/roster view

//Decrement month post/roster view
function decrementMonth(page) {
	if (!page) {
		page = cur_page.page.page;
	}
	calendarSettings1.date.subtract(1, "Months");
	let element = get_wrapper_element();
	if (element == '.rosterMonth' || element == 'rosterOtMonth' || element == '.postMonth') {
		GetHeaders(1);
		displayCalendar(calendarSettings1);
		element = element.slice(1);
		page[element](page);
	} else {
		GetWeekHeaders(1);
		displayWeekCalendar(calendarSettings1);
		element = element.slice(1);
		page[element](page);
	}
}
//Decrement month post/roster view


function displayCalendar(calendarSettings1, page) {
	if (!page) {
		page = cur_page.page.page;
	}
	let element = get_wrapper_element();
	const calendar = $(element).find('.calendertitlechange')[0];
	const calendarTitle = calendarSettings1.date.format("MMM");
	const calendaryear = calendarSettings1.date.format("YYYY");
	const daysInMonth = calendarSettings1.date.endOf("Month").date();
	page.start_date = calendarSettings1.date.startOf("Month").format('YYYY-MM-DD');
	page.end_date = calendarSettings1.date.endOf("Month").format('YYYY-MM-DD');

	calendar.innerHTML = "";
	calendar.innerHTML = "Month of <span> " + calendarTitle + " </span> 1 - <span>" + daysInMonth + "</span>, " + calendaryear + "";

}


//function for changing roster date
function ChangeRosteringDate(seldate, this1) {
	var date = calendarSettings1.today.format("DD");
	var month = calendarSettings1.date.format("MM") - 1;
	var year = calendarSettings1.date.format("YYYY");
	var d1 = new Date(year, month, date);
	$(this1).parent().children().removeClass("hightlightedtable");
	$(this1).addClass("hightlightedtable");
	cur_page.page.page.datepicker.set('defaultDate', d1);
}
//function for changing roster date

//Get the visible roster/post view parent
function get_wrapper_element(element) {
	if (element) return element;
	let roster_element = $(".rosterMonth").attr("class").split(/\s+/).includes("d-none");
	let roster_ot_element = $(".rosterOtMonth").attr("class").split(/\s+/).includes("d-none");
	let roster_week_element = $(".rosterWeek").attr("class").split(/\s+/).includes("d-none");
	let post_element = $(".postMonth").attr("class").split(/\s+/).includes("d-none");
	let post_week_element = $(".postWeek").attr("class").split(/\s+/).includes("d-none");

	if (roster_element && roster_week_element && !post_element && post_week_element) {
		element = '.postMonth';
		return element;
	} else if (!roster_element && roster_week_element && post_element && post_week_element) {
		element = '.rosterMonth';
		return element;
	} else if (!roster_ot_element && roster_week_element && post_element && post_week_element) {
		element = '.rosterOtMonth';
		return element;
	} else if (roster_element && roster_week_element && post_element && !post_week_element) {
		element = '.postWeek';
		return element;
	} else if (roster_element && !roster_week_element && post_element && post_week_element) {
		element = '.rosterWeek';
		return element;
	}
}

const search_staff = () => {
	let key = $('input[name="searchbyradiobtn"]:checked').val();
	let search_term = $('#inputtextsearch').val();
	let view = $(".layoutSidenav_content").attr("data-view");

	frappe.xcall('one_fm.one_fm.page.roster.roster.search_staff', { key, search_term })
		.then(res => {
			if (res) {
				let data = res;
				if (view == "list") {
					render_staff_list_view(data);
				} else if (view == "card") {
					render_staff_card_view(data);
				}
			}
		});

};

// const debounce = function (fn, d) {
// 	let timer;
// 	return function () {
// 	  let context = this,
// 		args = arguments;
// 	  clearTimeout(timer);
// 	  timer = setTimeout(() => {
// 		fn.apply(context, arguments);
// 	  }, d);
// 	}
// }


//function for dynamic set calender header data on right calender
function GetHeaders(IsMonthSet, element) {

	var thHTML = "";
	var thStartHTML = `<th class="sticky vertical-sticky" style="max-width: 140px !important; min-width: 140px !important;">Post Type / Days</th>`;
	var thEndHTML = `<th class="vertical-sticky">Total</th>`;
	element = get_wrapper_element(element);
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
			if (todayDay == 'Fri' || todayDay == 'Sat') {
				th = '<th class="greytablebg vertical-sticky" style="z-index:1" id="data-day_' + i + '" onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			} else if (todayDaydate === getdateres) {
				th = '<th class="hightlightedtable vertical-sticky" style="z-index:1" id="data-day_' + i + '" onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			} else {
				th = '<th class=" vertical-sticky" style="z-index:1" id="data-day_' + i + '" onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			}
			dataHTML = dataHTML + th;
		}
		thHTML = thStartHTML + dataHTML + thEndHTML;

		selectedMonth = today.getMonth();
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
				th = '<th class="greytablebg vertical-sticky" style="z-index:1" id="data-day_' + i + '" onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			}
			else {
				th = '<th class="vertical-sticky" style="z-index:1" id="data-day_' + i + '" onclick="ChangeRosteringDate(' + i + ',this)">' + calDate.format('ddd') + ' ' + calDate.format('DD') + '</th>';
			}
			dataHTML = dataHTML + th;

		}

		thHTML = thStartHTML + dataHTML + thEndHTML;
		selectedMonth = today.getMonth();
		$(element).find('.rosterViewTH').html("");
		$(element).find('.rosterViewTH').html(thHTML);


	}

	var month = moment(new Date()).format("MM");
	var month1 = calendarSettings1.date.format("MM");
	if (month == month1) { GetTodaySelectedDate(); }

}
//function for dynamic set calender header data on right calender



//datatable function call for staff
function staffmanagement() {
	let table;
	if ($.fn.dataTable.isDataTable('[data-page-route="roster"] #staffdatatable')) {
		table = $('[data-page-route="roster"] #staffdatatable').DataTable();
		table.clear();
		table.destroy();
		// table.rows().invalidate().draw();
	}
	// else {
	table = $('[data-page-route="roster"] #staffdatatable').on('processing.dt', function (e, settings, processing) {
		$('.dataTables_processing')
			.css('display', processing ? 'flex' : 'none');
	})
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
	var filtervale = $(`[data-page-route="roster"] #desktopview.filtertextget`).text().trim();
	var functionmainvalue = value1;

	if (filtervale == "Assigned" && functionmainvalue == 0) {
		// $(".unassignedbtn").removeClass("d-none");
		// $(".assignedbtn").addClass("d-none");
		$(".editbtn").removeClass("d-none");
		$(".mainclassfilter").removeClass("d-none");
		$(".allfilters").addClass("d-none");
	}
	else if (filtervale == "Unassigned" && functionmainvalue == 0) {
		// $(".unassignedbtn").addClass("d-none");
		// $(".assignedbtn").removeClass("d-none");
		$(".editbtn").removeClass("d-none");
		$(".mainclassfilter").removeClass("d-none");
		$(".allfilters").addClass("d-none");
	}
	else {
		// $(".unassignedbtn").addClass("d-none");
		// $(".assignedbtn").addClass("d-none");
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
	setup_staff_filters();
	$(".allfilters").removeClass("d-none");
	$(".allfilters").addClass("d-none");
	$(".assigneddrpval").html("");
	$(".assigneddrpval").html("Assigned");
	$(".hideshowprjname").addClass("d-none");
	// $(".btnunassignonclick").removeClass("d-block").addClass("d-none");
	// $(".rostercustomstafftab").removeClass("d-none").addClass("d-flex");
	render_staff($(".layoutSidenav_content").attr("data-view"));
}
//clear dropdown value

//function for notification call and pass parameter
function notificationmsg(title, message) {

	var titletxt = title;
	var messagetxt = message;
	$.notify({
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



function render_staff(view) {
	let filters = cur_page.page.page.filters;
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_staff', filters)
		.then(res => {
			if (res) {
				let data = res;
				if (view == "list") {
					render_staff_list_view(data);
				} else if (view == "card") {
					render_staff_card_view(data);
				}
			}
		});
}

function render_staff_list_view(data) {
	if ($.fn.dataTable.isDataTable('[data-page-route="roster"] #staffdatatable')) {
		table = $('[data-page-route="roster"] #staffdatatable').DataTable();
		table.clear();
		table.destroy();
	}
	let $staffdatatable = $('#staffdatatable tbody');
	data.forEach(function (employee) {
		let { name, employee_id, employee_name, nationality, mobile_no, email, designation, project, site, shift, department } = employee;
		let row = `
		<tr>
			<td>
				<label class="checkboxcontainer">
					<span class="text-white"></span>
					<input type="checkbox" name="datatableckeckbox" class="datatablecjeckbox" data-employee-id="${name}">
					<span class="checkmark"></span>
				</label>
			</td>
			<td>
				<div href="#"
					class="themecolor customgetposition d-none d-md-block">${employee_id}</div>
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
		$staffdatatable.append(row);
		$(".datatablecjeckbox").change(function () {
			let getdatatableval = this.checked;
			if (getdatatableval === true) {
				$(this).parent().parent().parent().css("background", "#E7EDFB");
				assignedfilter(0);
			}
			else {
				$(this).parent().parent().parent().css("background", "#ffffff");
			}
			let checked = $(".datatablecjeckbox:checked");
			if (checked.length == 0) assignedfilter(1);
		});
	});
	staffmanagement();
}

function render_staff_card_view(data) {
	$('.staff-card-wrapper').empty();
	data.forEach(function (employee, i) {
		let { name, employee_id, employee_name, nationality, mobile_no, email, designation, project, site, shift, department, image } = employee;
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
										<img src="${image ? image : 'images/userfill.svg'}" class="img_responsive">
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
													name="cardviewcheckbox" class="cardviewcheckbox" data-employee-id="${name}"><span
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
		$(".cardviewcheckbox").change(function () {
			var getdatatableval = this.checked;
			if (getdatatableval === true) {
				assignedfilter(0);
			}
			else {
				assignedfilter(1);
			}
		});
	});
	staffmanagement();
}

function setup_staff_filters(page) {
	let filters = {
		assigned: 1,
		company: '',
		project: '',
		site: '',
		shift: '',
		department: '',
		designation: '',
		post_type: '',
		employee_search_name: '',
		employee_search_id: ''
	};
	let pagination = {
		limit_start: 0,
		limit_page_length: 100
	};
	if (page) {
		page.filters = filters;
		page.pagination = pagination;
	} else {
		cur_page.page.page.filters = filters;
		cur_page.page.page.pagination = pagination;
	}
	console.log(page);
}

function setup_staff_filters_data() {
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_staff_filters_data')
		.then(res => {
			cur_page.page.page.staff_filters_data = res;
			let { company, projects, sites, shifts, departments, designations } = res;
			let $companydropdown = $('.company-dropdown');
			let $projectdropdown = $('.project-dropdown');
			let $sitedropdown = $('.site-dropdown');
			let $shiftdropdown = $('.shift-dropdown');
			let $departmentdropdown = $('.department-dropdown');
			let $designationdropdown = $('.designation-dropdown');
			company.forEach(function (element) {
				let companies = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
				$companydropdown.append(companies);
			});
			projects.forEach(function (element) {
				let project = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
				$projectdropdown.append(project);
			});
			sites.forEach(function (element) {
				let site = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
				$sitedropdown.append(site);
			});
			shifts.forEach(function (element) {
				let shift = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
				$shiftdropdown.append(shift);
			});
			departments.forEach(function (element) {
				let department = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
				$departmentdropdown.append(department);
			});
			designations.forEach(function (element) {
				let designation = `<a class="dropdown-item filteronserviceboard">${element.name}</a>`;
				$designationdropdown.append(designation);
			});

			/*dropdown for assign set text on hide show clear filter text*/
			$(".customredropdown .customdropdownheight .dropdown-item").click(function () {
				let text = $(this).html();
				let filter_type = $(this).parent().attr('data-filter-type');
				$(this).closest(".btn-group").find(".dropdown-toggle .dropdowncustomres").html(text);
				if (filter_type == "assigned") {
					cur_page.page.page.filters[filter_type] = text == "Assigned" ? 1 : 0;
				} else {
					cur_page.page.page.filters[filter_type] = text;
				}
				if (text === "Assigned") {

					$(".hideshowprjname").addClass("d-none");
					// $(".btnunassignonclick").removeClass("d-block").addClass("d-none");
					// $(".rostercustomstafftab").removeClass("d-none").addClass("d-flex");
				}
				else {

					$(".hideshowprjname").removeClass("d-none");
					// $(".btnunassignonclick").removeClass("d-none").addClass("d-block");
					// $(".rostercustomstafftab").addClass("d-none").removeClass("d-flex");
				}
				render_staff($(".layoutSidenav_content").attr("data-view"));
			});
			/*dropdown for assign set text on hide show clear filter text*/
		});
}

function ClearServiceBoard(e) {
	let filter_type = $(e).attr('data-filter-type');
	let filter_text = filter_type.charAt(0).toUpperCase() + filter_type.slice(1);
	$(e).closest(".btn-group").find(".dropdown-toggle .dropdowncustomres").html(filter_text);
	cur_page.page.page.filters[filter_type] = '';
	render_staff($(".layoutSidenav_content").attr("data-view"));
}

function staff_edit_dialog() {
	let employees = [];
	if ($(".layoutSidenav_content").attr("data-view") == "list") {
		employees = $(".datatablecjeckbox:checked").map(function () {
			return $(this).attr("data-employee-id");
		}).get();
	} else if ($(".layoutSidenav_content").attr("data-view") == "card") {
		employees = $(".cardviewcheckbox:checked").map(function () {
			return $(this).attr("data-employee-id");
		}).get();
	}

	let d = new frappe.ui.Dialog({
		'title': 'Edit',
		'fields': [
			{
				'label': 'Project', 'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', get_query: function () {
					return {
						"filters": {
							"project_type": "External"
						},
						"page_len": 9999
					};
				}
			},
			{
				'label': 'Site', 'fieldname': 'site', 'fieldtype': 'Link', 'options': 'Operations Site', get_query: function () {
					let project = d.get_value('project');
					if (project) {
						return {
							"filters": { project },
							"page_len": 9999
						};
					}
				}
			},
			{
				'label': 'Shift', 'fieldname': 'shift', 'fieldtype': 'Link', 'options': 'Operations Shift', 'reqd': 1, get_query: function () {
					let site = d.get_value('site');
					if (site) {
						return {
							"filters": { site },
							"page_len": 9999
						};
					}
				},

				onchange: function () {
					let name = d.get_value('shift');
					if (name) {
						frappe.db.get_value("Operations Shift", name, ["site", "project"])
							.then(res => {
								let { site, project } = res.message;
								d.set_value('site', site);
								d.set_value('project', project);
							});
					}
				}
			},
			{'label': 'Request Employee Assignment', 'fieldname': 'request_employee_assignment', 'fieldtype': 'Check'},
		],
		primary_action: function () {
			let { shift, request_employee_assignment } = d.get_values();

			$('#cover-spin').show(0);
			frappe.call({
				method: 'one_fm.one_fm.page.roster.roster.assign_staff',
				args: { employees, shift, request_employee_assignment},
				callback: function (r) {
					d.hide();
					$('#cover-spin').hide();
					update_staff_view();
					frappe.msgprint(__("Successful!"));
					// render_staff($(".layoutSidenav_content").attr("data-view"));
				},
				freeze: true,
				freeze_message: __('Editing Post....')
			});
		}
	});
	d.show();
}

function update_staff_view() {
	frappe.realtime.on("staff_view", function (output) {
		console.log(output, typeof (output));
		render_staff($(".layoutSidenav_content").attr("data-view"));
	});
}

//function for dynamic set calender header data on right calender
function GetWeekHeaders(IsMonthSet, element) {
	var thHTML = "";
	var thStartHTML = `<th class="sticky vertical-sticky">Post Type / Days</th>`;
	var thEndHTML = `<th class="vertical-sticky">Total</th>`;
	var selectedMonth;
	element = get_wrapper_element(element);
	(element);
	if (IsMonthSet == 0) {
		var today = new Date();
		// var firstDay = weekCalendarSettings.date.startOf("week").date();
		// var endofday = weekCalendarSettings.date.endOf("week").date();
		// (firstDay, endofday);
		var firstDay = new Date(startOfWeek(today));
		var lastDay = new Date(today.getFullYear(), today.getMonth() + 1, today.getDate() + 6);
		var lastDate = moment(lastDay);
		var getdateres = moment(new Date()).format("DD");

		var dataHTML = "";
		var calDate = moment(new Date(firstDay));//moment(new Date(firstDay.getFullYear(), firstDay.getMonth(), i));
		for (var i = 1; i <= 7; i++) {

			// var calDate = moment(new Date(firstDay.getFullYear(), firstDay.getMonth(), i));
			var todayDay = calDate.format("ddd");
			var weekNumber = getWeekOfMonth(calDate.toDate());
			var todayDaydate = calDate.format("DD");

			var th = "";
			if (todayDay == 'Fri' || todayDay == 'Sat') {
				th = `<th class="greytablebg vertical-sticky" id="data-day_${i}" onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			else if (todayDaydate === getdateres) {
				th = `<th class="hightlightedtable vertical-sticky" id="data-day_${i}" onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			else {
				th = `<th class=" vertical-sticky" id="data-day_${i}"  onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
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
				th = `<th class="greytablebg vertical-sticky" id="data-day_${i}" onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			else {
				th = `<th class=" vertical-sticky" id="data-day_${i}"  onclick="ChangeRosteringDate(${i} ,this)"> ${calDate.format("ddd") + " " + calDate.format("DD")}</th>`;
			}
			dataHTML = dataHTML + th;

			calDate = calDate.add(1, "Days");
		}
		thHTML = thStartHTML + dataHTML + thEndHTML;
		selectedMonth = today.getMonth();
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
	GetWeekHeaders(1);
	displayWeekCalendar(weekCalendarSettings);
	let element = get_wrapper_element().slice(1);
	if (element == "rosterWeek") {
		get_roster_week_data(cur_page.page.page);
	} else {
		get_post_week_data(cur_page.page.page);
	}
}
//on next month title display on arrow click

//on previous month title display on arrow click
function rosterweekdecrement() {
	weekCalendarSettings.date.subtract(1, "Weeks"); //.subtract(7, "days");
	GetWeekHeaders(1);
	displayWeekCalendar(weekCalendarSettings);
	let element = get_wrapper_element().slice(1);
	if (element == "rosterWeek") {
		get_roster_week_data(cur_page.page.page);
	} else {
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
	let startcalendarmonth = weekCalendarSettings.date.startOf("week").format("MMM");
	let endcalendarmonth = weekCalendarSettings.date.endOf("week").format("MMM");
	let calendaryear = weekCalendarSettings.date.format("YYYY");
	let startofday, endofday;
	console.log(page.start_date, page.end_date);
	if (page.start_date) {
		startofday = moment(page.start_date, 'YYYY-MM-DD').startOf("week").date();
		endofday = moment(page.start_date, 'YYYY-MM-DD').endOf("week").date();
		page.start_date = moment(page.start_date, 'YYYY-MM-DD').startOf("week").format('YYYY-MM-DD');
		page.end_date = moment(page.start_date, 'YYYY-MM-DD').endOf("week").format('YYYY-MM-DD');
		startcalendarmonth = moment(page.start_date, 'YYYY-MM-DD').startOf("week").format("MMM");
		endcalendarmonth = moment(page.start_date, 'YYYY-MM-DD').endOf("week").format("MMM");
	} else {
		startofday = weekCalendarSettings.date.startOf("week").date();
		endofday = weekCalendarSettings.date.endOf("week").date();
		page.start_date = weekCalendarSettings.date.startOf("week").format('YYYY-MM-DD');
		page.end_date = weekCalendarSettings.date.endOf("week").format('YYYY-MM-DD');
	}

	weekcalendar.innerHTML = "";
	weekcalendar.innerHTML = "Month of <span> " + startcalendarmonth + "</span> <span> " + startofday + "</span> - <span> " + endcalendarmonth + " </span> <span> " + endofday + "</span>, " + calendaryear + "";
}

function unschedule_staff(page) {
	let employees = [];
	let selected = [... new Set(classgrt)];
	selected.forEach(function (i) {
		let [employee, date] = i.split("|");
		employees.push({ employee, date });
	});
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let d = new frappe.ui.Dialog({
		'title': 'Unschedule Staff',
		'fields': [
			{
				'label': 'Start Date', 'fieldname': 'start_date', 'fieldtype': 'Date', 'reqd': 1, 'default': date, onchange: function () {
					let start_date = d.get_value('start_date');
					if (start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						frappe.throw(__("Start Date cannot be before today."));
					}
				}
			},
			{ 'fieldtype': 'Section Break' },
			{
				'label': 'Never End', 'fieldname': 'never_end', 'fieldtype': 'Check', onchange: function () {
					let val = d.get_value('never_end');
					if (val) {
						d.set_value('select_end', 0);
					}
				}
			},
			{ 'fieldtype': 'Column Break' },
			{
				'label': 'Select End Date', 'fieldname': 'select_end', 'fieldtype': 'Check', onchange: function () {
					let val = d.get_value('select_end');
					if (val) {
						d.set_value('never_end', 0);
					}
				}
			},
			{ 'fieldtype': 'Section Break', 'depends_on': "eval:this.get_value('select_end') == 1" },
			{
				'label': 'End Date', 'fieldname': 'end_date', 'fieldtype': 'Date', 'default': date, onchange: function () {
					let end_date = d.get_value('end_date');
					let start_date = d.get_value('start_date');
					if (end_date && moment(end_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						frappe.throw(__("End Date cannot be before today."));
					}
					if (start_date && end_date && moment(end_date).isBefore(moment(frappe.datetime.nowdate()))) {
						frappe.throw(__("End Date cannot be before Start Date."));
					}
				}
			}
		],
		primary_action: function () {
			$('#cover-spin').show(0);
			let { start_date, end_date, never_end } = d.get_values();
			frappe.xcall('one_fm.one_fm.page.roster.roster.unschedule_staff',
				{ employees, start_date, end_date, never_end })
				.then(res => {
					d.hide();
					$('#cover-spin').hide();
					let element = get_wrapper_element().slice(1);
					page[element](page);
				});
		}
	});
	d.show();
}

function schedule_leave(page) {
	let employees = [];
	let selected = [... new Set(classgrt)];
	selected.forEach(function (i) {
		let [employee, date] = i.split("|");
		employees.push({ employee, date });
	});
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let d = new frappe.ui.Dialog({
		'title': 'Leaves',
		'fields': [
			{ 'label': 'Type of Leave', 'fieldname': 'leave_type', 'fieldtype': 'Select', 'reqd': 1, 'options': '\nSick Leave\nAnnual Leave\nEmergency Leave' },
			{
				'label': 'Start Date', 'fieldname': 'start_date', 'fieldtype': 'Date', 'reqd': 1, 'default': date, onchange: function () {
					let start_date = d.get_value('start_date');
					if (start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						// d.set_value('start_date', frappe.datetime.add_days(moment(frappe.datetime.nowdate()), '1'));
						frappe.throw(__("Start Date cannot be before today."));
					}
				}
			},
			{
				'label': 'End Date', 'fieldname': 'end_date', 'fieldtype': 'Date', 'reqd': 1, 'default': date, onchange: function () {
					let end_date = d.get_value('end_date');
					let start_date = d.get_value('start_date');
					if (end_date && moment(end_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						// d.set_value('end_date', undefined);
						frappe.throw(__("End Date cannot be before today."));
					}
					if (start_date && end_date && moment(end_date).isBefore(moment(frappe.datetime.nowdate()))) {
						// d.set_value('end_date', undefined);
						frappe.throw(__("End Date cannot be before Start Date."));
					}
				}
			}
		],
		primary_action: function () {
			$('#cover-spin').show(0);
			let { leave_type, start_date, end_date } = d.get_values();
			frappe.xcall('one_fm.one_fm.page.roster.roster.schedule_leave',
				{ employees, leave_type, start_date, end_date })
				.then(res => {
					d.hide();
					$('#cover-spin').hide();
					let element = get_wrapper_element().slice(1);
					page[element](page);
				});
		}
	});
	d.show();
}

function change_post(page) {
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let d = new frappe.ui.Dialog({
		'title': 'Change Post',
		'fields': [
			{
				'label': 'Choose Post Type', 'fieldname': 'post_type', 'fieldtype': 'Link', 'options': 'Post Type', 'reqd': 1, get_query: function () {
					// return {
					// 	// "filters": { 
					// 	// 	"project_type": "External"							
					// 	// },
					// 	"page_len": 9999
					// };
				}
			},
		],
		primary_action: function () {
			d.hide();
			let element = get_wrapper_element().slice(1);
			page[element](page);

		}
	});
	d.show();
}

function schedule_change_post(page) {
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let employees = [];
	let selected = [... new Set(classgrt)];
	let otRoster = false;
	if (selected.length > 0) {
		selected.forEach(function (i) {
			let [employee, date] = i.split("|");
			employees.push(employee);
			employees = [... new Set(employees)];
		});
	}
	let d = new frappe.ui.Dialog({
		'title': 'Schedule/Change Post',
		'fields': [
			{
				'label': 'Shift', 'fieldname': 'shift', 'fieldtype': 'Link', 'options': 'Operations Shift', 'reqd': 1, onchange: function () {
					let name = d.get_value('shift');
					if (name) {
						frappe.db.get_value("Operations Shift", name, ["site", "project"])
							.then(res => {
								let { site, project } = res.message;
								d.set_value('site', site);
								d.set_value('project', project);
							});
					}
				}
			},
			{ 'label': 'Site', 'fieldname': 'site', 'fieldtype': 'Link', 'options': 'Operations Site', 'read_only': 1 },
			{ 'label': 'Project', 'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', 'read_only': 1 },
			{
				'label': 'Choose Post Type', 'fieldname': 'post_type', 'fieldtype': 'Link', 'reqd': 1, 'options': 'Post Type', get_query: function () {
					return {
						query: "one_fm.one_fm.page.roster.roster.get_filtered_post_types",
						filters: { "shift": d.get_value('shift') }
					};
				}
			},
			{ 'fieldname': 'cb1', 'fieldtype': 'Section Break' },
			{
				'label': 'From Date', 'fieldname': 'start_date', 'fieldtype': 'Date', 'default': date, onchange: function () {
					let start_date = d.get_value('start_date');
					if (start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						// d.set_value('start_date', frappe.datetime.add_days(moment(frappe.datetime.nowdate()), '1'));
						frappe.throw(__("Start Date cannot be before today."));
					}
				}
			},
			{ 'label': 'Project End Date', 'fieldname': 'project_end_date', 'fieldtype': 'Check' },
			{ 'label': 'Keep Days Off', 'fieldname': 'keep_days_off', 'fieldtype': 'Check' },
			{ 'label': 'Request Employee Schedule', 'fieldname': 'request_employee_schedule', 'fieldtype': 'Check' },
			{ 'fieldname': 'cb1', 'fieldtype': 'Column Break' },
			{
				'label': 'Till Date', 'fieldname': 'end_date', 'fieldtype': 'Date', 'depends_on': 'eval:this.get_value("project_end_date")==0', onchange: function () {
					let end_date = d.get_value('end_date');
					let start_date = d.get_value('start_date');
					if (end_date && moment(end_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						frappe.throw(__("End Date cannot be before today."));
					}
					if (start_date && end_date && moment(end_date).isBefore(moment(frappe.datetime.nowdate()))) {
						frappe.throw(__("End Date cannot be before Start Date."));
					}
				}
			},
		],
		primary_action: function () {

			let { shift, site, post_type, project, start_date, project_end_date, keep_days_off, end_date, request_employee_schedule } = d.get_values();
			$('#cover-spin').show(0);
			let element = get_wrapper_element();
			if (element == ".rosterOtMonth") {
				otRoster = true;
			} else if (element == ".rosterMonth") {
				otRoster = false;
			}
			frappe.xcall('one_fm.one_fm.page.roster.roster.schedule_staff',
				{ employees, shift, post_type, otRoster, start_date, project_end_date, keep_days_off, request_employee_schedule, end_date })
				.then(res => {
					d.hide();
					$('#cover-spin').hide();
					let element = get_wrapper_element().slice(1);
					update_roster_view(element, page);
				}).catch(e => {
					console.log(e);
					$('#cover-spin').hide();
				});
		}
	});
	d.show();
}
function update_roster_view(element, page) {
	page[element](page);
	frappe.realtime.on("roster_view", function (output) {
		// message = JSON.parse(output);
		console.log(output);
		page[element](page);
	});
}
function paginateTable(page) {
	$.fn.pageMe = function (opts) {
		var $this = this,
			defaults = {
				perPage: 100,
				showPrevNext: false,
				hidePageNumbers: false
			},
			settings = $.extend(defaults, opts);

		var listElement = $this;
		var perPage = settings.perPage;
		var children = listElement.children();
		let wrapper_element = $(get_wrapper_element());
		var pager = wrapper_element.find('.pager');
		console.log(listElement, children, pager);
		if (typeof settings.childSelector != "undefined") {
			children = listElement.find(settings.childSelector);
		}

		if (typeof settings.pagerSelector != "undefined") {
			pager = wrapper_element.find(settings.pagerSelector);
		}

		// var numItems = children.size();
		var numItems = page.pagination.total;
		var numPages = Math.ceil(numItems / perPage);

		pager.data("curr", 0);
		$(pager).empty();
		if (settings.showPrevNext) {
			$('<li><a href="#" class="prev_link">«</a></li>').appendTo(pager);
		}

		var curr = 0;

		while (numPages > curr && (settings.hidePageNumbers == false)) {
			$('<li><a href="#" class="page_link">' + (curr + 1) + '</a></li>').appendTo(pager);
			curr++;
		}

		if (settings.showPrevNext) {
			$('<li><a href="#" class="next_link">»</a></li>').appendTo(pager);
		}

		// pager.find('.page_link:first').addClass('active');
		pager.find('.prev_link').hide();
		if (numPages <= 1) {
			pager.find('.next_link').hide();
		}
		// pager.children().eq(1).addClass("active");
		let active_page = (page.pagination.limit_start / page.pagination.limit_page_length);
		pager.children().eq(active_page).addClass("active");

		children.hide();
		children.slice(0, perPage).show();
		pager.find('li .page_link').click(function () {
			var clickedPage = $(this).html().valueOf() - 1;
			let limit_start = ((clickedPage + 1) * 100) - 100;
			console.log(clickedPage, limit_start);
			page.pagination.limit_start = limit_start;
			// goTo(clickedPage,perPage);
			let element = get_wrapper_element().slice(1);
			page[element](page);
			return false;
		});
		pager.find('li .prev_link').click(function () {
			let start = page.pagination.current + 1;
			let page_len = 100;
			previous();
			return false;
		});
		pager.find('li .next_link').click(function () {
			let start = page.pagination.current + 1;
			let page_len = 100;
			next();
			return false;
		});

		function previous() {
			var goToPage = parseInt(pager.data("curr")) - 1;
			goTo(goToPage);
		}

		function next() {
			goToPage = parseInt(pager.data("curr")) + 1;
			goTo(goToPage);
		}

		function goTo(page) {
			var startAt = page * perPage,
				endOn = startAt + perPage;

			children.css('display', 'none').slice(startAt, endOn).show();

			if (page >= 1) {
				pager.find('.prev_link').show();
			}
			else {
				pager.find('.prev_link').hide();
			}

			if (page < (numPages - 1)) {
				pager.find('.next_link').show();
			}
			else {
				pager.find('.next_link').hide();
			}

			pager.data("curr", page);
			pager.children().removeClass("active");
			pager.children().eq(page + 1).addClass("active");

		}
	};
}

function dayoff(page) {
	let employees = [];
	let selected = [... new Set(classgrt)];
	selected.forEach(function (i) {
		let [employee, date] = i.split("|");
		employees.push({ employee, date });
	});
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let d = new frappe.ui.Dialog({
		'title': 'Day Off',
		'fields': [
			{ 'label': 'Selected days only', 'fieldname': 'selected_dates', 'fieldtype': 'Check', 'default': 0 },
			{ 'label': 'Repeat', 'fieldname': 'repeat', 'fieldtype': 'Select', 'depends_on': 'eval:this.get_value("selected_dates")==0', 'options': 'Does not repeat\nDaily\nWeekly\nMonthly\nYearly' },
			{ 'fieldtype': 'Section Break', 'fieldname': 'sb1', 'depends_on': 'eval:this.get_value("repeat")=="Weekly" && this.get_value("selected_dates")==0' },
			{ 'label': 'Sunday', 'fieldname': 'sunday', 'fieldtype': 'Check' },
			{ 'label': 'Wednesday', 'fieldname': 'wednesday', 'fieldtype': 'Check' },
			{ 'label': 'Saturday', 'fieldname': 'saturday', 'fieldtype': 'Check' },
			{ 'fieldtype': 'Column Break', 'fieldname': 'cb1' },
			{ 'label': 'Monday', 'fieldname': 'monday', 'fieldtype': 'Check' },
			{ 'label': 'Thursday', 'fieldname': 'thursday', 'fieldtype': 'Check' },
			{ 'fieldtype': 'Column Break', 'fieldname': 'cb2' },
			{ 'label': 'Tuesday', 'fieldname': 'tuesday', 'fieldtype': 'Check' },
			{ 'label': 'Friday', 'fieldname': 'friday', 'fieldtype': 'Check' },
			{ 'fieldtype': 'Section Break', 'fieldname': 'sb2', 'depends_on': 'eval:this.get_value("selected_dates")==0' },
			{ 'label': 'Repeat Till', 'fieldtype': 'Date', 'fieldname': 'repeat_till', 'depends_on': 'eval:this.get_value("repeat")!= "Does not repeat" && this.get_value("project_end_date")==0' },
			{'label': 'Project End Date', 'fieldname': 'project_end_date', 'fieldtype': 'Check' },
		],
		primary_action: function () {
			$('#cover-spin').show(0);
			let week_days = [];
			let args = {};
			let repeat_freq = '';
			let { selected_dates, repeat, sunday, monday, tuesday, wednesday, thursday, friday, saturday, repeat_till, project_end_date } = d.get_values();
			args["selected_dates"] = selected_dates;
			args["employees"] = employees;

			if (selected_dates == 1) {
				args["repeat"] = 0;
			}

			if (!selected_dates && repeat !== "Does not repeat") {
				args["repeat"] = 1;
				args["repeat_till"] = repeat_till;
				args["project_end_date"] = project_end_date

				if (repeat == "Weekly") {
					repeat_freq = "Weekly";
					sunday ? week_days.push("Sunday") : '';
					monday ? week_days.push("Monday") : '';
					tuesday ? week_days.push("Tuesday") : '';
					wednesday ? week_days.push("Wednesday") : '';
					thursday ? week_days.push("Thursday") : '';
					friday ? week_days.push("Friday") : '';
					saturday ? week_days.push("Saturday") : '';
					args["week_days"] = week_days;
					args["repeat_freq"] = repeat_freq;
				}
				else if (repeat == "Daily") {
					repeat_freq = "Daily";
					args["repeat_freq"] = repeat_freq;
				}
				else if (repeat == "Monthly") {
					repeat_freq = "Monthly";
					args["repeat_freq"] = repeat_freq;
				}
				else if (repeat == "Yearly") {
					repeat_freq = "Yearly";
					args["repeat_freq"] = repeat_freq;
				}
			}
			console.log(args);
			frappe.xcall('one_fm.one_fm.page.roster.roster.dayoff', args)
				.then(res => {
					d.hide();
					$('#cover-spin').hide();
					let element = get_wrapper_element().slice(1);
					page[element](page);
				}).catch(e => {
					console.log(e);
					$('#cover-spin').hide();
				});
		}
	});
	d.show();
}