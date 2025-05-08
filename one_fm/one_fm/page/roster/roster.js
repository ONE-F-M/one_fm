// Frappe Init function to render Roster
frappe.pages['roster'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Roster',
		single_column: true
	});
	$('#page-roster').empty().append(frappe.render_template('roster'));

	load_js(page);

	$(".mobile-edit").on("click", function () {
		;
	})


};



// Initializes the page with default values
function load_js(page) {
	$(this).scrollTop(0);

	window.clickcount = 0;
	window.employees_list = [];
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
		$postWeek = $('.postWeek');

		function basicRosterClick() {
			window.isOt = false;
			$(".otRosterClick").removeClass("active");
			$(".otRosterClick").removeClass("bg-primary");
			$(".basicRosterClick").addClass("active");
			$(".basicRosterClick").addClass("bg-primary");
			$rosterMonth.removeClass("d-none");
			$rosterOtMonth.addClass("d-none");
			$(".switch-container").removeClass("d-none");
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".rosterMonth");
			get_roster_data(page);
		};
		function otRosterClick() {
			window.isOt = true;
			$(".basicRosterClick").removeClass("active");
			$(".basicRosterClick").removeClass("bg-primary");
			$(".otRosterClick").addClass("active");
			$(".otRosterClick").addClass("bg-primary");
			$(".filterhideshow").addClass("d-none");
			$rosterMonth.addClass("d-none");
			$rosterOtMonth.removeClass("d-none");
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
			$("#rosterTypeButtons").removeClass("d-none");
			$("#rosterTypeButtons").addClass("d-flex");
			$rosterMonth.removeClass("d-none");
			$rosterOtMonth.addClass("d-none");
			$postMonth.addClass("d-none");
			$postWeek.addClass("d-none");
			$(".postviewclick").removeClass("active");
			$(".postviewclick").removeClass("bg-primary");
			$(".rosterviewclick").addClass("active");
			$(".rosterviewclick").addClass("bg-primary");
			$(".switch-container").removeClass("d-none");
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
			$("#rosterTypeButtons").removeClass("d-flex");
			$("#rosterTypeButtons").addClass("d-none");
			$(".basicRosterClick").off('click');
			$(".otRosterClick").off('click');
			$rosterMonth.addClass("d-none");
			$rosterOtMonth.addClass("d-none");
			$postMonth.removeClass("d-none");
			$postWeek.addClass("d-none");
			$(".postviewclick").addClass("active");
			$(".postviewclick").addClass("bg-primary");
			$(".rosterviewclick").removeClass("active");
			$(".rosterviewclick").removeClass("bg-primary");
			$(".switch-container").addClass("d-none");
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
			$postWeek.addClass("d-none");
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".postMonth");
			get_post_data(page);
		});
		$('.monthviewclick').click(function () {
			$rosterMonth.removeClass("d-none");
			$postMonth.addClass("d-none");
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
							depends_on: "eval:doc.post_status == 'Plan Post'",
						},
						{
							label: 'Plan From Date',
							fieldname: 'plan_from_date',
							fieldtype: 'Date',
							default: date
						},
						{
							label: 'Plan Till Date',
							fieldname: 'plan_end_date',
							fieldtype: 'Date',
							depends_upon: 'eval:doc.project_end_date==0',
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
							depends_on: "eval:doc.post_status == 'Cancel Post'",
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
							depends_upon: 'eval:doc.project_end_date==0',
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
							depends_on: "eval:doc.post_status == 'Post Off'",
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
							fieldname: 'sb5',
							fieldtype: 'Section Break',
							depends_on: "eval:doc.post_status == 'Post Off'",
						},
						{
							label: 'Post Off From Date',
							fieldname: 'post_off_from_date',
							fieldtype: 'Date',
							default: date
						},
						{ label: 'Repeat', fieldname: 'repeat', fieldtype: 'Select', options: 'Does not repeat\nSelected Days Only\nDaily\nWeekly\nMonthly\nYearly' },
						{ 'fieldtype': 'Section Break', 'fieldname': 'sb1', 'depends_on': 'eval:doc.post_status=="Post Off" && doc.repeat=="Weekly"' },
						{ 'label': 'Sunday', 'fieldname': 'sunday', 'fieldtype': 'Check' },
						{ 'label': 'Wednesday', 'fieldname': 'wednesday', 'fieldtype': 'Check' },
						{ 'label': 'Saturday', 'fieldname': 'saturday', 'fieldtype': 'Check' },
						{ 'fieldtype': 'Column Break', 'fieldname': 'cb1' },
						{ 'label': 'Monday', 'fieldname': 'monday', 'fieldtype': 'Check' },
						{ 'label': 'Thursday', 'fieldname': 'thursday', 'fieldtype': 'Check' },
						{ 'fieldtype': 'Column Break', 'fieldname': 'cb2' },
						{ 'label': 'Tuesday', 'fieldname': 'tuesday', 'fieldtype': 'Check' },
						{ 'label': 'Friday', 'fieldname': 'friday', 'fieldtype': 'Check' },
						{ 'fieldtype': 'Section Break', 'fieldname': 'sb2', 'depends_on': 'eval:doc.post_status=="Post Off" && doc.repeat!= "Does not repeat" && doc.repeat!= "Selected Days Only"' },
						{ 'label': 'Repeat Till', 'fieldtype': 'Date', 'fieldname': 'repeat_till', 'depends_upon': 'eval:doc.project_end_date==0' },
						{
							fieldname: 'sb2',
							fieldtype: 'Section Break',
							depends_on: "eval:doc.post_status == 'Suspend Post'",
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
							depends_on: 'eval:doc.project_end_date==0',
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

								if (r.status_code == 200) {
									frappe.msgprint(r.data.message);

									setTimeout(() => {
										frappe.hide_msgprint();
									}, 4000);
								}
							},
							freeze: true,
							freeze_message: __('Editing Post....')
						});
					}
				});

				d.show();
			}
			else{
				frappe.throw(frappe._("Insufficient permissions to Edit Post."));

			}
		});


		//check schedule staff on load
		$("#chkassgined").prop("checked", true);
		$("#chkassgined").trigger("change");


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
		//page.rosterWeek = get_roster_week_data;
		page.postWeek = get_post_week_data;
		page.postMonth = get_post_data;

	}


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

	setup_preset_filters(page)
}

function get_preset_filters () {
	const { main_view, sub_view, roster_type, staff_view_mode, employee_id, employee_name,...pageFilters } = frappe.utils.get_query_params();

	return {
		view: { main_view, sub_view, roster_type, staff_view_mode },
		employee: { employee_id, employee_name },
		page: pageFilters
	}
}

// Setup and populate preset filters set via query params
function setup_preset_filters (page) {
	// To avoid re-rendering of roster page
	if(window.preset_filters_applied) return

	const { view: viewFilters, page: pageFilters, employee: employeeFilters } = get_preset_filters()

	const { main_view: mainView, sub_view: subView, roster_type: rosterType, staff_view_mode: staffViewMode } = viewFilters

	if (mainView) {
		setTimeout(() => {
		  $("#page-roster")
			.find(`.redirect_route[data-route="${mainView}"]`)
			.click();
		}, 500);
	}

	function toggle_between_views() {
		if(mainView === 'roster') {
			if(subView === 'roster') {
				setTimeout(() => {
					$(".rosterviewclick").click()
				  }, 1000);
			}
			if(subView === 'post') {
				setTimeout(() => {
					$(".postviewclick").click()
				  }, 1000);
			}
			if(rosterType === 'basic') {
				setTimeout(() => {
					$(".basicRosterClick").click()
				  }, 1000);
			}
			if(rosterType === 'ot') {
				setTimeout(() => {
					$(".otRosterClick").click()
				  }, 1000);
			}
		}
	}

	function populate_values() {
		if (mainView === 'roster') {
			setTimeout(() => {
				const { employee_id: employeeID, employee_name: employeeName } = employeeFilters;

			    let wrapper_element = get_wrapper_element();
				if (employeeID) {
					$(wrapper_element).find(".search-employee-id").val(employeeID);
				}
			    if (employeeName) {
					$(wrapper_element).find(".search-employee-name").val(employeeName);
				}
			}, 1000);
		} else if (mainView === 'staff') {
			setTimeout(() => {
				const { company, project, site, shift, department, designation } = pageFilters;
			    if(company) $('.staff-company-dropdown').html(company)
			    if(project) $('.staff-project-dropdown').html(project)
			    if(site) $('.staff-site-dropdown').html(site)
			    if(shift) $('.staff-shift-dropdown').html(shift)
			    if(department) $('.staff-department-dropdown').html(department)
			    if(designation) $('.staff-designation-dropdown').html(designation)

				render_staff(staffViewMode || "list")
			}, 1000);
		}
	}

	toggle_between_views()
	populate_values()

	window.preset_filters_applied = true
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

	$('.clear_roster_filters').on('click', function () {
		clear_roster_filters(page);
	});

	$('.clear_staff_filters').on('click', function () {
		clear_staff_filters(page);
	});

	$('.clear_selection').on('click', function () {
		clear_selection(page);
	});

	$("#rosterEmployeeActions").on("click", function() {
		roster_employee_actions(page);
	});
}

//Bind events to Edit options in Roster/Post view
function bind_events(page) {
	let wrapper_element = $(get_wrapper_element());
	paginateTable(page);

	wrapper_element.find('#paginate-parent').pageMe({ pagerSelector: '#myPager', showPrevNext: false, hidePageNumbers: false, perPage: 9999 });
	if (["Operations Manager", "Site Supervisor", "Shift Manager", "Shift Supervisor", "Projects Manager"].some(i => frappe.user_roles.includes(i))) {
		let $rosterMonth = $('.rosterMonth');
		let $rosterOtMonth = $('.rosterOtMonth');
		let $postMonth = $('.postMonth');
		let $postWeek = $('.postWeek');
		$postMonth.find(".hoverselectclass").on("click", function () {
            // Loop through all rows and if there is a checked row, unselect all cells in that row.
            $(this).closest("tbody").children("tr").each(function (i, cell) {
                const checked_row = $(cell).find('input[name="selectallcheckbox"]:checked');
                if (checked_row.length > 0) {
                    $(checked_row).prop('checked', false);
                    $(cell).find("div").removeClass("selectclass");
                }
            });

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
            // Loop through all rows and if there is a checked row, unselect all cells in that row.
            $(this).closest("tbody").children("tr").each(function (i, cell) {
                const checked_row = $(cell).find('input[name="selectallcheckbox"]:checked');
                if (checked_row.length > 0) {
                    $(checked_row).prop('checked', false);
                    $(cell).find("div").removeClass("selectclass");
                }
            });

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
           // Loop through all rows and if there is a checked row, unselect all cells in that row.
           $(this).closest("tbody").children("tr").each(function (i, cell) {
                const checked_row = $(cell).find('input[name="selectallcheckbox"]:checked');
                if (checked_row.length > 0) {
                    $(checked_row).prop('checked', false);
                    $(cell).find("div").removeClass("selectclass");
                }
            });

            // select cell
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
            // Loop through all rows and if there is a checked row, unselect all cells in that row.
            $(this).closest("tbody").children("tr").each(function (i, cell) {
                const checked_row = $(cell).find('input[name="selectallcheckbox"]:checked');
                if (checked_row.length > 0) {
                    $(checked_row).prop('checked', false);
                    $(cell).find("div").removeClass("selectclass");
                }
            });

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


		/*on checkbox select change*/
		$postWeek.find(`input[name="selectallcheckbox"]`).on("change", function () {
            let $checked_employee = $(this);
            let selected_employee = $checked_employee.parent().parent().parent().attr('data-name');
			if ($checked_employee.is(":checked")) {
				$checked_employee.parent().parent().parent().children("td").children().not("label").each(function (i, v) {
					let date = $(v).attr('data-date');
					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
					}
				});
				$checked_employee.parent().parent().parent().children("td").children().not("label").removeClass("hoverselectclass");
				$(".Postfilterhideshow").removeClass("d-none");

			}
			else {
				$checked_employee.parent().parent().parent().children("td").children().not("label").addClass("hoverselectclass");
				$checked_employee.closest('tr').children("td").children().not("label").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr('data-selectid')), 1);
				});
				$checked_employee.parent().parent().parent().children("td").children().not("label").removeClass("selectclass");
				$(".Postfilterhideshow").addClass("d-none");
			}

            // Check for rows that are not selected full and unselect cells in that row.
            $checked_employee.closest("tbody").children("tr").each(function (i, cell) {
                const unchecked_row = $(cell).find('input[name="selectallcheckbox"]:not(:checked)');
                if (unchecked_row.length > 0) {
                    $(cell).find("div").removeClass("selectclass");
                }
            });

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

            // Check for rows that are not selected full and unselect cells in that row.
            $(this).closest("tbody").children("tr").each(function (i, cell) {
                const unchecked_row = $(cell).find('input[name="selectallcheckbox"]:not(:checked)');
                if (unchecked_row.length > 0) {
                    $(cell).find("div").removeClass("selectclass");
                }
            });


			$(".selectclass").map(function () {

				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];
			});
		});

		//on checkbox select change
        $rosterMonth.find(`input[name="selectallcheckbox"]`).on("change", function () {
            let $checked_employee = $(this);
            let selected_employee = $checked_employee.parent().parent().parent().attr('data-name');

			//Show Day Off and Schedule Leave button if hidden for basic roster
			if ($(".dayoff").is(":hidden")) {
				$(".dayoff").show();
			}
			if ($(".scheduleleave").is(":hidden")) {
				$(".scheduleleave").show();
			}

			if ($checked_employee.is(":checked")) {
                $checked_employee.closest('tr').children("td").children().not("label").each(function (i, v) {

					let [employee, date] = $(v).attr('data-selectid').split('|');
					classgrt.push($(v).attr('data-selectid'));
					var r = Date.parse(date)


					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
					}

				});
				$(".filterhideshow").removeClass("d-none");
			}
			else {
				$checked_employee.closest('tr').children("td").children().not("label").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr('data-selectid')), 1);
				});
				$checked_employee.closest('tr').children("td").children().not("label").removeClass("selectclass");
				$(".filterhideshow").addClass("d-none");
			}

            // Check for rows that are not selected full and unselect cells in that row.
            $checked_employee.closest("tbody").children("tr").each(function (i, cell) {
                const unchecked_row = $(cell).find('input[name="selectallcheckbox"]:not(:checked)');
                if (unchecked_row.length > 0) {
                    $(cell).find("div").removeClass("selectclass");
                }
            });;


			$(".selectclass").map(function () {
				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];
			});
		});
		$rosterOtMonth.find(`input[name="selectallcheckbox"]`).on("change", function () {
            let $checked_employee = $(this);

			//Hide Day Off and schedule leave button for OT Roster
			$(".dayoff").hide();
			$(".scheduleleave").hide();
			if ($(this).is(":checked")) {
				$(this).closest('tr').children("td").children().not("label").each(function (i, v) {

					let [employee, date] = $(v).attr('data-selectid').split('|');
					var r = Date.parse(date)

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

            // Check for rows that are not selected full and unselect cells in that row.
            $(this).closest("tbody").children("tr").each(function (i, cell) {
                const unchecked_row = $(cell).find('input[name="selectallcheckbox"]:not(:checked)');
                if (unchecked_row.length > 0) {
                    $(cell).find("div").removeClass("selectclass");
                }
            });

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

	window.employees_list = [];
	bind_search_bar_event(page);

	// manage employee selection

	$('.checkboxcontainer.simplecheckbox').click((e)=>{
		if(window.clickcount>0){
			window.clickcount = 0;
		} else {
			let employee = e.target.parentNode.parentNode.parentNode.getAttributeNode('data-name').value;
			if(window.employees_list.includes(employee)){
				window.employees_list = window.employees_list.filter(function(value, index, arr){
					return value != employee;
				});
			} else {
				window.employees_list.push(employee);
			}
			window.clickcount = window.clickcount + 1
		}

	})


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
	if (window.isOt) {isOt = true;}
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
	let { project, site, shift, department, operations_role, designation, relievers } = page.filters;
	let { limit_start, limit_page_length } = page.pagination;
	if (project || site || shift || department || operations_role || designation || relievers){
		$(".clear_roster_filters").removeClass("d-none")
		$('#cover-spin').show(0);
		frappe.call({
			method: "one_fm.one_fm.page.roster.roster.get_roster_view", //dotted path to server method
			type: "POST",
			args: { start_date, end_date, employee_search_id, employee_search_name, project, site,
				shift, department, operations_role, designation, relievers, isOt, limit_start, limit_page_length
			},
			callback: function(res) {
				// code snippet

				error_handler(res);
				render_roster(res.data, page, isOt);
			}
		});
	} else {
		$(".clear_roster_filters").addClass("d-none")
	}
}
// Function responsible for Rendering the Table
let classmap = {
	'Working': 'bluebox',
	'Day Off': 'greyboxcolor',
	'Sick Leave': 'purplebox',
	'Emergency Leave': 'purplebox',
	'Annual Leave': 'purplebox',
	'ASA': 'pinkboxcolor',
	'Day Off OT': 'yellowboxcolor'
};
let leavemap = {
	'Day Off': 'DO',
	'Sick Leave': 'SL',
	'Annual Leave': 'AL',
	'Emergency Leave': 'EL',
	'Leave Without Pay': 'LWP',
	'Working': '!'
};
let attendancemap = {
	'Present': 'greenboxcolor',
	'Absent': 'redboxcolor',
	'Work From Home': 'greenboxcolor',
	'Half Day': 'greenboxcolor',
	'On Leave': 'purplebox',
	"Holiday":"greyboxcolor",
	"On Hold": "orangeboxcolor"
};
let attendance_abbr_map = {
	'Present': 'P',
	'Absent': 'A',
	'Work From Home': 'WFH',
	'Half Day': 'HD',
	"Holiday":"H",
	'On Leave': 'OL',
	'On Hold': 'OH'
};

let reliever_data;

// Renders on get_roster_data function
function render_roster(res, page, isOt) {
	let { operations_roles_data, employees_data,reliever,total } = res;
	reliever_data =  reliever
	page.pagination.total = total;
	let $rosterMonth = isOt ? $('.rosterOtMonth') : $('.rosterMonth');
	let $rosterMonthbody = isOt ? $('.rosterOtMonth').find('#calenderviewtable tbody') : $('.rosterMonth').find('#calenderviewtable tbody');
	$rosterMonthbody.empty();
	for (operations_role_name in operations_roles_data) {
		let pt_row = `
		<tr class="colorclass scheduledStaff" data-name="${operations_role_name}">
			<td class="sticky">
				<div class="d-flex">
					<div class="font16 paddingdiv cursorpointer orangecolor">
						<i class="fa fa-plus" aria-hidden="true"></i>
					</div>
					<div class="font16 paddingdiv borderleft cursorpointer">
						${operations_role_name}
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
			let { date, operations_role, count, highlight } = operations_roles_data[operations_role_name][i];
			let pt_count = `
			<td class="${highlight}">
				<div class="text-center" data-selectid="${operations_role + "|" + date}">${count}</div>
			</td>`;
			$rosterMonth.find(`#calenderviewtable tbody tr[data-name='${escape_values(operations_role)}']`).append(pt_count);
			i++;
			start_date.add(1, 'days');
		}
		$rosterMonth.find(`#calenderviewtable tbody tr[data-name='${escape_values(operations_roles_data[operations_role_name][i - 1]["operations_role"])}']`).append(`<td></td>`);
	}

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
		// let { employee_name, employee, date } = employees_data[employee_key];


		let employee = employees_data[employee_key][0]['employee']
		let employee_id = employees_data[employee_key][0]['employee_id']
		let employee_day_off = employees_data[employee_key][0]['day_off_category']
		if(employees_data[employee_key][0]['number_of_days_off']){
			employee_day_off += " " + employees_data[employee_key][0]['number_of_days_off'] + " Day(s) off"
		}



		let emp_row = `
		<tr data-name="${employee}">
			<td class="sticky">
				<label class="checkboxcontainer simplecheckbox">
					<span class="lightgrey font16 customfontweight fontw400 postname" style="color:black">${employee_key}</span>
					<input type="checkbox" name="selectallcheckbox" class="selectallcheckbox">
					<span class="checkmark"></span>
				</label>
				<label >
					<span class="lightgrey employee_day_off"><span id="employee_id" style="color:black; font-size:13px">${employee_id}</span> - ${employee_day_off}</span>
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


			let { employee, employee_name, date, operations_role, post_abbrv, employee_availability, shift, start_datetime, end_datetime, start_time, end_time, actual_shift, roster_type, attendance, asa, day_off_ot,leave_type,leave_application,relieving_date } = employees_data[employee_key][i];
			//OT schedule view
			var r = Date.parse(date)
			let shift_start = moment(start_datetime, "YYYY-MM-DD HH:mm:ss").format("LT");
			let shift_end = moment(end_datetime, "YYYY-MM-DD HH:mm:ss").format("LT");
			start_time = moment(start_time, "HH:mm").format("LT");
			end_time = moment(end_time, "HH:mm").format("LT");

			if (isOt) {
				if ((actual_shift && shift) && (actual_shift!=shift) && roster_type == 'Over-Time' && day_off_ot==0) {

					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap['ASA']} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${shift}<br>Start: ${shift_start}<br>End: ${shift_end}</span></div>
					</td>`;
				} else if (post_abbrv && roster_type == 'Over-Time' && !asa && day_off_ot==0) {

					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${shift}<br>Start: ${shift_start}<br>End: ${shift_end}</span></div>
					</td>`;
				} else if(post_abbrv && roster_type == 'Over-Time' && asa && day_off_ot==0){

					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap['ASA']} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${"<strong>Scheduled:</strong> <br>" + shift + "<br>" + "<strong>Assigned:</strong> <br>" + asa}</span></div>
					</td>`;
				}else if(post_abbrv && roster_type == 'Over-Time' && day_off_ot==1){

					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap['Day Off OT']} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${shift}<br>Start: ${shift_start}<br>End: ${shift_end}</span></div>
					</td>`;
				}
				else if (employee_availability && !post_abbrv) {

					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center text-white so"
							data-selectid="${employee + "|" + date + "|" + employee_availability}">${leavemap[employee_availability]}</div>
					</td>`;
				} else if (attendance && !employee_availability) {

					if (attendance == 'Present') { j++; }
					sch = `
					<td>
						<div class="forbidden tablebox ${attendancemap[attendance]} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + attendance}">${attendance_abbr_map[attendance]}<span class="customtooltiptext">${leave_application ? leave_application+'|'+leave_type : shift+`<br>Start: ${start_time}<br>End: ${end_time}`}</span></div>
					</td>`;
				} else {

					if(moment(date)>=moment(relieving_date)){

						sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox darkblackox d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">EX<span class="customtooltiptext">Exited</span></div>
					</td>`;
					}
					else{

					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox borderbox d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date}"></div>
					</td>`;
					}
				}
				i++;
				start_date.add(1, 'days');
				$rosterMonth.find(`#rowchildtable tbody tr[data-name="${employee}"]`).append(sch);

			}
			//Basic schedule view
			else {

			 	if ((actual_shift && shift) && (actual_shift!=shift) && day_off_ot==0) {
									sch = `
				<td>
					<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap['ASA']} d-flex justify-content-center align-items-center text-white so customtooltip"
						data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${shift}<br>Start: ${shift_start}<br>End: ${shift_end}</span></div>
				</td>`;
				}
				else if (post_abbrv && roster_type == 'Basic' && !asa && day_off_ot==0) {

					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${shift}<br>Start: ${shift_start}<br>End: ${shift_end}</span></div>
					</td>`;
				}
				else if(post_abbrv && roster_type == 'Basic' && asa && day_off_ot==0){

					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap['ASA']} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${"<strong>Scheduled:</strong> <br>" + shift + "<br>" + "<strong>Assigned:</strong> <br>" + asa}</span></div>
					</td>`;
				}else if(post_abbrv && roster_type == 'Basic' && day_off_ot==1){

					j++;
					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap['Day Off OT']} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}<span class="customtooltiptext">${shift}<br>Start: ${shift_start}<br>End: ${shift_end}</span></div>
					</td>`;
				}
				else if (employee_availability && !post_abbrv) {

					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center text-white so"
							data-selectid="${employee + "|" + date + "|" + employee_availability}">${leavemap[employee_availability]}</div>
					</td>`;
				} else if (attendance && !employee_availability) {

					if(day_off_ot){
												sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox darkgreenbox d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + attendance}">${attendance_abbr_map[attendance]}<span class="customtooltiptext">${leave_application ? leave_application+'|'+leave_type : shift+`<br>Start: ${start_time}<br>End: ${end_time}`}</span></div>
					</td>`;
					}
					else{
												if (attendance == 'Present') {
															sch = `
						<td>
							<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${attendancemap[attendance]} d-flex justify-content-center align-items-center text-white so customtooltip"
								data-selectid="${employee + "|" + date + "|" + attendance}">${attendance_abbr_map[attendance]}<span class="customtooltiptext">${leave_application ? leave_application+'|'+leave_type : shift+`<br>Start: ${start_time}<br>End: ${end_time}`}</span></div>
						</td>`;
							j++;

						}
						else if (attendance == "On Leave"){
														sch = `
						<td>
							<div class="forbidden tablebox ${attendancemap[attendance]} d-flex justify-content-center align-items-center text-white so customtooltip"
								data-selectid="${employee + "|" + date + "|" + attendance}">${leavemap[leave_type]?leavemap[leave_type]:'LV'}<span class="customtooltiptext">${leave_application ? leave_application+'|'+leave_type : shift +`<br>Start: ${start_time}<br>End: ${end_time}`}</span></div>
						</td>`;

						}
						else{
							sch = `
						<td>
							<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${attendancemap[attendance]} d-flex justify-content-center align-items-center text-white so customtooltip"
								data-selectid="${employee + "|" + date + "|" + attendance}">${attendance_abbr_map[attendance]}<span class="customtooltiptext">${leave_application ? leave_application+'|'+leave_type : shift +`<br>Start: ${start_time}<br>End: ${end_time}`}</span></div>
						</td>`;

						}
					}



				} else {

					if(moment(date)>=moment(relieving_date)){

						sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox darkblackox d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">EX<span class="customtooltiptext">Exited</span></div>
					</td>`;
					}
					else{

					sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox borderbox d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date}"></div>
					</td>`;
					}
				}
				i++;
				start_date.add(1, 'days');
				$rosterMonth.find(`#rowchildtable tbody tr[data-name="${employee}"]`).append(sch);

			}
		}
		$rosterMonth.find(`#rowchildtable tbody tr[data-name="${employees_data[employee_key][i - 1]['employee']}"]`).append(`<td>${j}</td>`);

	}
	bind_events(page);
}


// Get data for Roster weekly view and render it
function get_roster_week_data(page, isOt) {
	classgrt = [];
	classgrtw = [];
	let employee_search_name = '';
	if (page.employee_search_name) {
		employee_search_name = page.employee_search_name;
	}
	let { start_date, end_date } = page;
	let { project, site, shift, department, operations_role } = page.filters;
	let { limit_start, limit_page_length } = page.pagination;


	frappe.xcall('one_fm.one_fm.page.roster.roster.get_roster_view', { start_date, end_date, employee_search_name, project, site, shift, department, operations_role, isOt, limit_start, limit_page_length })
		.then(res => {
			let { operations_roles_data, employees_data, total } = res;
			page.pagination.total = total;

			let $rosterWeek;
			if (isOt) $rosterWeek = $('.rosterOtWeek');
			else $rosterWeek = $('.rosterWeek');
			let $rosterWeekbody = $rosterWeek.find('#calenderweekviewtable tbody');
			$rosterWeekbody.empty();
			for (operations_role_name in operations_roles_data) {
				let pt_row = `
				<tr class="colorclass scheduledStaff" data-name="${operations_role_name}">
					<td class="sticky">
						<div class="d-flex">
							<div class="font16 paddingdiv cursorpointer orangecolor">
								<i class="fa fa-plus" aria-hidden="true"></i>
							</div>
							<div class="font16 paddingdiv borderleft cursorpointer">
								${operations_role_name}
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
					let { date, operations_role, count, highlight } = operations_roles_data[operations_role_name][i];

					let pt_count = `
					<td class="${highlight}">
						<div class="text-center" data-selectid="${operations_role + "|" + date}">${count}</div>
					</td>`;
					$rosterWeek.find(`#calenderweekviewtable tbody tr[data-name="${escape_values(operations_role)}"]`).append(pt_count);
					i++;
					start_date.add(1, 'days');
				}
				$rosterWeek.find(`#calenderweekviewtable tbody tr[data-name="${escape_values(operations_roles_data[operations_role_name][i - 1]['operations_role'])}"]`).append(`<td></td>`);
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
				let employee_day_off = employees_data[employee_key][0]['employee_day_off']
				let emp_row = `
				<tr data-name="${employee_key}">
					<td class="sticky">
						<label class="checkboxcontainer simplecheckbox">
							<span class="lightgrey font16 customfontweight fontw400 postname">${employee_key}</span>
							<input type="checkbox" name="selectallcheckbox" class="selectallcheckbox">
							<span class="checkmark"></span>
						</label>
						<label >
							<span class="lightgrey employee_day_off">${employee_day_off}</span>
						</label>
					</td>
				</tr>`;
				$rosterWeek.find('#rowchildtable tbody').append(emp_row);

				let { start_date, end_date } = page;
				start_date = moment(start_date);
				end_date = moment(end_date);
				let i = 0;
				let j = 0;
				let day = start_date;
				while (day <= end_date) {
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
						'Emergency Leave': 'EL',
						'Leave Without Pay': 'LWP',
						'Working': '!'
					};
					let { employee, employee_name, date, operations_role, post_abbrv, employee_availability, shift } = employees_data[employee_key][i];

					if (employee_availability && post_abbrv) {
						j++;
						sch = `
					<td>
						<div class="${moment().isBefore(moment(date)) ? 'hoverselectclass' : 'forbidden'} tablebox ${classmap[employee_availability]} d-flex justify-content-center align-items-center so"
							data-selectid="${employee + "|" + date + "|" + operations_role + "|" + shift + "|" + employee_availability}">${post_abbrv}</div>
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
			}
			bind_events(page);
		});
}

// Get data for Post view monthly and render it
function get_post_data(page) {
	classgrt = [];
	classgrtw = [];
	let { start_date, end_date } = page;
	let { project, site, shift, department, operations_role } = page.filters;
	let { limit_start, limit_page_length } = page.pagination;
	if (project || site || shift || department || operations_role){
		$('#cover-spin').show(0);

		frappe.xcall('one_fm.one_fm.page.roster.roster.get_post_view', { start_date, end_date, project, site, shift, operations_role, limit_start, limit_page_length })
			.then(res => {
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
						let schedule = ``;
						let classmap = {
							'Planned': 'bluebox',
							'Post Off': 'greyboxcolor',
							'Suspended': 'yellowboxcolor',
							'Cancelled': 'redboxcolor'
						};

						let { project, site, shift, date, post_status, operations_role, post, name } = res["post_data"][post_name][i];
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
								data-post-type="${operations_role}">
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
						$postMonth.find(`#calenderviewtable tbody tr[data-name="${escape_values(post_name)}"]`).append(schedule);
					}
					$postMonth.find(`#calenderviewtable tbody tr[data-name="${escape_values(post_name)}"]`).append(`<td></td>`);
				}
				bind_events(page);
			}).catch(e =>{
				console.log(e);
			});
	}
}

// Get data for Post view weekly and render it
function get_post_week_data(page) {
	classgrt = [];
	classgrtw = [];
	let { start_date, end_date } = page;
	let { project, site, shift, operations_role } = page.filters;

	let { limit_start, limit_page_length } = page.pagination;
	frappe.xcall('one_fm.one_fm.page.roster.roster.get_post_view', { start_date, end_date, project, site, shift, operations_role, limit_start, limit_page_length })
		.then(res => {

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
					let schedule = ``;
					let classmap = {
						'Planned': 'blueboxcolor',
						'Post Off': 'greyboxcolor',
						'Suspended': 'yellowboxcolor',
						'Cancelled': 'redboxcolor'
					};

					let { project, site, shift, date, post_status, operations_role, post, name } = res["post_data"][post_name][i];
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
							data-post-type="${operations_role}">
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
			get_operations_posts(page);
			get_designations(page);
			get_relievers(page);
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

			const selectedProject = page.filters['project'];
            if (selectedProject) {
	           parent.val(selectedProject).trigger("change");
            }

			$(parent).on('select2:select', function (e) {
				page.filters.project = $(this).val();
				get_sites(page);
				get_shifts(page);
				let element = get_wrapper_element().slice(1);

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

			const selectedSite = page.filters['site'];
            if (selectedSite) {
	           parent.val(selectedSite).trigger("change");
            }

			$(parent).on('select2:select', function (e) {
				page.filters.site = $(this).val();
				get_shifts(page);
				let element = get_wrapper_element().slice(1);


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
				shift_data.push({ 'id': element, 'text': element });
			});
			parent.empty().trigger("change");
			parent.select2({ data: shift_data });

			const selectedShift = page.filters['shift'];
            if (selectedShift) {
	           parent.val(selectedShift).trigger("change");
            }

			$(parent).on('select2:select', function (e) {
				page.filters.shift = $(this).val();
				let element = get_wrapper_element().slice(1);


				page[element](page);

			})


		});
}

function get_operations_posts(page) {
	let { employee_id, shift } = page;
	frappe.xcall('one_fm.api.mobile.roster.get_operations_posts', { employee_id, shift })
		.then(res => {
			let parent = $('[data-page-route="roster"] #rosteringpostselect');
			let operations_role_data = [];
			res.forEach(element => {
				let { name } = element;
				operations_role_data.push({ 'id': name, 'text': name });
			});
			parent.select2({ data: operations_role_data });

			const selectedOperationsRole = page.filters['operations_role'];
            if (selectedOperationsRole) {
	           parent.val(selectedOperationsRole).trigger("change");
            }

			$(parent).on('select2:select', function (e) {
				page.filters.operations_role = $(this).val();
				let element = get_wrapper_element().slice(1);


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

			const selectedDepartment = page.filters['department'];
            if (selectedDepartment) {
	           parent.val(selectedDepartment).trigger("change");
            }

			$(parent).on('select2:select', function (e) {
				page.filters.department = $(this).val();
				let element = get_wrapper_element().slice(1);


				page[element](page);
			});

		});
}

function get_designations(page){
	frappe.xcall('one_fm.api.mobile.roster.get_designations')
		.then(res => {
			let parent = $('[data-page-route="roster"] #rosteringdesignationselect');
			let designation_data = [];
			res.forEach(element => {
				let { name } = element;
				designation_data.push({ 'id': name, 'text': name });
			});
			parent.select2({ data: designation_data });

			const selectedDesignation = page.filters['designation'];
            if (selectedDesignation) {
	           parent.val(selectedDesignation).trigger("change");
            }

			$(parent).on('select2:select', function (e) {
				page.filters.designation = $(this).val();
				let element = get_wrapper_element().slice(1);

				page[element](page);
			});
		})
		.catch(e => {
			;
		})
}

function get_relievers(page){
	let parent = $('[data-page-route="roster"] #rosteringrelieverselect');
	let reliever_data = [
		{'id': 'True', 'text': 'Relievers Only'},
		{'id': 'False', 'text': 'Non Relievers Only'},
	];
	parent.select2({ data: reliever_data });

	const selectedReliverStatus = page.filters['relievers'];
    if (selectedReliverStatus) {
	    parent.val(selectedReliverStatus).trigger("change");
    }

	$(parent).on('select2:select', function (e) {
		page.filters.relievers = $(this).val();
		let element = get_wrapper_element().slice(1);

		page[element](page);
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
	let post_element = $(".postMonth").attr("class").split(/\s+/).includes("d-none");
	let post_week_element = $(".postWeek").attr("class").split(/\s+/).includes("d-none");

	if (roster_element && !post_element && post_week_element) {
		element = '.postMonth';
		return element;
	} else if (!roster_element && post_element && post_week_element) {
		element = '.rosterMonth';
		return element;
	} else if (!roster_ot_element && post_element && post_week_element) {
		element = '.rosterOtMonth';
		return element;
	} else if (roster_element && post_element && !post_week_element) {
		element = '.postWeek';
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


//function for dynamic set calender header data on right calender
function GetHeaders(IsMonthSet, element) {

	var thHTML = "";
	var thStartHTML = `<th class="sticky vertical-sticky" style="max-width: 238px !important; min-width: 238px !important;">Operations Role / Days</th>`;
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
			var th = "";
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

			var th = "";
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
	}
	table = $('[data-page-route="roster"] #staffdatatable').on('processing.dt', function (e, settings, processing) {
		$('.dataTables_processing')
			.css('display', processing ? 'flex' : 'none');
		}).on('preXhrpreXhr.dt', function (e, settings, data) {
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
			order: [],
			columnDefs: [{ orderable: false, targets: [0] }]

		}).columns.adjust();
}
//datatable function call for staff

//function for assign dropdown filter
function assignedfilter(value1) {
	var filtervale = $(`[data-page-route="roster"] #desktopview.filtertextget`).text().trim();
	var functionmainvalue = value1;

	if (filtervale == "Assigned" && functionmainvalue == 0) {
		$(".editbtn").removeClass("d-none");
		$(".mobile-edit").removeClass("d-none");
		$(".mainclassfilter").removeClass("d-none");
		$(".allfilters").addClass("d-none");
	}
	else if (filtervale == "Unassigned" && functionmainvalue == 0) {
		$(".editbtn").removeClass("d-none");
		$(".mobile-edit").removeClass("d-none");
		$(".mainclassfilter").removeClass("d-none");
		$(".allfilters").addClass("d-none");
	}
	else {
		$(".editbtn").addClass("d-none");
		$(".mobile-edit").addClass("d-none");
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

	const { project, site, shift, department, operations_role, designation } = filters

	if (project || site || shift || department || operations_role || designation){
		$(".clear_staff_filters").removeClass("d-none")
	} else {
		$(".clear_staff_filters").addClass("d-none")
	}

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


		let { name, employee_id, employee_name, nationality, mobile_no, email, designation, project, site, shift, department,site_supervisor,shift_supervisor,custom_operations_role_allocation,custom_is_reliever } = employee;
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
				${site_supervisor || 'N/A'}
			</td>
			<td>
				${shift || 'N/A'}
			</td>
			<td>
				${shift_supervisor || 'N/A'}
			</td>
			<td>
				${department || 'N/A'}
			</td>
			<td>
				${custom_operations_role_allocation || 'N/A'}
			</td>
			<td>
				${custom_is_reliever ? 'Yes' : 'No'}
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
	const { page: pageFilters, employee: employeeFilters } = get_preset_filters()

	let filters = {
		assigned: pageFilters.assigned === '0' ? 0 : 1,
		company: pageFilters.company || '',
		project: pageFilters.project || '',
		site: pageFilters.site || '',
		shift: pageFilters.shift || '',
		department: pageFilters.department || '',
		designation: pageFilters.designation || '',
		operations_role: pageFilters.operations_role || '',
		employee_search_name: employeeFilters.employee_name || '',
		employee_search_id: employeeFilters.employee_id || '',
		relievers: pageFilters.relievers || '',
	};
	let pagination = {
		limit_start: 0,
		limit_page_length: 100
	};
	if (page) {
		page.filters = filters;
		page.pagination = pagination;
		page.employee_search_id = employeeFilters.employee_id || ''
	    page.employee_search_name = employeeFilters.employee_name || ''
	} else {
		cur_page.page.page.filters = filters;
		cur_page.page.page.pagination = pagination;
	}

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
				}
				else {

					$(".hideshowprjname").removeClass("d-none");
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
	$(".checkboxcontainer").map(function (i, data) {
		let selected = data.querySelectorAll('input[type="checkbox"]:checked');
		if (selected.length){
			let id = ''
			id = selected[0].getAttribute('data-employee-id');
			if (id){
				employees.push(id);
			}
		}
	});

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
							"filters": { site,'status':'Active' },
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
			{'label': 'Is Reliever', 'fieldname': 'custom_is_reliever', 'fieldtype': 'Check', onchange: function () {
				let is_reliever = d.get_value('custom_is_reliever');
				d.set_df_property('custom_operations_role_allocation', 'reqd', !is_reliever);
			}
			},
			{
				'label': 'Default Operations Role', 'fieldname': 'custom_operations_role_allocation', 'fieldtype': 'Link', 'options': 'Operations Role', 'reqd': 1, get_query: function () {
					let shift = d.get_value('shift');
					if (shift) {
						return {
							"filters": { shift },
							"page_len": 9999
						};
					}
				}
			}
		],
		primary_action: function () {
			let { shift, custom_operations_role_allocation, custom_is_reliever } = d.get_values();

			$('#cover-spin').show(0);
			frappe.call({
				method: 'one_fm.one_fm.page.roster.roster.assign_staff',
				args: { employees, shift, custom_operations_role_allocation, custom_is_reliever},
				callback: function (r) {

					d.hide();
					$('#cover-spin').hide();
					update_staff_view();
					frappe.msgprint(__("Successful!"));
				},
				freeze: true,
				freeze_message: __('Editing Post....')
			});
		}
	});

	// Pre-populate if only one employee is selected
	if (employees.length === 1) {
		frappe.call({
			method: 'one_fm.one_fm.page.roster.roster.get_employee_details',
			args: { employee_id: employees[0] },
			callback: function (r) {
				if (r.message) {
					let employee_details = r.message;
					// Populate fields
					d.set_value('project', employee_details.project);
					d.set_value('site', employee_details.site);
					d.set_value('shift', employee_details.shift);
					d.set_value('custom_is_reliever', employee_details.custom_is_reliever);
					d.set_value('custom_operations_role_allocation', employee_details.custom_operations_role_allocation);
				}
			}
		});
	}

	d.show();
}

function update_staff_view() {
	frappe.realtime.on("staff_view", function (output) {

		render_staff($(".layoutSidenav_content").attr("data-view"));
	});
}

//function for dynamic set calender header data on right calender
function GetWeekHeaders(IsMonthSet, element) {
	var thHTML = "";
	var thStartHTML = `<th class="sticky vertical-sticky">Operations Role / Days</th>`;
	var thEndHTML = `<th class="vertical-sticky">Total</th>`;
	var selectedMonth;
	element = get_wrapper_element(element);
	(element);
	if (IsMonthSet == 0) {
		var today = new Date();
		var firstDay = new Date(startOfWeek(today));
		var lastDay = new Date(today.getFullYear(), today.getMonth() + 1, today.getDate() + 6);
		var lastDate = moment(lastDay);
		var getdateres = moment(new Date()).format("DD");

		var dataHTML = "";
		var calDate = moment(new Date(firstDay));
		for (var i = 1; i <= 7; i++) {

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
	let element = get_wrapper_element().slice(1);
	$(element).find("#data-day_" + tdate).addClass("hightlightedtable");
}
//function for get selected date

//on next month title display on arrow click
function rosterweekincrement() {
	weekCalendarSettings.date.add(1, "Weeks");
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
	weekCalendarSettings.date.subtract(1, "Weeks");
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
	let otRoster = false
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
				'label': 'Selected Days Only', 'fieldname': 'selected_days_only', 'fieldtype': 'Check', 'default': 0, onchange: function () {
					let val = d.get_value('selected_days_only');
					if (val) {
						d.set_value('start_date', '');
						d.set_value('never_end', 0);
						d.set_value('select_end', 0);
						d.set_value('end_date', '');
					}
				}
			},
			{ 'fieldtype': 'Section Break', 'depends_on': "eval:doc.selected_days_only == 0" },
			{
				'label': 'Start Date', 'fieldname': 'start_date', 'fieldtype': 'Date', 'reqd': 1, 'mandatory_depends_on': "eval:doc.selected_days_only == 0", 'default': date, onchange: function () {
					let start_date = d.get_value('start_date');
					if (start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						frappe.throw(__("Start Date cannot be before today."));
					}
				}
			},
			{ 'fieldtype': 'Section Break', 'depends_on': "eval:doc.selected_days_only == 0" },
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
			{ 'fieldtype': 'Section Break', 'depends_on': "eval:doc.select_end == 1" },
			{
				'label': 'End Date', 'fieldname': 'end_date', 'fieldtype': 'Date', onchange: function () {
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
			let { selected_days_only, start_date, end_date, never_end } = d.get_values();
			let element = get_wrapper_element();
			if (element == ".rosterOtMonth") {
				otRoster = true;
			} else if (element == ".rosterMonth") {
				otRoster = false;
			}

			frappe.call({
				method: "one_fm.one_fm.page.roster.roster.unschedule_staff",
				type: "POST",
				args: { employees, otRoster, start_date, end_date, never_end, selected_days_only },
				callback: function(res) {
					d.hide();
					error_handler(res);
					let element = get_wrapper_element().slice(1);
					page[element](page);
					$(".filterhideshow").addClass("d-none");
				}
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
						frappe.throw(__("Start Date cannot be before today."));
					}
				}
			},
			{
				'label': 'End Date', 'fieldname': 'end_date', 'fieldtype': 'Date', 'reqd': 1, 'default': date, onchange: function () {
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
				'label': 'Choose Operations Role', 'fieldname': 'operations_role', 'fieldtype': 'Link', 'options': 'Operations Role', 'reqd': 1, get_query: function () {
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
							employees.push({employee, date});
				employees = [... new Set(employees)];
					});
	}
	var hide_day_off_ot_check = 0;
	var hide_keep_days_off_check = 0;
	let element = get_wrapper_element();
	if (element == ".rosterOtMonth") {
		hide_day_off_ot_check = 1;
		hide_keep_days_off_check = 1;
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
				}, get_query: function () {


						return {
							"filters": { 'status':"Active" },
							"page_len": 9999
						};

				}
			},
			{ 'label': 'Site', 'fieldname': 'site', 'fieldtype': 'Link', 'options': 'Operations Site', 'read_only': 1 },
			{ 'label': 'Project', 'fieldname': 'project', 'fieldtype': 'Link', 'options': 'Project', 'read_only': 1 },
			{
				'label': 'Choose Operations Role', 'fieldname': 'operations_role', 'fieldtype': 'Link', 'reqd': 1, 'options': 'Operations Role', get_query: function () {
					return {
						query: "one_fm.one_fm.page.roster.roster.get_filtered_operations_role",
						filters: { "shift": d.get_value('shift') }
					};
				}
			},
			{ 'fieldname': 'cb1', 'fieldtype': 'Section Break' },
			{
				'label': 'Selected Days Only', 'fieldname': 'selected_days_only', 'fieldtype': 'Check', 'default': 0, onchange: function () {
					if (d.get_value('selected_days_only')==1) {
						// Set the date to null and refresh the field
						d.fields_dict.end_date.df.read_only  = 1;
						d.fields_dict.start_date.df.read_only  = 1;
						d.fields_dict.project_end_date.df.read_only  = 1;
						d.fields_dict.project_end_date.df.hidden  = 1;
						d.fields_dict.project_end_date.value  = '';
						d.fields_dict.end_date.refresh()
						d.fields_dict.start_date.refresh()
						d.fields_dict.project_end_date.refresh()
					} else {
						d.fields_dict.end_date.df.read_only  = 0;
						d.fields_dict.start_date.df.read_only  = 0;
						d.fields_dict.project_end_date.df.read_only  = 0;
						d.fields_dict.project_end_date.df.hidden  = 0;
						d.fields_dict.end_date.refresh()
						d.fields_dict.start_date.refresh()
						d.fields_dict.project_end_date.refresh()
					}
				}
			},
			{ 'fieldname': 'cb2', 'fieldtype': 'Section Break' },
			{
				'label': 'From Date', 'fieldname': 'start_date', 'fieldtype': 'Date', 'default': date, onchange: function () {
					let start_date = d.get_value('start_date');
					let end_date = d.get_value('end_date');
					if (start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						// Set the date to null and refresh the field
						d.fields_dict.start_date.value  = '';
						d.fields_dict.start_date.refresh()
						frappe.throw(__("Start Date cannot be before today."));
					}
					if (start_date && end_date && moment(end_date).isBefore(moment(start_date))) {
						// Set the date to null and refresh the field
						d.fields_dict.start_date.value  = '';
						d.fields_dict.start_date.refresh()
						frappe.throw(__("From Date cannot be after Till Date."));
					}
				}
			},
			{ 'label': 'Project End Date', 'fieldname': 'project_end_date', 'fieldtype': 'Check', default:0 },
			{ 'label': 'Keep Days Off', 'fieldname': 'keep_days_off', 'fieldtype': 'Check', default: 0, 'hidden': hide_keep_days_off_check },
			{ 'label': 'Request Employee Schedule', 'fieldname': 'request_employee_schedule', 'fieldtype': 'Check' },
			{ 'label': 'Day Off OT', 'fieldname': 'day_off_ot', 'fieldtype': 'Check' , 'hidden': hide_day_off_ot_check},
			{ 'fieldname': 'cb1', 'fieldtype': 'Column Break' },
			{
				'label': 'Till Date', 'fieldname': 'end_date', 'fieldtype': 'Date', 'depends_on': 'eval:doc.project_end_date==0', default: 0, onchange: function () {
					let end_date = d.get_value('end_date');
					let start_date = d.get_value('start_date');
					if (end_date && moment(end_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						// Set the date to null and refresh the field
						d.fields_dict.end_date.value  = '';
						d.fields_dict.end_date.refresh()
						frappe.throw(__("End Date cannot be before today."));
					}
					if (start_date && end_date && moment(end_date).isBefore(moment(start_date))) {
						// Set the date to null and refresh the field
						d.fields_dict.end_date.value  = '';
						d.fields_dict.end_date.refresh()
						frappe.throw(__("End Date cannot be before Start Date."));
					}
				}
			},
		],
		primary_action: function () {
			let { shift, site, operations_role, project, start_date, project_end_date, keep_days_off, day_off_ot, end_date, request_employee_schedule, selected_days_only } = d.get_values();
			let data = d.get_values();
			$('#cover-spin').show(0);
			let element = get_wrapper_element();
			if (element == ".rosterOtMonth") {
				data.otRoster = true;
			} else if (element == ".rosterMonth") {
				data.otRoster = false;
			}

			if (!employees){
				frappe.throw(__('Please select employees to roster.'))
			}
			// update fields
			if(!data.project_end_date){data.project_end_date=0}
			if(!data.end_date){data.end_date=''}
			data.employees = employees;
			frappe.call({
				method: "one_fm.one_fm.page.roster.roster.schedule_staff",
				type: "POST",
				args: data,
				callback: function(res) {
					// code snippet
					d.hide();
					error_handler(res);
					let element = get_wrapper_element().slice(1);
					update_roster_view(element, page);
					$(".filterhideshow").addClass("d-none");

					if (!("_server_messages" in res)) {
						updateEmployeeDefaults(employees, data);
					}

				}
			});
		}
	});
	d.show();
}


async function updateEmployeeDefaults(employees, data) {
    let employees_to_update = [];

   // Use a Map to store only unique employee records
   let uniqueEmployeeIDs = [...new Set(employees.map(emp => emp.employee))];

   let validProjects = await frappe.db.get_list("Project", {
    filters: { "custom_exclude_from_default_shift_checker": ["!=", 1] },
		});

	// Extract project names (IDs) that are valid
	let validProjectIDs = validProjects.map(project => project.name);

    // Bulk fetch all employees' details in a single query
    let fetchedEmployees = await frappe.db.get_list("Employee", {
        filters: [["name", "in", uniqueEmployeeIDs],["project", "in", validProjectIDs]],
        fields: ["name", "employee_name", "shift", "custom_operations_role_allocation", "custom_is_reliever", "project", "site"],
        limit_page_length: uniqueEmployeeIDs.length // Fetch all in one call
    });

    // Process fetched employees
    fetchedEmployees.forEach(emp => {
        if (!emp.custom_is_reliever && (emp.shift !== data.shift || emp.custom_operations_role_allocation !== data.operations_role)) {
            employees_to_update.push({
                employee: emp.name,
				employee_name: emp.employee_name,
                current_shift: emp.shift,
                new_shift: data.shift,
                current_role: emp.custom_operations_role_allocation,
                new_role: data.operations_role
            });
        }
    });


    if (employees_to_update.length > 0) {
        let table_html = `
			<div style="max-height: 300px; overflow-y: auto;">
				<table style="border-collapse: collapse; width: 100%; text-align: left;">
					<thead>
						<tr style="background-color: #f8f9fa;">
							<th style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">Employee Name</th>
							<th style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">Current Shift</th>
							<th style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">New Shift</th>
							<th style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">Current Role</th>
							<th style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">New Role</th>
						</tr>
					</thead>
					<tbody>`;

		employees_to_update.forEach(emp => {
			table_html += `
				<tr>
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.employee_name}</td>
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.current_shift || 'Not Set'}</td>
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.new_shift || 'Not Set'}</td>
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.current_role || 'Not Set'}</td>
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.new_role || 'Not Set'}</td>
				</tr>`;
		});

		table_html += `</tbody></table></div>`;

		frappe.confirm(
			`Hey, you just rostered these employees to shifts or roles different from their defaults. Would you like to update their default shift or role?<br>${table_html}`,
			async () => {
				// Batch update in a single request
				await frappe.call({
					method: "one_fm.one_fm.page.roster.roster.bulk_employee_record_update",
					args: {
						updates: employees_to_update.map(emp => ({
							name: emp.employee,
							shift: emp.new_shift,
							custom_operations_role_allocation: emp.new_role,
							project: data.project,
							site: data.site
						}))
					},
					freeze: true,
					freeze_message: "Updating employee defaults..."
				});
			}
		);
    }
}


function clear_roster_filters(page) {
	window.history.replaceState({}, document.title, window.location.origin + window.location.pathname);

	page.filters = {}
	cur_page.page.page.filters = {}

	$('#page-roster').empty().append(frappe.render_template('roster'));
	load_js(page)
}

function clear_staff_filters(page) {
	window.history.replaceState({}, document.title, window.location.origin + window.location.pathname);

	page.filters = {}
	cur_page.page.page.filters = {}

	$(".assigneddrpval").html("Assigned");
	["company", "project", "site", "shift", "department", "designation"].forEach(item => {
		$(`a[data-filter-type=${item}]`).click()
	})

	render_staff($(".layoutSidenav_content").attr("data-view"));
}

function clear_selection(page) {
	classgrt = [];
	classgrtw = [];

	$(".filterhideshow").addClass("d-none");
	$(".Postfilterhideshow").addClass("d-none");

	$("#calenderviewtable tbody").find("tr").each(function (i, row) {
		$(row).find("input[type='checkbox']").prop("checked", false); // Uncheck the employee checkbox
		$(row).find("div").removeClass("selectclass"); // Remove days selections
	});
}

function update_roster_view(element, page) {
	page[element](page);
	frappe.realtime.on("roster_view", function (output) {
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

		if (typeof settings.childSelector != "undefined") {
			children = listElement.find(settings.childSelector);
		}

		if (typeof settings.pagerSelector != "undefined") {
			pager = wrapper_element.find(settings.pagerSelector);
		}

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

		pager.find('.prev_link').hide();
		if (numPages <= 1) {
			pager.find('.next_link').hide();
		}

		let active_page = (page.pagination.limit_start / page.pagination.limit_page_length);
		pager.children().eq(active_page).addClass("active");

		children.hide();
		children.slice(0, perPage).show();
		pager.find('li .page_link').click(function () {
			var clickedPage = $(this).html().valueOf() - 1;
			let limit_start = ((clickedPage + 1) * 100) - 100;

			page.pagination.limit_start = limit_start;
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
	let reliever_options = reliever_data.map(item => `${item.employee_id} - ${item.employee_name}`).join("\n");


	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), '1');
	let d = new frappe.ui.Dialog({
		'title': 'Day Off',
		'fields': [
			{ 'label': 'Selected days only', 'fieldname': 'selected_dates', 'fieldtype': 'Check', 'default': 0 },
			{ 'label': 'Set Reliever', 'fieldname': 'set_reliever', 'fieldtype': 'Check', 'default': 0 },
			{ 'label': 'Reliever', 'fieldname': 'selected_reliever', 'fieldtype': 'Select', 'options': reliever_options,'depends_on': 'eval:doc.set_reliever==1' },
			{ 'label': 'Repeat', 'fieldname': 'repeat', 'fieldtype': 'Select', 'depends_on': 'eval:doc.selected_dates==0', 'options': 'Does not repeat\nWeekly\nMonthly' },
			{ 'fieldtype': 'Section Break', 'fieldname': 'sb1', 'depends_on': 'eval:doc.repeat=="Weekly" && doc.selected_dates==0' },
			{ 'label': 'Sunday', 'fieldname': 'sunday', 'fieldtype': 'Check' },
			{ 'label': 'Wednesday', 'fieldname': 'wednesday', 'fieldtype': 'Check' },
			{ 'label': 'Saturday', 'fieldname': 'saturday', 'fieldtype': 'Check' },
			{ 'fieldtype': 'Column Break', 'fieldname': 'cb1' },
			{ 'label': 'Monday', 'fieldname': 'monday', 'fieldtype': 'Check' },
			{ 'label': 'Thursday', 'fieldname': 'thursday', 'fieldtype': 'Check' },
			{ 'fieldtype': 'Column Break', 'fieldname': 'cb2' },
			{ 'label': 'Tuesday', 'fieldname': 'tuesday', 'fieldtype': 'Check' },
			{ 'label': 'Friday', 'fieldname': 'friday', 'fieldtype': 'Check' },
			{ 'fieldtype': 'Section Break', 'fieldname': 'sb2', 'depends_on': 'eval:doc.selected_dates==0' },
			{ 'label': 'Repeat Till', 'fieldtype': 'Date', 'fieldname': 'repeat_till', 'depends_on': 'eval:doc.repeat!= "Does not repeat" && doc.project_end_date==0' },
			{'label': 'Project End Date', 'fieldname': 'project_end_date', 'fieldtype': 'Check' },
		],
		primary_action: function () {
			$('#cover-spin').show(0);
			let week_days = [];
			let args = {};
			let repeat_freq = '';
			let { selected_dates,set_reliever,selected_reliever, repeat, sunday, monday, tuesday, wednesday, thursday, friday, saturday, repeat_till, project_end_date } = d.get_values();
			args["selected_dates"] = selected_dates;
			args["set_reliever"] = set_reliever;
			args["employees"] = employees;

			if(set_reliever == 0){
				args['selected_reliever']=""
			}else{
				args['selected_reliever']=selected_reliever
			}

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
				else if (repeat == "Monthly") {
					repeat_freq = "Monthly";
					args["repeat_freq"] = repeat_freq;
				}
			}

			frappe.call({
				method: "one_fm.one_fm.page.roster.roster.dayoff",
				type: "POST",
				args: args,
				callback: function(res) {
					// code snippet
					d.hide();
					error_handler(res);
					let element = get_wrapper_element().slice(1);
					page[element](page);
					$(".filterhideshow").addClass("d-none");
				}
			});
		}
	});
	d.show();
}

// Edit mobile number
function editMobileNumber(){
	employees_pk = $(".datatablecjeckbox:checked").map(function () {
		return $(this).attr("data-employee-id");
	}).get();
	const table_fields = [
		{
			fieldname: "employee", fieldtype: "Link",
			in_list_view: 1, label: "Employee",
			options: "Employee", reqd: 1
		},
		{
			fieldname: "employee_id", fieldtype: "Data",
			in_list_view: 1, label: "Employee ID", reqd:1,
			read_only: 1, depends_on: "employee",
			fetch_from: "employee.employee_id"
		},
		{
			fieldname: "employee_name", fieldtype: "Data",
			in_list_view: 1, label: "Name", reqd:1,
			read_only: 1, depends_on: "employee",
			fetch_from: "employee.employee_name"
		}
	];

	let d = new frappe.ui.Dialog({
		title: 'Enter details',
		fields: [
			{
				label: 'First Name',
				fieldname: 'first_name',
				fieldtype: 'Data'
			},
			{
				label: 'Last Name',
				fieldname: 'last_name',
				fieldtype: 'Data'
			},
			{
				fieldname: "employees",
				fieldtype: "Table",
				label: "Employees",
				cannot_delete_rows: true,
				in_place_edit: true,
				reqd: 1,
				data: [],
				fields: table_fields
			}
		],
		primary_action_label: 'Submit',
		primary_action(values) {

			d.hide();
		}
	});

	d.show();

	employees_pk.forEach((item, i) => {
		d.fields_dict.employees.df.data.push(
			{ employee: item}
		);
	});
	d.fields_dict.employees.grid.refresh();
}


function editSingleEmployeeData(){
	let d = new frappe.ui.Dialog({
		title: 'Update Employee Record',
		fields: [
			{
				label: 'Employee',
				fieldname: 'employee',
				fieldtype: 'Link',
				options: "Employee",
				reqd:1,
				ignore_user_permissions: 1,
				change: function (x) {
					employee_pk = d.fields_dict.employee.value;
					if(employee_pk){
					frappe.xcall('one_fm.one_fm.page.roster.roster.get_employee_detail', { employee_pk })
						.then(res => {
							d.fields_dict.employee_id.value = res.employee_id;
							d.fields_dict.employee_name.value = res.employee_name;
							d.fields_dict.enrolled.value = res.enrolled;
							d.fields_dict.cell_number.value = res.cell_number;
							d.fields_dict.employee_id.refresh();
							d.fields_dict.employee_name.refresh();
							d.fields_dict.enrolled.refresh();
							d.fields_dict.cell_number.refresh();
						});

					}
				}
			},
			{
				label: 'Employee ID',
				fieldname: 'employee_id',
				fieldtype: 'Data',
				depends_on: 'employee',
				read_only: 1
			},
			{
				label: 'Employee Name',
				fieldname: 'employee_name',
				fieldtype: 'Data',
				depends_on: 'employee',
				read_only: 1
			},

			{
			   fieldname: "column_break0",
			   fieldtype: "Column Break"
			},
			{
				label: 'Phone Number',
				fieldname: 'cell_number',
				fieldtype: 'Data',
				depends_on: 'employee',
				read_only: 1
			},
			{
				label: 'Enrolled',
				fieldname: 'enrolled',
				fieldtype: 'Data',
				depends_on: 'employee',
				read_only: 1
			},
			{
				label: '<i style="color:red">Action</i>',
				fieldname: 'action_type',
				fieldtype: 'Select',
				depends_on: 'employee',
				options: ["Update Phone Number", "Reset Enrollment"],
				reqd: 1,
			},
			{
				label: 'New Phone Number',
				fieldname: 'new_phone_number',
				fieldtype: 'Data',
				depends_on: "eval:doc.action_type=='Update Phone Number'",
				options: ""
			},

		],
		primary_action_label: 'Submit',
		primary_action(values) {
			// action to perform if Yes is selected
			d.hide();
			makeCall(values);
		}
	});

	d.show();
}


function makeCall(argsObject){
	frappe.confirm('Are you sure you want to proceed?',
		() => {
			let postvalue = {employee_id: argsObject.employee_id};
			if (argsObject.action_type === 'Update Phone Number') {
				postvalue.field = 'cell_number';
				postvalue.value = argsObject.new_phone_number;
			} else {
				postvalue.field = 'enrolled';
				postvalue.value = 0;
			}
			frappe.call({
				method: "one_fm.api.v1.utils.update_employee", //dotted path to server method
				args: postvalue,
				callback: function(r) {
					// code snippet
					frappe.msgprint(r.message);
				}
			});
		}, () => {
			// action to perform if No is selected
	})
}



let error_handler = (res) => {
	if (res.error){
		$('#cover-spin').hide();
		frappe.throw(res.error);
	} else if (res.data){
		if(res.data.message){
			frappe.msgprint(res.data.message);
			$('#cover-spin').hide();
		} else {
			$('#cover-spin').hide();
		}
	} else {
		$('#cover-spin').hide();
	}
}


function roster_employee_actions(page){
	let dialog = new frappe.ui.Dialog({
		title: "Employee with Missing Schedules",
		fields: [
			{
				fieldname: "employees_table",
				fieldtype: "HTML",
				options: "<div id='employees_table'></div>"
			}
		]
	})
	dialog.$wrapper.find(".modal-dialog").css("max-width", "75%");


	frappe.call({
		method: "one_fm.one_fm.doctype.roster_employee_actions.roster_employee_actions.get_employees_with_missing_schedules",
		// freeze: true,
		async: true,
		callback: function(r) {
			dialog.fields_dict.employees_table.$wrapper.html(r.message);
		}
	});
	dialog.show();
}