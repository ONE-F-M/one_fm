// Frappe Init function to render Roster
frappe.pages["roster"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Roster",
		single_column: true
	});
	$("#page-roster").empty().append(frappe.render_template("roster"));

	load_js(page);
};


// Initializes the page with default values
function load_js(page) {
	$(this).scrollTop(0);

	window.clickcount = 0;
	window.employees_list = [];
	window.isMonth = 1;
	window.classgrt = [];

	setup_staff_filters(page);
	setup_topbar_events(page);

	$(`a[href="#"]`).click(function (e) {
		if (!$(this).hasClass("navbar-brand")) {
			e.preventDefault();
		}
	});

	$(".customredropdown .customdropdownheight .dropdown-item").click(function () {
		var text = $(this).html();
		$(this).parent().parent().parent().find(".dropdown-toggle .dropdowncustomres").html(text);
	});

	window.today = new Date();
	today.setHours(0, 0, 0, 0);
	if ($(".layoutSidenav_content").attr("data-view") == "roster") {
		setup_filters(page);

		// Dropdown option click
		$(document).on("click", ".dropdown-option", function() {
			let filter_type = $(this).attr("data-filter");
			let value = $(this).attr("data-" + filter_type);

			// Set this and all parent filters from data attributes
			if (filter_type === "project") {
				page.filters.project = value;
				["site", "shift", "operations_role", "employee_search_name", "employee_search_id"].forEach(k => delete page.filters[k]);
			}
			if (filter_type === "site") {
				page.filters.project = $(this).attr("data-project");
				page.filters.site = value;
				["shift", "operations_role", "employee_search_name", "employee_search_id"].forEach(k => delete page.filters[k]);
			}
			if (filter_type === "shift") {
				page.filters.project = $(this).attr("data-project");
				page.filters.site = $(this).attr("data-site");
				page.filters.shift = value;
				["operations_role", "employee_search_name", "employee_search_id"].forEach(k => delete page.filters[k]);
			}
			if (filter_type === "operations_role") {
				page.filters.project = $(this).attr("data-project");
				page.filters.site = $(this).attr("data-site");
				page.filters.shift = $(this).attr("data-shift");
				page.filters.operations_role = value;
				["employee_search_name", "employee_search_id"].forEach(k => delete page.filters[k]);
			}
			if (filter_type === "employee_search_id" || filter_type === "employee_search_name") {
				page.filters.project = $(this).attr("data-project");
				page.filters.site = $(this).attr("data-site");
				page.filters.shift = $(this).attr("data-shift");
				page.filters.operations_role = $(this).attr("data-operations_role");
				page.filters.employee_search_name = $(this).attr("data-employee_search_name");
				page.filters.employee_search_id = value;
				delete page.filters.reliever;
			}
			if (filter_type === "reliever") {
				page.filters.reliever = value;
			}

			// Clear search text after selection
			$("#search-bar").val("");
			populate_dropdown_options(page, "");
			render_selected_tags(page);
			update_clear_button(page);

		});

		$("#dropdown-apply-btn").on("click", function() {
			// Hide dropdown
			$("#dropdownContent").addClass("d-none");
			// Call the roster loader as per your code
			let element = get_wrapper_element().slice(1);
			page[element](page);
		});

		// Search bar input
		$("#search-bar").on("input", function() {
			populate_dropdown_options(page, $(this).val());
		});

		// Clear all filters
		$("#clear-filters").on("click", function() {
			page.filters = {};
			$("#search-bar").val("");
			populate_dropdown_options(page, "");
			render_selected_tags(page);
			update_clear_button(page);
			clear_roster_filters(page);
		});

		// Show dropdown on focus
		$("#search-bar").on("focus", function() {
			$("#dropdownContent").removeClass("d-none");
		});

		// Hide dropdown when clicking outside
		$(document).on("mousedown", function(e) {
			if (!$(".input-search").is(e.target) && $(".input-search").has(e.target).length === 0) {
				$("#dropdownContent").addClass("d-none");
			}
		});

		// Focus input on container click
		$("#search-bar-container").on("click", function() {
			$("#search-bar").focus();
		});

		// Initial render
		$(function() {
			render_selected_tags(page);
			update_clear_button(page);
		});

		$rosterMonth = $(".rosterMonth");
		$postMonth = $(".postMonth");

		
		$(".rosterviewclick").click(function () {
			$("#rosterTypeButtons").removeClass("d-none");
			$("#rosterTypeButtons").addClass("d-flex");
			$rosterMonth.removeClass("d-none");
			$postMonth.addClass("d-none");
			$(".postviewclick").removeClass("active bg-primary");
			$(".rosterviewclick").addClass("active bg-primary");
			$(".switch-container").removeClass("d-none");
			$(".Postfilterhideshow").addClass("d-none");
			$(".filterhideshow").addClass("d-none");
			$(".rosterviewfilterbg").removeClass("d-none");
			$(".postviewfilterbg").addClass("d-none");
			$(".employee-section").removeClass("d-none");
			$(".reliever-section").removeClass("d-none");

			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".rosterMonth");
			get_roster_data(page);
		});

		$(".postviewclick").click(function () {
			$("#rosterTypeButtons").removeClass("d-flex");
			$("#rosterTypeButtons").addClass("d-none");
			$rosterMonth.addClass("d-none");
			$postMonth.removeClass("d-none");
			$(".postviewclick").addClass("active bg-primary");
			$(".rosterviewclick").removeClass("active bg-primary");
			$(".switch-container").addClass("d-none");
			$(".Postfilterhideshow").addClass("d-none");
			$(".filterhideshow").addClass("d-none");
			$(".rosterviewfilterbg").addClass("d-none");
			$(".postviewfilterbg").removeClass("d-none");
			$(".employee-section").addClass("d-none");
			$(".reliever-section").addClass("d-none");

			displayCalendar(calendarSettings1, page);
			GetHeaders(0, ".postMonth");
			get_post_data(page);
		});

		$(".postmonthviewclick").click(function () {
			$rosterMonth.addClass("d-none");
			$postMonth.removeClass("d-none");
			displayCalendar(calendarSettings1, page);
			GetHeaders(1, ".postMonth");
			get_post_data(page);
		});

		$(".monthviewclick").click(function () {
			$rosterMonth.removeClass("d-none");
			$postMonth.addClass("d-none");
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

		$(".editpostclassclick").click(function () {
			if (["Operations Manager", "Projects Manager"].some(i => frappe.user_roles.includes(i))) {
				let date = frappe.datetime.add_days(frappe.datetime.nowdate(), "1");
				let posts = [];
				let selected = [... new Set(classgrt)];

				selected.forEach(function (i) {
					let [post, date] = i.split("_");
					posts.push({ post, date });
				});
				posts = [... new Set(posts)];
				let d = new frappe.ui.Dialog({
					title: "Edit Post",
					fields: [
						{
							label: "Post Status",
							fieldname: "post_status",
							fieldtype: "Select",
							options: "\nPlan Post\nPost Off\nSuspend Post\nCancel Post",
							reqd: 1
						},
						{
							fieldname: "sb4",
							fieldtype: "Section Break",
							depends_on: "eval:doc.post_status == 'Plan Post'",
						},
						{
							label: "Plan From Date",
							fieldname: "plan_from_date",
							fieldtype: "Date",
							default: date
						},
						{
							label: "Plan Till Date",
							fieldname: "plan_end_date",
							fieldtype: "Date",
							depends_upon: "eval:doc.project_end_date==0",
							onchange: function () {
								let plan_end_date = d.get_value("plan_end_date");
								if (plan_end_date && moment(plan_end_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Plan Till Date cannot be before today."));
								}
							}
						},
						{
							fieldname: "sb1",
							fieldtype: "Section Break",
							depends_on: "eval:doc.post_status == 'Cancel Post'",
						},
						{
							label: "Cancel From Date",
							fieldname: "cancel_from_date",
							fieldtype: "Date",
							default: date,
							onchange: function () {
								let cancel_from_date = d.get_value("cancel_from_date");
								if (cancel_from_date && moment(cancel_from_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Cancel From date cannot be before today."));
								}
							}
						},
						{
							label: "Cancel Till Date",
							fieldname: "cancel_end_date",
							fieldtype: "Date",
							depends_upon: "eval:doc.project_end_date==0",
							onchange: function () {
								let plan_end_date = d.get_value("cancel_end_date");
								if (plan_end_date && moment(plan_end_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Cancel Till Date cannot be before today."));
								}
							}
						},
						{
							fieldname: "sb3",
							fieldtype: "Section Break",
							depends_on: "eval:doc.post_status == 'Post Off'",
						},
						{
							label: "Paid",
							fieldname: "post_off_paid",
							fieldtype: "Check",
							onchange: function () {
								let val = d.get_value("post_off_paid");
								if (val) {
									d.set_value("post_off_unpaid", 0);
								}
							}
						},
						{
							fieldname: "cb7",
							fieldtype: "Column Break",
						},
						{
							fieldname: "sb5",
							fieldtype: "Section Break",
							depends_on: "eval:doc.post_status == 'Post Off'",
						},
						{
							label: "Post Off From Date",
							fieldname: "post_off_from_date",
							fieldtype: "Date",
							default: date
						},
						{ label: "Repeat", fieldname: "repeat", fieldtype: "Select", options: "Does not repeat\nSelected Days Only\nDaily\nWeekly\nMonthly\nYearly" },
						{ "fieldtype": "Section Break", "fieldname": "sb1", "depends_on": "eval:doc.post_status=='Post Off' && doc.repeat=='Weekly'" },
						{ "label": "Sunday", "fieldname": "sunday", "fieldtype": "Check" },
						{ "label": "Wednesday", "fieldname": "wednesday", "fieldtype": "Check" },
						{ "label": "Saturday", "fieldname": "saturday", "fieldtype": "Check" },
						{ "fieldtype": "Column Break", "fieldname": "cb1" },
						{ "label": "Monday", "fieldname": "monday", "fieldtype": "Check" },
						{ "label": "Thursday", "fieldname": "thursday", "fieldtype": "Check" },
						{ "fieldtype": "Column Break", "fieldname": "cb2" },
						{ "label": "Tuesday", "fieldname": "tuesday", "fieldtype": "Check" },
						{ "label": "Friday", "fieldname": "friday", "fieldtype": "Check" },
						{ "fieldtype": "Section Break", "fieldname": "sb2", "depends_on": "eval:doc.post_status=='Post Off' && doc.repeat!= 'Does not repeat' && doc.repeat!= 'Selected Days Only'" },
						{ "label": "Repeat Till", "fieldtype": "Date", "fieldname": "repeat_till", "depends_upon": "eval:doc.project_end_date==0" },
						{
							fieldname: "sb2",
							fieldtype: "Section Break",
							depends_on: "eval:doc.post_status == 'Suspend Post'",
						},
						{
							label: "Paid",
							fieldname: "suspend_paid",
							fieldtype: "Check",
							onchange: function () {
								let val = d.get_value("suspend_paid");
								if (val) {
									d.set_value("suspend_unpaid", 0);
								}
							}
						},
						{
							label: "Suspend From Date",
							fieldname: "suspend_from_date",
							fieldtype: "Date",
							default: date,
							onchange: function () {
								let suspend_from_date = d.get_value("suspend_from_date");
								if (suspend_from_date && moment(suspend_from_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Suspend From Date cannot be before today."));
								}
							}
						},
						{
							label: "Never End",
							fieldname: "suspend_never_end",
							fieldtype: "Check",
						},
						{
							fieldname: "cb1",
							fieldtype: "Column Break",
						},
						{
							label: "Unpaid",
							fieldname: "suspend_unpaid",
							fieldtype: "Check",
							onchange: function () {
								let val = d.get_value("suspend_unpaid");
								if (val) {
									d.set_value("suspend_paid", 0);
								}
							}
						},
						{
							label: "Suspend Till Date",
							fieldname: "suspend_to_date",
							fieldtype: "Date",
							depends_on: "eval:doc.project_end_date==0",
							onchange: function () {
								let suspend_to_date = d.get_value("suspend_to_date");
								if (suspend_to_date && moment(suspend_to_date).isBefore(moment(frappe.datetime.nowdate()))) {
									frappe.throw(__("Suspend To Date cannot be before today."));
								}
							}
						},
						{
							fieldname: "sb_project_end_date",
							fieldtype: "Section Break"
						},
						{
							label: "Project end date",
							fieldname: "project_end_date",
							fieldtype: "Check",
						},
					],
					primary_action_label: "Submit",
					primary_action(values) {
						$("#cover-spin").show(0);

						frappe.call({
							method: "one_fm.one_fm.page.roster.roster.edit_post",
							args: { posts, values },
							callback: function (r) {

								d.hide();
								$("#cover-spin").hide();
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
							freeze_message: __("Editing Post....")
						});
					}
				});

				d.show();
			}
			else {
				frappe.throw(frappe._("Insufficient permissions to Edit Post."));

			}
		});
		$("#chkassgined").prop("checked", true);
		$("#chkassgined").trigger("change");


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
		page.postMonth = get_post_data;

	}


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

	setup_preset_filters(page)
}

function populate_dropdown_options(page, filter = "") {
    let selected = page.filters || {};
    let reliever_selected = selected.reliever;
    const filter_order = ["project", "site", "shift", "operations_role", "employee_search_name", "reliever"];
    let last_selected_idx = -1;
    filter_order.forEach((k, i) => { if (selected[k]) last_selected_idx = i; });

    // If filter is present and no filter is selected, filter all main filters
    let filterAll = filter && last_selected_idx === -1;

    // Helper: Should this filter be filtered by search text?
    function shouldFilter(idx) {
        if (!filter) return false;
        if (last_selected_idx === -1) return true; // No filter selected: filter all
        return idx > last_selected_idx; // Only filter unselected filters after last selected
    }

    // PROJECTS
    let $projectList = $("#rosteringprojectselect").empty();
    (page.search_bar_data["rosteringprojectselect"] || []).forEach(project_obj => {
        const project_name = project_obj.project;
        let show = (!selected.project || selected.project === project_name);
        if (shouldFilter(0)) show = show && project_name.toLowerCase().includes(filter.toLowerCase());
        if (show) {
            $projectList.append(
                $("<div class='dropdown-option'></div>")
                    .text(project_name)
                    .attr("data-filter", "project")
                    .attr("data-project", project_name)
            );
        }
    });

    // SITES
    let $siteList = $("#rosteringsiteselect").empty();
    (page.search_bar_data["rosteringsiteselect"] || []).forEach(site_obj => {
        let {site, project} = site_obj;
        let show = (!selected.project || selected.project === project) &&
                   (!selected.site || selected.site === site);
        if (shouldFilter(1)) show = show && site.toLowerCase().includes(filter.toLowerCase());
        if (show) {
            $siteList.append(
                $("<div class='dropdown-option'></div>")
                    .text(site)
                    .attr("data-filter", "site")
                    .attr("data-site", site)
                    .attr("data-project", project)
            );
        }
    });

    // SHIFTS
    let $shiftList = $("#rosteringshiftselect").empty();
    (page.search_bar_data["rosteringshiftselect"] || []).forEach(shift_obj => {
        let {shift, site, project} = shift_obj;
        let show = (!selected.project || selected.project === project) &&
                   (!selected.site || selected.site === site) &&
                   (!selected.shift || selected.shift === shift);
        if (shouldFilter(2)) show = show && shift.toLowerCase().includes(filter.toLowerCase());
        if (show) {
            $shiftList.append(
                $("<div class='dropdown-option'></div>")
                    .text(shift)
                    .attr("data-filter", "shift")
                    .attr("data-shift", shift)
                    .attr("data-site", site)
                    .attr("data-project", project)
            );
        }
    });

    // ROLES
    let $roleList = $("#rosteringroleselect").empty();
    (page.search_bar_data["rosteringroleselect"] || []).forEach(role_obj => {
        let {operations_role, shift, site, project} = role_obj;
        let show = (!selected.project || selected.project === project) &&
                   (!selected.site || selected.site === site) &&
                   (!selected.shift || selected.shift === shift) &&
                   (!selected.operations_role || selected.operations_role === operations_role);
        if (shouldFilter(3)) show = show && operations_role.toLowerCase().includes(filter.toLowerCase());
        if (show) {
            $roleList.append(
                $("<div class='dropdown-option'></div>")
                    .text(operations_role)
                    .attr("data-filter", "operations_role")
                    .attr("data-operations_role", operations_role)
                    .attr("data-shift", shift)
                    .attr("data-site", site)
                    .attr("data-project", project)
            );
        }
    });

    // EMPLOYEES
	let $employeeList = $("#rosteringemployeeselect").empty();
	(page.search_bar_data["rosteringemployeeselect"] || []).forEach(emp => {
		let empName = emp.name || emp.employee_name || emp;
		let empId = emp.employee_id || emp.id || emp;
		let is_reliever = emp.is_reliever;
		let { project, site, shift, operations_role } = emp;

		// Hierarchical filtering
		let show = true;
		if (selected.project && project !== selected.project) show = false;
		if (selected.site && site !== selected.site) show = false;
		if (selected.shift && shift !== selected.shift) show = false;
		if (selected.operations_role && operations_role !== selected.operations_role) show = false;

		// Reliever filter: always applies if selected, regardless of other filters
		if (reliever_selected !== undefined && reliever_selected !== "") {
			show = show && (String(is_reliever) === String(reliever_selected));
		}

		// Search text filtering (only if no filter is selected, or if all main filters are selected)
		if (shouldFilter(4)) {
			show = show && (
				empName.toLowerCase().includes(filter.toLowerCase()) ||
				(empId && empId.toLowerCase().includes(filter.toLowerCase()))
			);
		}

		if (show) {
			$employeeList.append(
				$("<div class='dropdown-option'></div>")
					.text(`${empName} - ${empId}`)
					.attr("data-filter", "employee_search_id")
					.attr("data-employee_search_name", empName)
					.attr("data-employee_search_id", empId)
					.attr("data-is_reliever", is_reliever)
					.attr("data-project", project)
					.attr("data-site", site)
					.attr("data-shift", shift)
					.attr("data-operations_role", operations_role)
			);
		}
	});

    // RELIEVERS (no hierarchy, just render)
    let $relieverList = $("#rosteringrelieverselect").empty();
    (page.search_bar_data["rosteringrelieverselect"] || []).forEach(rel => {
        let relText = rel.text || rel;
        $relieverList.append(
            $("<div class='dropdown-option'></div>")
                .text(relText)
                .attr("data-filter", "reliever")
				.attr("data-filter_name", rel.text)
                .attr("data-reliever", rel.id)
        );
    });
}


// Show/hide clear button
function update_clear_button(page) {
    if (Object.keys(page.filters).some(k => page.filters[k])) {
        $("#clear-filters").show();
    } else {
        $("#clear-filters").hide();
    }
}

const filter_order = ["project", "site", "shift", "operations_role", "employee_search_name", "reliever"];

function render_selected_tags(page) {
    let $container = $("#search-bar-container");
    $container.find(".selected-tag").remove();

    filter_order.forEach(filterKey => {
		if (page.filters[filterKey]) {
			let tag_text = "";
			if (filterKey == "reliever") { page.filters[filterKey] == "1" ? tag_text = "Relievers Only" : tag_text = "Non-Relievers Only"; }

            let $tag = $("<span class='selected-tag'></span>").html(`<span class="selected-tag-text">${filterKey == "reliever" ? tag_text : page.filters[filterKey]}</span>`);
            let $close = $("<span class='remove-tag'>&times;</span>");
            $close.on("click", function(e) {
                e.stopPropagation();
                // Remove this and all child filters
                let idx = filter_order.indexOf(filterKey);
                filter_order.slice(idx).forEach(k => delete page.filters[k]);
                render_selected_tags(page);
                $("#search-bar").val("");
                populate_dropdown_options(page, "");
                update_clear_button(page);
            });
            $tag.append($close);
            $tag.insertBefore($("#search-bar"));
        }
    });
    update_clear_button(page);
}

function get_preset_filters() {
	let { main_view, sub_view, roster_type, staff_view_mode, employee_id, employee_name, ...pageFilters } = frappe.utils.get_query_params();

	return {
		view: { main_view, sub_view, roster_type, staff_view_mode },
		employee: { employee_id, employee_name },
		page: pageFilters
	}
}

// Setup and populate preset filters set via query params
function setup_preset_filters(page) {
	// To avoid re-rendering of roster page
	if (window.preset_filters_applied) return

	const { view: viewFilters, page: pageFilters, employee: employeeFilters } = get_preset_filters()

	const { main_view: mainView, sub_view: subView, roster_type: rosterType, staff_view_mode: staffViewMode } = viewFilters

	if (mainView) {
		setTimeout(() => {
			$("#page-roster")
				.find(`.redirect_route[data-route="${mainView}"]`)
				.click();
		}, 500);
	}

	if (pageFilters.month && pageFilters.year) {
		const newDate = moment(`${pageFilters.year}-${pageFilters.month}-01`, "YYYY-MM-DD").toDate();
		if (calendarSettings1) {
			calendarSettings1.date = moment(newDate);
			displayCalendar(calendarSettings1, page);
		}
	}


	function toggle_between_views() {
		if (mainView === "roster") {
			if (subView === "roster") {
				setTimeout(() => {
					$(".rosterviewclick").click()
				}, 1000);
			}
			if (subView === "post") {
				setTimeout(() => {
					$(".postviewclick").click()
				}, 1000);
			}
		}
	}

	function populate_values() {
		if (mainView === "roster") {
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
		} else if (mainView === "staff") {
			setTimeout(() => {
				const { company, project, site, shift, department, designation } = pageFilters;
				if (company) $(".staff-company-dropdown").html(company)
				if (project) $(".staff-project-dropdown").html(project)
				if (site) $(".staff-site-dropdown").html(site)
				if (shift) $(".staff-shift-dropdown").html(shift)
				if (department) $(".staff-department-dropdown").html(department)
				if (designation) $(".staff-designation-dropdown").html(designation)

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

	$(".changepost").on("click", function () {
		schedule_change_post(page);
	});

	$(".change_ot").on("click", function () {
		change_ot_schedule(page);
	});

	$(".assignchangemodal").on("click", function () {
		unschedule_staff(page);
	});

	$(".dayoff").on("click", function () {
		dayoff(page);
	});

	$(".clear_roster_filters").on("click", function () {
		clear_roster_filters(page);
	});

	$(".clear_staff_filters").on("click", function () {
		clear_staff_filters(page);
	});

	$(".clear_selection").on("click", function () {
		clear_selection(page);
	});

	$("#rosterEmployeeActions").on("click", function () {
		roster_employee_actions(page);
	});

	$("#rosterDayOffIssues").on("click", function () {
		roster_day_off_issues(page);
	});

	$("#rosterPostActions").on("click", function () {
		roster_post_actions(page);
	});
}

//Bind events to Edit options in Roster/Post view
function bind_events(page) {
	if (["Operations Manager", "Site Supervisor", "Shift Manager", "Shift Supervisor", "Projects Manager"].some(i => frappe.user_roles.includes(i))) {
		let $rosterMonth = $(".rosterMonth");
		let $postMonth = $(".postMonth");

		$postMonth.find(".hoverselectclass").on("click", function () {
			$(this).closest("tbody").children("tr").each(function (i, cell) {
				const checked_row = $(cell).find("input[name='selectallcheckbox']:checked");
				if (checked_row.length > 0) {
					$(checked_row).prop("checked", false);
					$(cell).find("div").removeClass("selectclass");
				}
			});
			$(this).toggleClass("selectclass");
			classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
			if (classgrt.join(",") === "") {
				$(".Postfilterhideshow").addClass("d-none");
			} else {
				$(".Postfilterhideshow").removeClass("d-none");
			}
		});

		$rosterMonth.find(".hoverselectclass").on("click", function () {
			$(this).closest("tbody").children("tr").each(function (i, cell) {
				const checked_row = $(cell).find("input[name='selectallcheckbox']:checked");
				if (checked_row.length > 0) {
					$(checked_row).prop("checked", false);
					$(cell).find("div").removeClass("selectclass");
				}
			});
			$(this).toggleClass("selectclass");
			if ($(".dayoff").is(":hidden")) {
				$(".dayoff").show();
			}
			classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
			if (classgrt.join(",") === "") {
				$(".filterhideshow").addClass("d-none");
			} else {
				$(".filterhideshow").removeClass("d-none");
			}
		});

		$postMonth.find(`input[name="selectallcheckbox"]`).on("change", function () {
			if ($(this).is(":checked")) {
				$(this).parent().parent().parent().children("td").children().not("label").not("span").each(function (i, v) {
					let date = $(v).attr("data-date");
					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
					}
				});
				$(this).parent().parent().parent().children("td").children().not("label").not("span").removeClass("hoverselectclass");
				$(".Postfilterhideshow").removeClass("d-none");
			} else {
				$(this).parent().parent().parent().children("td").children().not("label").not("span").addClass("hoverselectclass");
				$(this).closest("tr").children("td").children().not("label").not("span").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr("data-selectid")), 1);
				});
				$(this).parent().parent().parent().children("td").children().not("label").not("span").removeClass("selectclass");
				$(".Postfilterhideshow").addClass("d-none");
			}
			$(this).closest("tbody").children("tr").each(function (i, cell) {
				const unchecked_row = $(cell).find("input[name='selectallcheckbox']:not(:checked)");
				if (unchecked_row.length > 0) {
					$(cell).find("div").removeClass("selectclass");
				}
			});
			$(".selectclass").map(function () {
				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];
			});
		});

		$rosterMonth.find(`input[name="selectallcheckbox"]`).on("change", function () {
			let $checked_employee = $(this);
			if ($(".dayoff").is(":hidden")) {
				$(".dayoff").show();
			}
			if ($checked_employee.is(":checked")) {
				$checked_employee.closest("tr").children("td").children().not("label").not("span").each(function (i, v) {
					let [employee, date] = $(v).attr("data-selectid").split("|");
					if (moment(date).isAfter(moment())) {
						$(v).addClass("selectclass");
						classgrt.push($(v).attr("data-selectid"));
					}
				});
				$(".filterhideshow").removeClass("d-none");
			} else {
				$checked_employee.closest("tr").children("td").children().not("label").not("span").each(function (i, v) {
					classgrt.splice(classgrt.indexOf($(v).attr("data-selectid")), 1);
				});
				$checked_employee.closest("tr").children("td").children().not("label").not("span").removeClass("selectclass");
				$(".filterhideshow").addClass("d-none");
			}
			$checked_employee.closest("tbody").children("tr").each(function (i, cell) {
				const unchecked_row = $(cell).find("input[name='selectallcheckbox']:not(:checked)");
				if (unchecked_row.length > 0) {
					$(cell).find("div").removeClass("selectclass");
				}
			});;
			$(".selectclass").map(function () {
				classgrt.push($(this).attr("data-selectid"));
				classgrt = [... new Set(classgrt)];
			});
		});

		$("input[name='selectallcheckboxes']").on("change", function () {
			if ($(this).is(":checked")) {
				$(this).parent().parent().parent().children("td").children().not("label").not("span").removeClass("hoverselectclass");
				$(this).parent().parent().parent().children("td").children().not("label").not("span").addClass("selectclass");
				$(this).parent().parent().parent().children("td").children().not("label").not("span").addClass("disableselectclass");
				$(".Postfilterhideshow").removeClass("d-none");
			} else {
				$(this).parent().parent().parent().children("td").children().not("label").not("span").addClass("hoverselectclass");
				$(this).parent().parent().parent().children("td").children().not("label").not("span").removeClass("selectclass");
				$(this).parent().parent().parent().children("td").children().not("label").not("span").removeClass("disableselectclass");
				$(".Postfilterhideshow").addClass("d-none");
			}
			$(".selectclass").map(function () {
				classgrt.indexOf(this.getAttribute("data-selectid")) === -1 ? classgrt.push(this.getAttribute("data-selectid")) : classgrt.splice(classgrt.indexOf(this.getAttribute("data-selectid")), 1);
			});
			if ($(this).parent().parent().parent().children("td").children().hasClass("redboxcolor")) {
				$("#selRetrive").show();
				$(".selPost").hide();
			} else {
				$("#selRetrive").hide();
				$(".selPost").show();
			}
		});
	}

	window.employees_list = [];
	bind_search_bar_event(page);

	$(".checkboxcontainer.simplecheckbox").click((e) => {
		if (window.clickcount > 0) {
			window.clickcount = 0;
		} else {
			let employee = e.target.parentNode.parentNode.parentNode.getAttributeNode("data-name").value;
			if (window.employees_list.includes(employee)) {
				window.employees_list = window.employees_list.filter(function (value, index, arr) {
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
			page.employee_search_name = frappe.utils.xss_sanitise($(wrapper_element).find(".search-employee-name").val());
			if (wrapper_element == ".rosterMonth") {
				get_roster_data(page);
			}
		}
	});
	$(".closed").on("click", function (event) {
		$(wrapper_element).find(".search-employee-name").val("");
		page.employee_search_name = "";
		if (wrapper_element == ".rosterMonth") {
			get_roster_data(page);
		}
	});
	$(wrapper_element).find(".search-employee-id").keypress(function (event) {
		if (event.which == 13) {
			page.employee_search_id = frappe.utils.xss_sanitise($(wrapper_element).find(".search-employee-id").val());
			if (wrapper_element == ".rosterMonth") {
				get_roster_data(page);
			}
		}
	});
	$(".closed").on("click", function (event) {
		$(wrapper_element).find(".search-employee-id").val("");
		page.employee_search_id = "";
		if (wrapper_element == ".rosterMonth") {
			get_roster_data(page);
		}
	});
}


// Setup filters data on left sidebar
function setup_filters(page) {
	frappe.db.get_value("Employee", { "user_id": frappe.session.user }, ["name"])
		.then(async res => {
			let { name } = res.message;
			page.employee_id = name;
			page.search_bar_data = {};
			await get_projects(page);
			await get_sites(page);
			await get_shifts(page);
			await get_operations_roles(page);
			await get_employees(page);
			get_relievers(page);
			
		})
		.then(r => {
			populate_dropdown_options(page);
		})
		.then(r => {
			get_roster_data(page);
		});
}

async function get_projects(page) {
	let { employee_id } = page;
	await frappe.xcall("one_fm.api.mobile.roster.get_assigned_projects", { employee_id })
		.then(res => {
			page.search_bar_data["rosteringprojectselect"] = res;
		});
}

async function get_sites(page) {
	let { employee_id } = page;
	let { project } = page.filters;
	await frappe.xcall("one_fm.api.mobile.roster.get_assigned_sites", { employee_id, project })
		.then(res => {
			page.search_bar_data["rosteringsiteselect"] = res;
		});
}

async function get_shifts(page) {

	let { employee_id } = page;
	let { project, site } = page.filters;
	await frappe.xcall("one_fm.api.mobile.roster.get_assigned_shifts", { employee_id, project, site })
		.then(res => {
			page.search_bar_data["rosteringshiftselect"] = res;
		});
}

async function get_operations_roles(page) {
	let { employee_id, shift } = page;
	await frappe.xcall("one_fm.api.mobile.roster.get_operations_roles", { employee_id, shift })
		.then(res => {
			page.search_bar_data["rosteringroleselect"] = res;
		});
}

async function get_employees(page) {
	await frappe.xcall("one_fm.api.mobile.roster.get_employees")
		.then(res => {
			page.search_bar_data["rosteringemployeeselect"] = res;
		});
}

async function get_departments(page) {
	await frappe.xcall("one_fm.api.mobile.roster.get_departments")
		.then(res => {
			let parent = $("[data-page-route='roster'] #rosteringdepartmentselect");
			
			let department_data = [];
			res.forEach(element => {
				let { name } = element;
				department_data.push({ "id": name, "text": name });
			});
			parent.select2({ data: department_data });

			const selectedDepartment = page.filters["department"];
			if (selectedDepartment) {
				parent.val(selectedDepartment).trigger("change");
			}

			$(parent).on("select2:select", function (e) {
				page.filters.department = $(this).val();
				let element = get_wrapper_element().slice(1);
				page[element](page);
			});

		});
}

async function get_designations(page) {
	await frappe.xcall("one_fm.api.mobile.roster.get_designations")
		.then(res => {
			let parent = $("[data-page-route='roster'] #rosteringdesignationselect");
			let designation_data = [];
			res.forEach(element => {
				let { name } = element;
				designation_data.push({ "id": name, "text": name });
			});
			parent.select2({ data: designation_data });

			const selectedDesignation = page.filters["designation"];
			if (selectedDesignation) {
				parent.val(selectedDesignation).trigger("change");
			}

			$(parent).on("select2:select", function (e) {
				page.filters.designation = $(this).val();
				let element = get_wrapper_element().slice(1);

				page[element](page);
			});
		})
		.catch(e => {
			// console.log(e);
		})
}

function get_relievers(page) {
	let relievers = [
		{ "id": 1, "text": "Relievers Only" },
		{ "id": 0, "text": "Non Relievers Only" },
	];
	page.search_bar_data["rosteringrelieverselect"] = relievers;

}

function get_roster_data(page) {
	classgrt = [];
	let { start_date, end_date } = page;
	let { employee_search_name, employee_search_id, project, site, shift, department, operations_role, designation, reliever } = page.filters;
	let { limit_start } = page.pagination;
	let limit_page_length = 50; // Set default page length
	
	page.pagination.limit_page_length = limit_page_length;
	
	if (project || site || shift || operations_role || reliever || employee_search_id || reliever) {
		$(".clear_roster_filters").removeClass("d-none")
		$("#cover-spin").show(0);
		frappe.call({
			method: "one_fm.one_fm.page.roster.roster.get_roster_view",
			type: "POST",
			args: {
				start_date, end_date, employee_search_id, employee_search_name, project, site,
				shift, department, operations_role, designation, reliever, limit_start, limit_page_length
			},
			callback: function (res) {
				error_handler(res);
				render_roster(res.data, page);
			}
		});
	} else {
		$(".clear_roster_filters").addClass("d-none")
	}
}

let classmap = {
	"Working": "lightblueboxcolor",
	"Day Off": "greyboxcolor",
	"Client Day Off": "silverboxcolor",
	"Sick Leave": "purplebox",
	"Emergency Leave": "purplebox",
	"Annual Leave": "purplebox",
	"ASA": "pinkboxcolor",
	"Day Off OT": "yellowboxcolor",
	"Present": "greenboxcolor",
	"Absent": "redboxcolor",
	"Work From Home": "greenboxcolor",
	"Half Day": "greenboxcolor",
	"On Leave": "purplebox",
	"Holiday": "greyboxcolor",
	"On Hold": "orangeboxcolor"
};

let abbr_map = {
	"Present": "P",
	"Absent": "A",
	"Work From Home": "WFH",
	"Half Day": "HD",
	"Holiday": "H",
	"On Leave": "OL",
	"On Hold": "OH",
	"Day Off": "DO",
	"Client Day Off": "CDO",
	"Sick Leave": "SL",
	"Annual Leave": "AL",
	"Emergency Leave": "EL",
	"Leave Without Pay": "LWP",
	"Working": "!"

};


function render_roster(res, page) {
	let { operations_roles_data, employees_data, total } = res;
	page.pagination.total = total;
	let $rosterMonth = $(".rosterMonth");
	let $rosterMonthbody = $rosterMonth.find("#calenderviewtable tbody");
	$rosterMonthbody.empty();

	for (operations_role_name in operations_roles_data) {
		let pt_row_html = `
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
		$rosterMonthbody.append(pt_row_html);
		let $roleRow = $rosterMonthbody.find(`tr[data-name="${escape_values(operations_role_name)}"]`);

		let { start_date, end_date } = page;
		let current_day = moment(start_date); 
		let end_moment = moment(end_date);
		let i = 0;
		
		while (current_day <= end_moment) {
			// Ensure operations_roles_data has data for the current index
			if (operations_roles_data[operations_role_name] && operations_roles_data[operations_role_name][i]) {
				let { date, operations_role, count, highlight } = operations_roles_data[operations_role_name][i];
				let pt_count_html = `
				<td class="${highlight}">
					<div class="text-center" data-selectid="${operations_role + "|" + date}">${count}</div>
				</td>`;
				$roleRow.append(pt_count_html);
			} else {
				// Append an empty cell if data is missing, to maintain table structure
				$roleRow.append("<td><div class='text-center'>&nbsp;</div></td>");
			}
			i++;
			current_day.add(1, "days");
		}
		$roleRow.append(`<td></td>`); // Total column
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
	let $employeeTableBody = $rosterMonth.find("#rowchildtable tbody");

	const transformed = Object.keys(employees_data)
		.sort()
		.reduce((acc, employeeKey) => {
			const dateToRecords = employees_data[employeeKey];
			const sortedDates = Object.keys(dateToRecords).sort();
			acc[employeeKey] = sortedDates.map(date => dateToRecords[date]);
			return acc;
		}, {});

	for (employee_key in transformed) {
		let { start_date, end_date } = page; 
		// Assuming the first record on the start_date has the necessary employee details
		let first_day_records = employees_data[employee_key][start_date];
		if (!first_day_records || first_day_records.length === 0) continue; // Skip if no data for start_date

		let employee = first_day_records[0]["employee"];
		let employee_id = first_day_records[0]["employee_id"];
		let employee_day_off = first_day_records[0]["day_off_category"][0] || "";
		let employee_relieving_date_str = first_day_records[0]["relieving_date"];
		let employee_relieving_date = employee_relieving_date_str ? moment(employee_relieving_date_str) : null;
		let filter_assignment = '';
		
		let actual_filter = "actual_";
		let applied_filter = 
			page.filters.shift ? "shift" :
			page.filters.site ? "site" :
			page.filters.project ? "project" : "";

		if (applied_filter) actual_filter += applied_filter;

		if (page.filters.operations_role) { filter_assignment = `Role: ${page.filters.operations_role}`; }
		else if (page.filters.shift) { filter_assignment = `Shift: ${first_day_records[0][actual_filter] || page.filters.shift}`; }
		else if (page.filters.site) { filter_assignment = `Site: ${first_day_records[0][actual_filter] || page.filters.site}`; }
		else if (page.filters.project) { filter_assignment = `Project: ${first_day_records[0][actual_filter] || page.filters.project}`; }
				

		if (first_day_records[0]["number_of_days_off"]) {
			employee_day_off += "-" + first_day_records[0]["number_of_days_off"];
		}

		let emp_row_html = `
			<tr data-name="${employee}">
				<td class="sticky">
					<label class="checkboxcontainer simplecheckbox">
						<span class="lightgrey font16 customfontweight fontw400 postname" style="color:black">${employee_key}</span>
						<input type="checkbox" name="selectallcheckbox" class="selectallcheckbox">
						<span class="checkmark"></span>
					</label>
					<label class="d-flex w-100 pt-1 justify-content-between align-items-center">
						<span class="lightgrey d-flex employee_day_off"><span title="${filter_assignment}" id="employee_id">${filter_assignment}</span></span>
						<span class="badge badge-secondary" style="font-size:0.8rem; font-weight: 300">${employee_day_off}</span>		
					</label>
				</td>
			</tr>`;
		$employeeTableBody.append(emp_row_html);
		let $employeeRow = $employeeTableBody.find(`tr[data-name="${employee}"]`);

		let current_day_iter = moment(start_date); // Use a new moment object for iteration
		let end_moment_iter = moment(end_date);
		let basic_count = 0;
		let ot_count = 0;
		let employeeCellsHTML = ""; // Initialize for batch append

		while (current_day_iter <= end_moment_iter) {
			let sch = ``;
			let date_key = current_day_iter.format("YYYY-MM-DD");
			let abbrv = ``;
			let data_selectid = ``; 
			let data_ot = ``;
			let tooltiptext = ``;
			let bgclass = ``;

			let is_relieved_this_day = employee_relieving_date && current_day_iter.isSameOrAfter(employee_relieving_date);

			if (employees_data[employee_key][date_key] && employees_data[employee_key][date_key].length > 0) {
				for (let k = 0; k < employees_data[employee_key][date_key].length; k++) {
					let record = employees_data[employee_key][date_key][k];
					let { employee, date, operations_role, post_abbrv, employee_availability, shift, start_datetime, end_datetime, start_time, end_time, roster_type, attendance, day_off_ot, leave_type, leave_application } = record;
					let shift_start = start_time ? moment(start_time, "HH:mm").format("LT") : moment(start_datetime, "YYYY-MM-DD HH:mm:ss").format("LT") ;
					let shift_end = end_time ? moment(end_time, "HH:mm").format("LT") : moment(end_datetime, "YYYY-MM-DD HH:mm:ss").format("LT");

					if (!attendance && roster_type == "Basic" && page.filters[applied_filter] == record[applied_filter] && day_off_ot == 0 ) {
						if(employee_availability == "Working") {
							basic_count++;
							bgclass = "samebasic";
							data_selectid = `${employee}|${date}|${operations_role}|${shift}|${employee_availability}`;
						} else if (employee_availability && !post_abbrv){
							bgclass = classmap[employee_availability]; 	
							data_selectid = `${employee}|${date}|${employee_availability}`;	
						}
					}
					else if (!attendance && roster_type == "Basic" && page.filters[applied_filter] != record[applied_filter] && day_off_ot == 0 ){
						if(employee_availability == "Working") {
							basic_count++;
							bgclass = "diffbasic"; 						
							data_selectid = `${employee}|${date}|${operations_role}|${shift}|${employee_availability}`;
						} else if (employee_availability && !post_abbrv){
							bgclass = classmap[employee_availability]; 	
							data_selectid = `${employee}|${date}|${employee_availability}`;	
						}
					}
					else if (!attendance && roster_type == "Over-Time" && page.filters[applied_filter] == record[applied_filter]) {
						ot_count++;
						bgclass = bgclass ? `${bgclass}-sameot` : "sameot"; 
						data_ot = `${employee}|${date}|${operations_role}|${shift}|${employee_availability}`;
					}
					else if (!attendance && roster_type == "Over-Time" && page.filters[applied_filter] != record[applied_filter]) {
						ot_count++;
						bgclass = bgclass ? `${bgclass}-diffot` : "diffot";
						data_ot = `${employee}|${date}|${operations_role}|${shift}|${employee_availability}`;
					}
					else if (!attendance && roster_type == "Basic" && page.filters[applied_filter] == record[applied_filter] && day_off_ot == 1 ){
						if(employee_availability == "Working") basic_count++;
						bgclass = "samedayoffot"; 
						data_selectid = `${employee}|${date}|${operations_role}|${shift}|${employee_availability}`;
					}
					else if (!attendance && roster_type == "Basic" && page.filters[applied_filter] != record[applied_filter] && day_off_ot == 1 ){
						if(employee_availability == "Working") basic_count++;
						bgclass = "diffdayoffot";
						data_selectid = `${employee}|${date}|${operations_role}|${shift}|${employee_availability}`;
					}
					else if (attendance && in_list(["Day Off", "On Leave", "Absent", "On Hold"], attendance)) {
						data_selectid = `${employee}|${date}|${employee_availability}`; 
						if (attendance == "Absent") {
							if (roster_type == "Over-Time") { bgclass = bgclass ? `${bgclass}-absentot` : "absentot" }
							else if (roster_type == "Basic" && day_off_ot == 1) { bgclass = "absentdayoffot" }
							else { bgclass = "absentbasic" } 
						} 
						else { bgclass = classmap[attendance] }
					}
					else if (attendance && attendance == "Present") {
						data_selectid = `${employee}|${date}|${operations_role}|${shift}|${employee_availability}`;
						if (roster_type == "Over-Time") { 
							ot_count++;
							bgclass = bgclass ? `${bgclass}-presentot` : "presentot"; 
						} else if (roster_type == "Basic" && day_off_ot == 1) { 
							basic_count++;
							bgclass = "presentdayoffot"; 
						} else { 
							basic_count++;
							bgclass = "presentbasic";
						}
					}

					if (k == (employees_data[employee_key][date_key].length - 1)) {
						if (attendance && attendance == "On Leave" && !employee_availability) {
							tooltiptext += `${leave_application}<br>${leave_type}`;
							abbrv += `${abbr_map[attendance]}<br>`;
						} else if (attendance && !employee_availability){
							tooltiptext += `${roster_type}:<br>${shift}<br>Start: ${shift_start}<br>End: ${shift_end}`;
							abbrv += `${abbr_map[attendance]}<br>`;
						} else if (employee_availability && !post_abbrv) {
							tooltiptext = ``;
							abbrv += `${abbr_map[employee_availability]}<br>`;
						} else {
							tooltiptext += `${roster_type}:<br>${shift }<br>Start: ${shift_start}<br>End: ${shift_end}<br>`;
							abbrv += `${post_abbrv}<br>`;				
						}
					} else {
						if (attendance && !employee_availability) {
							abbrv += `${abbr_map[attendance]}<br>`;
						} else if (employee_availability && !post_abbrv){
							abbrv += `${abbr_map[employee_availability]}<br>`;
						} else {
							abbrv += `${post_abbrv}<br>`;				
						}
						tooltiptext += `${roster_type}:<br>${shift}<br>Start: ${shift_start}<br>End: ${shift_end}<br>`;
					}
				}
			}

			if (is_relieved_this_day) {
				sch = `
					<td>
						<div class="${moment().isBefore(current_day_iter) ? "hoverselectclass" : "forbidden"} tablebox darkblackox d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${data_selectid}">EX<span class="customtooltiptext">Exited</span></div>
					</td>`;
			} else if (!data_selectid && !data_ot) { 
				sch = `
					<td>
						<div class="${moment().isBefore(current_day_iter) ? "hoverselectclass" : "forbidden"} tablebox borderbox d-flex justify-content-center align-items-center so"
							data-selectid="${employee}|${date_key}"></div>
					</td>`;
			} else {
				let tooltip_html = tooltiptext ? `<span class="customtooltiptext ${bgclass}">${tooltiptext}</span>` : ""; 
				sch = `
					<td>
						<div class="${moment().isBefore(current_day_iter) ? "hoverselectclass" : "forbidden"} tablebox ${bgclass} d-flex justify-content-center align-items-center text-white so customtooltip"
							data-selectid="${data_selectid}" data-ot="${data_ot}">${abbrv}${tooltip_html}</div>
					</td>`;
			}
			employeeCellsHTML += sch;
			current_day_iter.add(1, "days");
		}
		$employeeRow.append(employeeCellsHTML);
		$employeeRow.append(`<td><span>${basic_count}<br>${ot_count}</span></td>`);
	}

	// Add new pagination controls
	let totalPages = Math.ceil(page.pagination.total / page.pagination.limit_page_length);
	let currentPage = (page.pagination.limit_start / page.pagination.limit_page_length) + 1;

	let paginationControlsHTML = `<div class="custom-pagination-controls">`;
	if (currentPage > 1) {
		paginationControlsHTML += `<button class="btn btn-default btn-sm prev-page">Previous</button>`;
	}
	paginationControlsHTML += `<span class="page-info"> Page ${currentPage} of ${totalPages} </span>`;
	if (currentPage < totalPages) {
		paginationControlsHTML += `<button class="btn btn-default btn-sm next-page">Next</button>`;
	}
	paginationControlsHTML += `</div>`;

	$('#myPager').html(paginationControlsHTML);
	$('#myPager').off('click', '.next-page').on('click', '.next-page', function() {
		page.pagination.limit_start += page.pagination.limit_page_length;
		get_roster_data(page);
	});

	$('#myPager').off('click', '.prev-page').on('click', '.prev-page', function() {
		page.pagination.limit_start -= page.pagination.limit_page_length;
		get_roster_data(page);
	});

	bind_events(page);
}


// Get data for Post view monthly and render it
function get_post_data(page) {
	classgrt = [];

	let { start_date, end_date } = page;
	let { project, site, shift, department, operations_role } = page.filters;
	let { limit_start, limit_page_length } = page.pagination;
	if (project || site || shift || department || operations_role) {
		$("#cover-spin").show(0);

		frappe.xcall("one_fm.one_fm.page.roster.roster.get_post_view", { start_date, end_date, project, site, shift, operations_role, limit_start, limit_page_length })
			.then(res => {
				$("#cover-spin").hide();
				page.pagination.total = res.total;
				let $postMonth = $(".postMonth");
				let $postMonthbody = $(".postMonth").find("#calenderviewtable tbody");
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
							"Planned": "bluebox",
							"Post Off": "greyboxcolor",
							"Suspended": "yellowboxcolor",
							"Cancelled": "redboxcolor"
						};

						let { project, site, shift, date, post_status, operations_role, post, name } = res["post_data"][post_name][i];
						if (name) {
							schedule = `
						<td>
							<div class="${moment().isBefore(moment(date)) ? "hoverselectclass" : "forbidden"} tablebox ${classmap[post_status]} d-flex justify-content-center align-items-center so"
								data-selectid="${post + "_" + date}"
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
							<div class="${moment().isBefore(moment(date)) ? "hoverselectclass" : "forbidden"} tablebox darkblackox d-flex justify-content-center align-items-center so"
								data-selectid="${post_name + "_" + start_date.format("YYYY-MM-DD")}"
								data-date="${start_date.format("YYYY-MM-DD")}"
								data-post="${post_name}"
							</div>
						</td>`;
						}
						i++;
						start_date.add(1, "days");
						$postMonth.find(`#calenderviewtable tbody tr[data-name="${escape_values(post_name)}"]`).append(schedule);
					}
					$postMonth.find(`#calenderviewtable tbody tr[data-name="${escape_values(post_name)}"]`).append(`<td></td>`);
				}


				bind_events(page);
			}).catch(e => {
				console.log(e);
			});
	}
}

function escape_values(string) {
	if (typeof string !== "string") return ""; // Handle non-string inputs
	return string.replace(/"/g, '\\"').replace(/"/g, "\\'");
}


//////////////////////////////////////////////////////////////////////////////////////////////////////////////////

//Increment month post/roster view
function incrementMonth(page) {
	if (!page) {
		page = cur_page.page.page;
	}
	calendarSettings1.date.add(1, "Months");

	let element = get_wrapper_element();
	if (element == ".rosterMonth" || element == ".postMonth") {
		GetHeaders(1);
		displayCalendar(calendarSettings1, page);
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
	if (element == ".rosterMonth" || element == ".postMonth") {
		GetHeaders(1);
		displayCalendar(calendarSettings1, page);
		element = element.slice(1);
		page[element](page);
	}
}
//Decrement month post/roster view


function displayCalendar(calendarSettings1, page) {
	if (!page) {
		page = cur_page.page.page;
	}
	let calendar_month = $(".calendarmonth")[0];
	const calendarTitle1 = calendarSettings1.date.format("MMMM");
	const calendaryear1 = calendarSettings1.date.format("YYYY");
	calendar_month.innerHTML = "";
	calendar_month.innerHTML = `${calendarTitle1} ${calendaryear1}`;
	page.start_date = calendarSettings1.date.startOf("Month").format("YYYY-MM-DD");
	page.end_date = calendarSettings1.date.endOf("Month").format("YYYY-MM-DD");

}


//function for changing roster date
function ChangeRosteringDate(seldate, this1) {
	var date = calendarSettings1.today.format("DD");
	var month = calendarSettings1.date.format("MM") - 1;
	var year = calendarSettings1.date.format("YYYY");
	var d1 = new Date(year, month, date);
	$(this1).parent().children().removeClass("hightlightedtable");
	$(this1).addClass("hightlightedtable");
}
//function for changing roster date

//Get the visible roster/post view parent
function get_wrapper_element(element) {
	if (element) return element;
	let roster_element = $(".rosterMonth").attr("class").split(/\s+/).includes("d-none");
	let post_element = $(".postMonth").attr("class").split(/\s+/).includes("d-none");

	if (roster_element && !post_element) {
		element = ".postMonth";
		return element;
	} else if (!roster_element && post_element) {
		element = ".rosterMonth";
		return element;
	}
	return ".rosterMonth";
}

const search_staff = () => {
	let key = $("input[name='searchbyradiobtn']:checked").val();
	let search_term = $("#inputtextsearch").val();
	let view = $(".layoutSidenav_content").attr("data-view");

	frappe.xcall("one_fm.one_fm.page.roster.roster.search_staff", { key, search_term })
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
			if (todayDay == "Fri" || todayDay == "Sat") {
				th = "<th class='greytablebg vertical-sticky' style='z-index:1' id='data-day_" + i + "' onclick='ChangeRosteringDate(' + i + ',this)'>" + calDate.format("ddd") + " " + calDate.format("DD") + "</th>";
			} else if (todayDaydate === getdateres) {
				th = "<th class='hightlightedtable vertical-sticky' style='z-index:1' id='data-day_" + i + "' onclick='ChangeRosteringDate(" + i + ",this)'>" + calDate.format("ddd") + " " + calDate.format("DD") + "</th>";
			} else {
				th = "<th class='vertical-sticky' style='z-index:1' id='data-day_" + i + "' onclick='ChangeRosteringDate(" + i + ",this)'>" + calDate.format("ddd") + " " + calDate.format("DD") + "</th>";
			}
			dataHTML = dataHTML + th;
		}
		thHTML = thStartHTML + dataHTML + thEndHTML;

		$(element).find(".rosterViewTH").html("");
		$(element).find(".rosterViewTH").html(thHTML);
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
			if (todayDay == "Fri" || todayDay == "Sat") {
				th = "<th class='greytablebg vertical-sticky' style='z-index:1' id='data-day_" + i + "' onclick='ChangeRosteringDate(" + i + ",this)'>" + calDate.format("ddd") + " " + calDate.format("DD") + "</th>";
			}
			else {
				th = "<th class='vertical-sticky' style='z-index:1' id='data-day_" + i + "' onclick='ChangeRosteringDate(" + i + ",this)'>" + calDate.format("ddd") + " " + calDate.format("DD") + "</th>";
			}
			dataHTML = dataHTML + th;

		}

		thHTML = thStartHTML + dataHTML + thEndHTML;
		$(element).find(".rosterViewTH").html("");
		$(element).find(".rosterViewTH").html(thHTML);


	}

	var month = moment(new Date()).format("MM");
	var month1 = calendarSettings1.date.format("MM");
	if (month == month1) { GetTodaySelectedDate(); }

}
//function for dynamic set calender header data on right calender



//datatable function call for staff
function staffmanagement() {
	let table;
	if ($.fn.dataTable.isDataTable("[data-page-route='roster'] #staffdatatable")) {
		table = $("[data-page-route='roster'] #staffdatatable").DataTable();
		table.clear();
		table.destroy();
	}
	table = $("[data-page-route='roster'] #staffdatatable").on("processing.dt", function (e, settings, processing) {
		$(".dataTables_processing")
			.css("display", processing ? "flex" : "none");
	}).on("preXhrpreXhr.dt", function (e, settings, data) {
	}).DataTable({
		"dom": "<'top'fl><'position-relative table-responsive customtableborder'tr><'bottom'ip><'clear'>",
		"paging": true,
		"processing": true,
		"ordering": true,
		"info": true,
		"autowidth": true,

		"language": {
			"loadingRecords": "Loading...",
			"processing": "Processing...",
			"search": "<i class='fas fa-search'></i>",
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

	if (filtervale == "Assigned" && value1 == 0) {
		$(".editbtn").removeClass("d-none");
		$(".mobile-edit").removeClass("d-none");
		$(".mainclassfilter").removeClass("d-none");
		$(".allfilters").addClass("d-none");
	}
	else if (filtervale == "Unassigned" && value1 == 0) {
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

	if (project || site || shift || department || operations_role || designation) {
		$(".clear_staff_filters").removeClass("d-none")
	} else {
		$(".clear_staff_filters").addClass("d-none")
	}

	frappe.xcall("one_fm.one_fm.page.roster.roster.get_staff", filters)
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
	if ($.fn.dataTable.isDataTable("[data-page-route='roster'] #staffdatatable")) {
		table = $("[data-page-route='roster'] #staffdatatable").DataTable();
		table.clear();
		table.destroy();
	}
	let $staffdatatable = $("#staffdatatable tbody");
	data.forEach(function (employee) {


		let { name, employee_id, employee_name, nationality, mobile_no, email, designation, project, site, shift, department, site_supervisor, shift_supervisor, custom_operations_role_allocation, custom_is_reliever } = employee;
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
				${employee_name || "N/A"}
			</td>
			<td>
				${nationality || "N/A"}
			</td>
			<td>
				${mobile_no || "N/A"}
			</td>
			<td>
				${email || "N/A"}
			</td>
			<td>
				${designation || "N/A"}
			</td>
			<td>
				${project || "N/A"}
			</td>
			<td>
				${site || "N/A"}
			</td>
			<td>
				${site_supervisor || "N/A"}
			</td>
			<td>
				${shift || "N/A"}
			</td>
			<td>
				${shift_supervisor || "N/A"}
			</td>
			<td>
				${department || "N/A"}
			</td>
			<td>
				${custom_operations_role_allocation || "N/A"}
			</td>
			<td>
				${custom_is_reliever ? "Yes" : "No"}
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
	$(".staff-card-wrapper").empty();
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
										<img src="${image ? image : "images/userfill.svg"}" class="img_responsive">
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
											<div class="show-read-more cardtitlecolor font20 ">${employee_name || "N/A"}</div>
											<label class="checkboxcontainer d-none d-md-block"><span
													class="text-white"></span><input type="checkbox"
													name="cardviewcheckbox" class="cardviewcheckbox" data-employee-id="${name}"><span
													class="checkmark rightcheckbox"></span></label>
										</div>
									</div>
									<div class="font16 pb8 lightgrey show-read-more">
										<span class="">${designation || "N/A"}</span>
									</div>
									<div class="font16 pb8 lightgrey show-read-more">
										<span class="">${department || "N/A"}</span>
									</div>
									<div class="font16 pb8 lightgrey show-read-more ">
										<!--<span><img src="images/icon/calendar.svg" class="responiconfont"></span>-->
										<span class="pl6">${nationality || "N/A"}</span>
									</div>
									<div class="font16 pb8 lightgrey show-read-more ">
										<span><img src="images/icon/phone.svg" class="responiconfont"></span>
										<span class="pl6">${mobile_no || "N/A"}</span>
									</div>
									<div class="font16 pb8 lightgrey show-read-more ">
										<span><img src="images/icon/Email.svg" class="responiconfont"></span>
										<span class="pl6">${email || "N/A"}</span>
									</div>
								</div>
								<div class="topportion bordertopdotted">
									<div class="d-flex justify-content-between pr12">
										<div class="pt8 w-100 overflow-hidden">
											<div class="font16 pb8 show-read-more">
												<span class="lightgrey customwidthcard">Project: </span>
												<span class="cardidcolor font-medium">
												${project || "N/A"}</span>
											</div>
											<div class="font16 pb8 show-read-more">
												<span class="lightgrey customwidthcard">Site: </span>
												<span class="cardidcolor font-medium">${site || "N/A"}</span>
											</div>
											<div class="font16 pb8 show-read-more">
												<span class="lightgrey customwidthcard">Shift: </span>
												<span class="cardidcolor font-medium">${shift || "N/A"}</span>
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
		$(".staff-card-wrapper").append(row);
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
		assigned: pageFilters.assigned === "0" ? 0 : 1,
		company: pageFilters.company ,
		project: pageFilters.project ,
		site: pageFilters.site ,
		shift: pageFilters.shift ,
		department: pageFilters.department ,
		designation: pageFilters.designation ,
		operations_role: pageFilters.operations_role ,
		employee_search_name: employeeFilters.employee_name ,
		employee_search_id: employeeFilters.employee_id ,
		reliever: pageFilters.reliever ,
	};
	let pagination = {
		limit_start: 0,
		limit_page_length: 100
	};
	if (page) {
		page.filters = filters;
		page.pagination = pagination;
		page.employee_search_id = employeeFilters.employee_id 
		page.employee_search_name = employeeFilters.employee_name 
	} else {
		cur_page.page.page.filters = filters;
		cur_page.page.page.pagination = pagination;
	}

}

function setup_staff_filters_data() {
	frappe.xcall("one_fm.one_fm.page.roster.roster.get_staff_filters_data")
		.then(res => {
			cur_page.page.page.staff_filters_data = res;
			let { company, projects, sites, shifts, departments, designations } = res;
			let $companydropdown = $(".company-dropdown");
			let $projectdropdown = $(".project-dropdown");
			let $sitedropdown = $(".site-dropdown");
			let $shiftdropdown = $(".shift-dropdown");
			let $departmentdropdown = $(".department-dropdown");
			let $designationdropdown = $(".designation-dropdown");
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
				let filter_type = $(this).parent().attr("data-filter-type");
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
	let filter_type = $(e).attr("data-filter-type");
	let filter_text = filter_type.charAt(0).toUpperCase() + filter_type.slice(1);
	$(e).closest(".btn-group").find(".dropdown-toggle .dropdowncustomres").html(filter_text);
	cur_page.page.page.filters[filter_type] = "";
	render_staff($(".layoutSidenav_content").attr("data-view"));
}

function staff_edit_dialog() {
	let employees = [];
	$(".checkboxcontainer").map(function (i, data) {
		let selected = data.querySelectorAll("input[type='checkbox']:checked");
		if (selected.length) {
			let id = ""
			id = selected[0].getAttribute("data-employee-id");
			if (id) {
				employees.push(id);
			}
		}
	});

	let d = new frappe.ui.Dialog({
		"title": "Edit",
		"fields": [
			{
				"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", get_query: function () {
					return {
						"filters": {
							"project_type": "External"
						},
						"page_length": 9999
					};
				}
			},
			{
				"label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Operations Site", get_query: function () {
					let project = d.get_value("project");
					if (project) {
						return {
							"filters": { project },
							"page_length": 9999
						};
					}
				}
			},
			{
				"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Operations Shift", "reqd": 1, get_query: function () {
					let site = d.get_value("site");
					if (site) {
						return {
							"filters": { site, "status": "Active" },
							"page_length": 9999
						};
					}
				},

				onchange: function () {
					let name = d.get_value("shift");
					if (name) {
						frappe.db.get_value("Operations Shift", name, ["site", "project"])
							.then(res => {
								let { site, project } = res.message;
								d.set_value("site", site);
								d.set_value("project", project);
							});
					}
				}
			},
			{
				"label": "Is Reliever", "fieldname": "custom_is_reliever", "fieldtype": "Check", onchange: function () {
					let is_reliever = d.get_value("custom_is_reliever");
					d.set_df_property("custom_operations_role_allocation", "reqd", !is_reliever);
				}
			},
			{
				"label": "Default Operations Role", "fieldname": "custom_operations_role_allocation", "fieldtype": "Link", "options": "Operations Role", "reqd": 1, get_query: function () {
					let shift = d.get_value("shift");
					if (shift) {
						return {
							"filters": { shift },
							"page_length": 9999
						};
					}
				}
			}
		],
		primary_action: function () {
			let { shift, custom_operations_role_allocation, custom_is_reliever } = d.get_values();

			$("#cover-spin").show(0);
			frappe.call({
				method: "one_fm.one_fm.page.roster.roster.assign_staff",
				args: { employees, shift, custom_operations_role_allocation, custom_is_reliever },
				callback: function (r) {

					d.hide();
					$("#cover-spin").hide();
					update_staff_view();
					frappe.msgprint(__("Successful!"));
				},
				freeze: true,
				freeze_message: __("Editing Post....")
			});
		}
	});

	// Pre-populate if only one employee is selected
	if (employees.length === 1) {
		frappe.call({
			method: "one_fm.one_fm.page.roster.roster.get_employee_details",
			args: { employee_id: employees[0] },
			callback: function (r) {
				if (r.message) {
					let employee_details = r.message;
					// Populate fields
					d.set_value("project", employee_details.project);
					d.set_value("site", employee_details.site);
					d.set_value("shift", employee_details.shift);
					d.set_value("custom_is_reliever", employee_details.custom_is_reliever);
					d.set_value("custom_operations_role_allocation", employee_details.custom_operations_role_allocation);
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


//function for get selected date
function GetTodaySelectedDate() {
	var tdate = weekCalendarSettings.today.format("DD");
	let element = get_wrapper_element(); // Removed .slice(1) as get_wrapper_element returns the selector string
	if (element) { // Ensure element is not undefined
		$(element).find("#data-day_" + tdate).addClass("hightlightedtable");
	}
}


function unschedule_staff(page) {
	let employees = [];
	let selected = [... new Set(classgrt)];
	selected.forEach(function (i) {
		let [employee, date] = i.split("|");
		employees.push({ employee, date });
	});
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), "1");
	let d = new frappe.ui.Dialog({
		"title": "Unschedule Staff",
		"fields": [
			{
				"label": "Roster Type", "fieldname": "roster_type", "fieldtype": "Select", "options": "Basic\nOver-Time", "default": "Basic"
			},
			{
				"label": "Selected Days Only", "fieldname": "selected_days_only", "fieldtype": "Check", "default": 0, onchange: function () {
					let val = d.get_value("selected_days_only");
					if (val) {
						d.set_value("start_date", "");
						d.set_value("never_end", 0);
						d.set_value("select_end", 0);
						d.set_value("end_date", "");
					}
				}
			},
			{ "fieldtype": "Section Break", "depends_on": "eval:doc.selected_days_only == 0" },
			{
				"label": "Start Date", "fieldname": "start_date", "fieldtype": "Date", "reqd": 1, "mandatory_depends_on": "eval:doc.selected_days_only == 0", "default": date, onchange: function () {
					let start_date = d.get_value("start_date");
					if (start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						frappe.throw(__("Start Date cannot be before today."));
					}
				}
			},
			{ "fieldtype": "Section Break", "depends_on": "eval:doc.selected_days_only == 0" },
			{
				"label": "Never End", "fieldname": "never_end", "fieldtype": "Check", onchange: function () {
					let val = d.get_value("never_end");
					if (val) {
						d.set_value("select_end", 0);
					}
				}
			},
			{ "fieldtype": "Column Break" },
			{
				"label": "Select End Date", "fieldname": "select_end", "fieldtype": "Check", onchange: function () {
					let val = d.get_value("select_end");
					if (val) {
						d.set_value("never_end", 0);
					}
				}
			},
			{ "fieldtype": "Section Break", "depends_on": "eval:doc.select_end == 1" },
			{
				"label": "End Date", "fieldname": "end_date", "fieldtype": "Date", onchange: function () {
					let end_date = d.get_value("end_date");
					let start_date = d.get_value("start_date");
					if (end_date && moment(end_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						frappe.throw(__("End Date cannot be before today."));
					}
					if (start_date && end_date && moment(end_date).isBefore(moment(start_date))) { // Corrected: end_date before start_date
						frappe.throw(__("End Date cannot be before Start Date."));
					}
				}
			}
		],
		primary_action: function () {
			$("#cover-spin").show(0);
			let { roster_type, selected_days_only, start_date, end_date, never_end } = d.get_values();

			frappe.call({
				method: "one_fm.one_fm.page.roster.roster.unschedule_staff",
				type: "POST",
				args: { employees, roster_type, start_date, end_date, never_end, selected_days_only },
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



function schedule_change_post(page) {
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), "1");
	let employees = [];
	let selected = [... new Set(classgrt)];
	if (selected.length > 0) {
		selected.forEach(function (i) {
			let [employee, date] = i.split("|");
			employees.push({ employee, date });
			employees = [... new Set(employees)]; // This might be redundant if items are unique from classgrt
		});
	}
	var hide_day_off_ot_check = 0;
	var hide_keep_days_off_check = 0;
	// let element = get_wrapper_element(); // element is not used here

	let d = new frappe.ui.Dialog({
		"title": "Schedule/Change Basic",
		"fields": [
			{
				"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Operations Shift", "reqd": 1, onchange: function () {
					let name = d.get_value("shift");
					if (name) {
						frappe.db.get_value("Operations Shift", name, ["site", "project"])
							.then(res => {
								let { site, project } = res.message;
								d.set_value("site", site);
								d.set_value("project", project);
							});
					}
				}, get_query: function () {
					return {
						"filters": { "status": "Active" },
						"page_length": 9999
					};
				}
			},
			{ "label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Operations Site", "read_only": 1 },
			{ "label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "read_only": 1 },
			{
				"label": "Choose Operations Role", "fieldname": "operations_role", "fieldtype": "Link", "reqd": 1, "options": "Operations Role", get_query: function () {
					return {
						query: "one_fm.one_fm.page.roster.roster.get_filtered_operations_role",
						filters: { "shift": d.get_value("shift") }
					};
				}
			},
			{ "fieldname": "cb1", "fieldtype": "Section Break" },
			{
				"label": "Selected Days Only", "fieldname": "selected_days_only", "fieldtype": "Check", "default": 0, onchange: function () {
					if (d.get_value("selected_days_only") == 1) {
						// Set the date to null and refresh the field
						d.fields_dict.end_date.df.read_only  = 1;
						d.fields_dict.start_date.df.read_only  = 1;
						d.fields_dict.project_end_date.df.read_only  = 1;
						d.fields_dict.project_end_date.df.hidden  = 1;
						d.fields_dict.project_end_date.value  = '';
						// d.fields_dict.end_date.refresh()
						// d.fields_dict.start_date.refresh()
						// d.fields_dict.project_end_date.refresh()
						d.refresh_fields(["end_date", "start_date", "project_end_date"]);
					} else {
						d.fields_dict.end_date.df.read_only = 0;
						d.fields_dict.start_date.df.read_only = 0;
						d.fields_dict.project_end_date.df.read_only = 0;
						d.fields_dict.project_end_date.df.hidden = 0;
						d.refresh_fields(["end_date", "start_date", "project_end_date"]); // Refresh fields
					}
				}
			},
			{ "fieldname": "cb2", "fieldtype": "Section Break" },
			{
				"label": "From Date", "fieldname": "start_date", "fieldtype": "Date", "default": date, onchange: function () {
					let start_date = d.get_value("start_date");
					let end_date = d.get_value("end_date");
					if (start_date && moment(start_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						d.set_value("start_date", null); // Clear value
						frappe.throw(__("Start Date cannot be before today."));
					}
					if (start_date && end_date && moment(end_date).isBefore(moment(start_date))) {
						d.set_value("start_date", null); // Clear value
						frappe.throw(__("From Date cannot be after Till Date."));
					}
				}
			},
			{ "label": "Project End Date", "fieldname": "project_end_date", "fieldtype": "Check", default: 0 },
			{ "label": "Keep Days Off", "fieldname": "keep_days_off", "fieldtype": "Check", default: 0, "hidden": hide_keep_days_off_check },
			{ "label": "Request Employee Schedule", "fieldname": "request_employee_schedule", "fieldtype": "Check" },
			{ "label": "Day Off OT", "fieldname": "day_off_ot", "fieldtype": "Check", "hidden": hide_day_off_ot_check },
			{ "fieldname": "cb1", "fieldtype": "Column Break" },
			{
				"label": "Till Date", "fieldname": "end_date", "fieldtype": "Date", "depends_on": "eval:doc.project_end_date==0", default: 0, onchange: function () {
					let end_date = d.get_value("end_date");
					let start_date = d.get_value("start_date");
					if (end_date && moment(end_date).isSameOrBefore(moment(frappe.datetime.nowdate()))) {
						d.set_value("end_date", null); // Clear value
						frappe.throw(__("End Date cannot be before today."));
					}
					if (start_date && end_date && moment(end_date).isBefore(moment(start_date))) {
						d.set_value("end_date", null); // Clear value
						frappe.throw(__("End Date cannot be before Start Date."));
					}
				}
			},
		],
		primary_action: function () {
			let values = d.get_values(); 
			$("#cover-spin").show(0);
			let wrapper_element_selector = get_wrapper_element(); 
			if (wrapper_element_selector == ".rosterMonth") {
				values.otRoster = false; 
			}

			if (!employees || employees.length === 0) { 
				frappe.throw(__("Please select employees to roster."))
				$("#cover-spin").hide(); 
				return; 
			}
			
			if (!values.project_end_date) { values.project_end_date = 0 }
			if (!values.end_date) { values.end_date = "" }
			values.employees = employees; 
			frappe.call({
				method: "one_fm.one_fm.page.roster.roster.schedule_staff",
				type: "POST",
				args: values, 
				callback: function (res) {
					d.hide();
					error_handler(res);
					let element_name = wrapper_element_selector.slice(1);
					update_roster_view(element_name, page);
					$(".filterhideshow").addClass("d-none");

					if (!("_server_messages" in res)) { // Check if not server messages from frappe.throw
						updateEmployeeDefaults(employees, values);
					}
				}
			});
		}
	});
	d.show();
}

function change_ot_schedule(page) {
	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), "1");
	let employees = [];
	let selected = [... new Set(classgrt)];
	if (selected.length > 0) {
		selected.forEach(function (i) {
			let [employee, date] = i.split("|");
			employees.push({ employee, date });
			employees = [... new Set(employees)]; // This might be redundant if items are unique from classgrt
		});
	}

	let d = new frappe.ui.Dialog({
		"title": "Schedule/Change OT",
		"fields": [
			{
				"label": "Shift", "fieldname": "shift", "fieldtype": "Link", "options": "Operations Shift", "reqd": 1, onchange: function () {
					let name = d.get_value("shift");
					if (name) {
						frappe.db.get_value("Operations Shift", name, ["site", "project"])
							.then(res => {
								let { site, project } = res.message;
								d.set_value("site", site);
								d.set_value("project", project);
							});
					}
				}, get_query: function () {
					return {
						"filters": { "status": "Active" },
						"page_length": 9999
					};
				}
			},
			{ "label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Operations Site", "read_only": 1 },
			{ "label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "read_only": 1 },
			{
				"label": "Choose Operations Role", "fieldname": "operations_role", "fieldtype": "Link", "reqd": 1, "options": "Operations Role", get_query: function () {
					return {
						query: "one_fm.one_fm.page.roster.roster.get_filtered_operations_role",
						filters: { "shift": d.get_value("shift") }
					};
				}
			},
		],
		primary_action: function () {
			let values = d.get_values();
			$("#cover-spin").show(0);
			let wrapper_element_selector = get_wrapper_element();

			if (!employees || employees.length === 0) { 
				frappe.throw(__("Please select employees to roster."))
				$("#cover-spin").hide();
				return;
			}
			// update fields
			if (!values.project_end_date) { values.project_end_date = 0 }
			if (!values.end_date) { values.end_date = "" } 
			values.employees = employees;

			frappe.call({
				method: "one_fm.one_fm.page.roster.roster.schedule_overtime",
				type: "POST",
				args: values,
				callback: function (res) {
					d.hide();
					error_handler(res);
					let element_name = wrapper_element_selector.slice(1);
					update_roster_view(element_name, page);
					$(".filterhideshow").addClass("d-none");
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
		fields: ["name"] // Specify fields
	});

	// Extract project names (IDs) that are valid
	let validProjectIDs = validProjects.map(project => project.name);

	if (uniqueEmployeeIDs.length === 0 || validProjectIDs.length === 0) {
		// No employees or no valid projects to check against, so nothing to update.
		return;
	}


	// Bulk fetch all employees" details in a single query
	let fetchedEmployees = await frappe.db.get_list("Employee", {
		filters: [["name", "in", uniqueEmployeeIDs], ["project", "in", validProjectIDs]],
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
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.current_shift || "Not Set"}</td>
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.new_shift || "Not Set"}</td>
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.current_role || "Not Set"}</td>
					<td style="border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top;">${emp.new_role || "Not Set"}</td>
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

	$("#page-roster").empty().append(frappe.render_template("roster"));
	load_js(page)
}

function clear_staff_filters(page) {
	window.history.replaceState({}, document.title, window.location.origin + window.location.pathname);

	page.filters = {}
	cur_page.page.page.filters = {}

	$(".assigneddrpval").html("Assigned");
	["company", "project", "site", "shift", "department", "designation"].forEach(item => {
		// Ensure the selector is specific enough and that .click() triggers the desired reset
		$(`.staff-${item}-dropdown`).html(item.charAt(0).toUpperCase() + item.slice(1)); // Reset text
		// If these are select2 or have specific clear actions, use those.
		// For simple dropdowns, clicking might not be the way to clear a filter.
		// This part assumes the filter clearing logic is tied to these dropdowns" change events.
	})

	render_staff($(".layoutSidenav_content").attr("data-view"));
}

function clear_selection(page) {
	classgrt = [];

	$(".filterhideshow").addClass("d-none");
	$(".Postfilterhideshow").addClass("d-none");

	// More specific selector for the tables within roster and post views
	$(".rosterMonth #calenderviewtable tbody, .postMonth #calenderviewtable tbody").find("tr").each(function (i, row) {
		$(row).find("input[type='checkbox']").prop("checked", false); // Uncheck the employee checkbox
		$(row).find("div.selectclass").removeClass("selectclass"); // Remove selections from divs
	});
}

function update_roster_view(element, page) {
	page[element](page);
	frappe.realtime.on("roster_view", function (output) {
		page[element](page);
	});
}



function dayoff(page) {
	let employees = [];
	let selected = [... new Set(classgrt)];
	selected.forEach(function (i) {
		let [employee, date] = i.split("|");
		employees.push({ employee, date });
	});
	

	let date = frappe.datetime.add_days(frappe.datetime.nowdate(), "1");
	let d = new frappe.ui.Dialog({
		"title": "Day Off",
		"fields": [
			{ "label": "Selected days only", "fieldname": "selected_dates", "fieldtype": "Check", "default": 0 },
			{ "label": "Set Reliever", "fieldname": "set_reliever", "fieldtype": "Check", "default": 0, onchange: function () {				
				let set_reliever = d.get_value("set_reliever");
				if (set_reliever) { d.set_value("client_day_off", 0); }		
			}},
			{ "label": "Client Day Off", "fieldname": "client_day_off", "fieldtype": "Check", "default": 0 , "depends_on": "eval:doc.set_reliever==0"},
			{ "fieldtype": "Section Break", "fieldname": "sb4", "depends_on": "eval:doc.set_reliever==1"},
			{
				"label": "Reliever", "fieldname": "reliever", "fieldtype": "Link", "options": "Employee", 
				get_query: function () {
					return {
						"filters": {
							"custom_is_reliever": 1,
							"status": [ "in", ["Active"]]
						},
						"page_length": 9999
					};
				},
				onchange: function () { 
					let reliever = d.get_value("reliever");
					if (reliever) {
						frappe.call({
							method: "frappe.client.get",
							args: {
								doctype: "Employee",
								name: reliever,
							},
							callback(r) {
								if (r.message) {
									var emp = r.message;
									d.set_value("reliever_name", emp.employee_name);
									d.set_value("reliever_id", emp.employee_id);
								}
							}
						});
					}
				}
			},
			{ "fieldtype": "Column Break", "fieldname": "cb3" },
			{ "label": "Reliever Name", "fieldname": "reliever_name", "fieldtype": "Data", "read_only": 1},
			{ "fieldtype": "Column Break", "fieldname": "cb4" },
			{ "label": "Reliever ID", "fieldname": "reliever_id", "fieldtype": "Data", "read_only": 1},
			{ "fieldtype": "Section Break", "fieldname": "sb5" },

			{ "label": "Repeat", "fieldname": "repeat", "fieldtype": "Select", "depends_on": "eval:doc.selected_dates==0", "options": "Does not repeat\nWeekly\nMonthly" },
			{ "fieldtype": "Section Break", "fieldname": "sb1", "depends_on": "eval:doc.repeat=='Weekly' && doc.selected_dates==0" },
			{ "label": "Sunday", "fieldname": "sunday", "fieldtype": "Check" },
			{ "label": "Wednesday", "fieldname": "wednesday", "fieldtype": "Check" },
			{ "label": "Saturday", "fieldname": "saturday", "fieldtype": "Check" },
			{ "fieldtype": "Column Break", "fieldname": "cb1" },
			{ "label": "Monday", "fieldname": "monday", "fieldtype": "Check" },
			{ "label": "Thursday", "fieldname": "thursday", "fieldtype": "Check" },
			{ "fieldtype": "Column Break", "fieldname": "cb2" },
			{ "label": "Tuesday", "fieldname": "tuesday", "fieldtype": "Check" },
			{ "label": "Friday", "fieldname": "friday", "fieldtype": "Check" },
			{ "fieldtype": "Section Break", "fieldname": "sb2", "depends_on": "eval:doc.selected_dates==0" },
			{ "label": "Repeat Till", "fieldtype": "Date", "fieldname": "repeat_till", "depends_on": "eval:doc.repeat!= 'Does not repeat' && doc.project_end_date==0" },
			{ "label": "Project End Date", "fieldname": "project_end_date", "fieldtype": "Check" },
		],
		primary_action: function () {
			$("#cover-spin").show(0);
			let week_days = [];
			let args = {};
			let values = d.get_values();
			
			args["selected_dates"] = values.selected_dates;
			args["set_reliever"] = values.set_reliever;
			args["employees"] = employees;
			args["client_day_off"] = values.client_day_off;

			if (values.set_reliever == 0 || !values.reliever) { 
				args["selected_reliever"] = "";
			} else {
				args["selected_reliever"] = values.reliever;
			}

			if (values.selected_dates == 1) {
				args["repeat"] = 0; 
				args["repeat_freq"] = null;
				args["week_days"] = []; 
				args["repeat_till"] = null; 
				args["project_end_date"] = 0;
			} else { 
				args["repeat"] = values.repeat === "Does not repeat" ? 0 : 1; 
				args["repeat_till"] = values.repeat_till;
				args["project_end_date"] = values.project_end_date;
				args["repeat_freq"] = values.repeat; 

				if (values.repeat == "Weekly") {
					if(values.sunday) week_days.push("Sunday");
					if(values.monday) week_days.push("Monday");
					if(values.tuesday) week_days.push("Tuesday");
					if(values.wednesday) week_days.push("Wednesday");
					if(values.thursday) week_days.push("Thursday");
					if(values.friday) week_days.push("Friday");
					if(values.saturday) week_days.push("Saturday");
					args["week_days"] = week_days;
				} else {
					args["week_days"] = []; 
				}
			}


			frappe.call({
				method: "one_fm.one_fm.page.roster.roster.dayoff",
				type: "POST",
				args: args,
				callback: function (res) {
					d.hide();
					error_handler(res);
					let element_name = get_wrapper_element().slice(1); 
					page[element_name](page);
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


let error_handler = (res) => {
	$("#cover-spin").hide();
	if (res.error) { 
		frappe.throw(res.error.message || res.error); 
	} else if (res.data && res.data.message) { 
		frappe.msgprint(res.data.message);
	} 
}

function roster_employee_actions(page) {
	let dialog = new frappe.ui.Dialog({
		title: "Employee with Missing Schedules",
		fields: [
			{
				fieldname: "employees_table",
				fieldtype: "HTML",
				options: "<div id='employees_table'>Loading...</div>"
			}
		]
	})
	dialog.$wrapper.find(".modal-dialog").css("max-width", "75%");

	frappe.call({
		method: "one_fm.one_fm.doctype.roster_employee_actions.roster_employee_actions.get_employees_with_missing_schedules",
		// freeze: true, 
		async: true, 
		callback: function (r) {
			if (r.message) {
				dialog.fields_dict.employees_table.$wrapper.html(r.message);
			} else {
				dialog.fields_dict.employees_table.$wrapper.html("<p>No data returned or an error occurred.</p>");
			}
		}
	});
	dialog.show();
}

function roster_post_actions(page) {
	let dialog = new frappe.ui.Dialog({
		title: "Overfilled/Underfilled Posts",
		fields: [
			{
				fieldname: "post_types_not_filled_section",
				fieldtype: "Section Break",
				label: "Not Filled Posts",
				collapsible: 1
			},
			{
				fieldname: "posts_notfilled_table",
				fieldtype: "HTML",
				options: "<div id='posts_notfilled_table'>Loading...</div>"
			},
			{
				fieldname: "post_types_overfilled_section",
				fieldtype: "Section Break",
				label: "Overfilled Posts",
				collapsible: 1

			},
			{
				fieldname: "posts_overfilled_table",
				fieldtype: "HTML",
				options: "<div id='posts_overfilled_table'>Loading...</div>"
			}

		]
	})
	dialog.$wrapper.find(".modal-dialog").css("max-width", "75%");


	frappe.call({
		method: "one_fm.one_fm.doctype.roster_post_actions.roster_post_actions.get_overfilled_underfilled_posts",
		// freeze: true,
		async: true,
		callback: function (r) {
			if (r.message) {
				dialog.fields_dict.posts_notfilled_table.$wrapper.html(r.message.under_filled || "<p>No underfilled posts data.</p>");
				dialog.fields_dict.posts_overfilled_table.$wrapper.html(r.message.over_filled || "<p>No overfilled posts data.</p>");
			} else {
				dialog.fields_dict.posts_notfilled_table.$wrapper.html("<p>Error loading data.</p>");
				dialog.fields_dict.posts_overfilled_table.$wrapper.html("<p>Error loading data.</p>");
			}
		}
	});
	dialog.show();
}

function roster_day_off_issues() {
	let dialog = new frappe.ui.Dialog({
		title: "Employees with Day Off Issues",
		fields: [
			{
				fieldname: "employees_table",
				fieldtype: "HTML",
				options: "<div id='employees_table'>Loading...</div>"
			}
		]
	})
	dialog.$wrapper.find(".modal-dialog").css("max-width", "75%");
	frappe.call({
		method: "one_fm.operations.doctype.roster_day_off_checker.roster_day_off_checker.get_day_off_issue_of_employees",
		// freeze: true,
		async: true,
		callback: function (r) {
			if (r.message) {
				dialog.fields_dict.employees_table.$wrapper.html(r.message);
			} else {
				dialog.fields_dict.employees_table.$wrapper.html("<p>No data returned or an error occurred.</p>");
			}
		}
	});
	dialog.show();
}