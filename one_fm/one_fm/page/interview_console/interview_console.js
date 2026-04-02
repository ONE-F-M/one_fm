/**
 * Interview Console - Bulk Recruitment Evaluation Interface
 *
 * CSS is injected via frappe.dom.set_style to ensure proper loading
 * within the Frappe Page lifecycle.
 */

	// HTML escape helper to prevent XSS
	function esc(str) {
		if (!str) return '';
		return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
	}

frappe.pages['interview_console'].on_page_load = function (wrapper) {
	try {

		// 1. Dynamic Font & CSS Loading
		if (!$('link[href*="Roboto"]').length) {
			$('head').append('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&display=swap">');
		}
		if (!$('link[href*="interview_console.css"]').length) {
			$('head').append('<link rel="stylesheet" href="/assets/one_fm/css/interview_console.css">');
		}


		// 2. Initialize Page Structure
		var page = frappe.ui.make_app_page({
			parent: wrapper,
			title: '',
			single_column: true
		});

		// 3. Render Template into the Main Container
		var content = frappe.render_template('interview_console', {});
		if (!content) throw new Error("Template failed to render");

        // The template should have #ic-root at its top level, ensuring it can receive classes
		$(page.main).empty().append(content);

		// 4. Page Visibility Handlers to prevent CSS leakage
		$(wrapper).on('show', function () {
			$('body').addClass('ic-active');
		});
		$(wrapper).on('hide', function () {
			$('body').removeClass('ic-active');
		});
		// Trigger initial show if already visible
		if ($(wrapper).is(':visible')) $('body').addClass('ic-active');

		setTimeout(function () {
			try {
				init_interview_console(wrapper, page);
			} catch (e) {
				console.error("Logic Init Error:", e);
			}
		}, 150);
	} catch (err) {
		console.error("Global Page Load Error:", err);
		$(wrapper).html('<div style="padding:100px; text-align:center; color:red;"><h3>Page Builder Error</h3><p>' + err.message + '</p></div>');
	}
};

// Handle re-navigation to the page (e.g., from Job Applicant button)
frappe.pages['interview_console'].on_page_show = function (wrapper) {
	if (frappe.route_options && frappe.route_options.applicant && wrapper._ic_state) {
		var target = frappe.route_options.applicant;
		frappe.route_options = null; // Consume the option
		// Re-fetch with the auto-select target
		wrapper._ic_fetch_applicants(target);
	}
};

function init_interview_console(wrapper, page) {
	var $w = function (selector) { return $(wrapper).find(selector); };

	// Helper for fuzzy matching question names
	var get_standard_key = function(str) {
		return (str || "").replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
	};

	var MASTER_WORD_MAPPING = {
		"Physical / Body Build (Fitness & Stature)": ["Tall, athletic, well-built.", "Fit, well-proportioned.", "Neutral, average build.", "Fatigued, poor posture.", "Unhealthy, physically brittle."],
		"Quality of Appearance (Grooming & Presence)": ["Crisp, clean, inviting.", "Clean, tidy attire.", "Standard, basic grooming.", "Scruffy or inappropriate.", "Unhygienic or aggressive."],
		"Tell me about a Difficult Situation?": ["Solves complex problems.", "Solves average problems.", "Solves simple problems.", "No solution provided.", "No situation stated."],
		"Tell me about a Difficult Customer you faced?": ["Expert crowd control.", "Manages groups effectively.", "Basic crowd control.", "No crowd control.", "Careless; no control."],
		"Hard Worker (Can you work 12 hours, 16 hours, 24 hours? Can you work 30days without a day off? can you work 2 years without vacation? can you work 1 year without sick leave?)": ["Full 24/7 availability.", "16hr/ takes sick leave.", "Limited shift availability.", "Cannot work 30- days.", "Minimal shift capacity."],
		"Work History (Promotion)": ["International experience.", "Local security promotions.", "Basic security experience.", "Non-security experience.", "No work history."],
		"A customer comes to asking for directions and you do not know the direction what do you do?": ["Guides customer personally.", "Researches then guides.", "Refers to supervisor.", "Defers to others.", "Claims no knowledge."],
		"Technical (Incident Fire + Theft)": ["Full emergency response.", "Follows basic protocols.", "Partial protocol knowledge.", "Major protocol gaps.", "Fails technical check."],
		"English Written": ["Perfect grammar/structure.", "Good; minor errors.", "Readable; limited vocab.", "Poor; many errors.", "Cannot write."],
		"English Read": ["Clear; no skips.", "Reads without hesitation.", "Skips/repeats words.", "Barely reads sentences.", "Cannot read."],
		"English Comprehension": ["Perfect understanding.", "Few clarifications needed.", "Needs many repetitions.", "Poor understanding.", "No understanding."],
		"English Speak": ["Eloquent natural speaker.", "Fluent English speech.", "Reasonable speaking clarity.", "Broken English speech.", "Cannot speak English."]
	};

	var state = {
		selected_applicant: null,
		scores: [], // Dynamic: will be array of selected row (1-5) for each question
		matrix: [],
		applicants: []
	};

	function init() {
		// Check for deep-link: if arriving from Job Applicant with applicant route_option
		var auto_select_applicant = null;
		if (frappe.route_options && frappe.route_options.applicant) {
			auto_select_applicant = frappe.route_options.applicant;
			frappe.route_options = null; // Consume the option
		}
		fetch_applicants(auto_select_applicant);
		setup_handlers();

		// Expose for on_page_show re-navigation
		wrapper._ic_state = state;
		wrapper._ic_select_applicant = select_applicant;
		wrapper._ic_fetch_applicants = fetch_applicants;
	}

	function render_dynamic_matrix(matrix) {
		if (!matrix || matrix.length === 0) {
			$w('.ic-table').hide();
			$w('#ic-no-matrix-msg').show();
			return;
		}

		$w('.ic-table').show();
		$w('#ic-no-matrix-msg').hide();

		// Group Matrix by Category
		var categories = [];
		var currentCat = null;
		for (var i = 0; i < matrix.length; i++) {
			var catName = matrix[i].category || "General";
			if (!currentCat || currentCat.name !== catName) {
				currentCat = { name: catName, weight: matrix[i].category_weight || "", count: 0, questions: [] };
				categories.push(currentCat);
			}
			currentCat.count++;
			currentCat.questions.push(matrix[i]);
		}

		// Update Headers (Two-Row Header)
		var headerHtml = '<tr><th rowspan="2" style="width: 40px; border: none; background: transparent; box-shadow: none;">Rate</th>';
		
		// Row 1: Categories
		var categoryColors = {
			"PHYSICAL": "#dcfce7",
			"CULTURE / ATTITUDE": "#fff9c4",
			"MOTIVATION": "#f3e8ff",
			"KNOWLEDGE / SKILLSET": "#fee2e2",
			"COMMUNICATION": "#e0f2fe"
		};
		var categoryTextColors = {
			"PHYSICAL": "#166534",
			"CULTURE / ATTITUDE": "#854d0e",
			"MOTIVATION": "#6b21a8",
			"KNOWLEDGE / SKILLSET": "#991b1b",
			"COMMUNICATION": "#0369a1"
		};

		for (var j = 0; j < categories.length; j++) {
			var cat = categories[j];
			var catKey = cat.name.trim().toUpperCase();
			var bg = categoryColors[catKey] || "#f1f5f9";
			var text = categoryTextColors[catKey] || "#475569";
			
			// Use the original category name as-is for display
			var display_name = cat.name.trim();
			
			headerHtml += '<th colspan="' + cat.count + '">';
			headerHtml += '<div class="ic-category-pill" style="background-color: ' + bg + '; color: ' + text + ';">' + 
						  display_name + '</div></th>';
		}
		headerHtml += '</tr><tr>';

		// Row 2: Questions
		for (var k = 0; k < matrix.length; k++) {
			var q = matrix[k];
			var question_name = q.question;
			var cat_name = q.category || "General";
			var full_color = categoryTextColors[cat_name.trim().toUpperCase()] || "#475569";
			var bg_tint = "#ffffff";
			
			// Overwrite wording if mapping exists (using fuzzy matching for robustness)
			var standard_q_key = Object.keys(MASTER_WORD_MAPPING).find(key => 
				get_standard_key(key) === get_standard_key(question_name)
			);
			
			if (standard_q_key) {
				q.ratings = MASTER_WORD_MAPPING[standard_q_key];
				question_name = standard_q_key;
			}
			
			headerHtml += '<th style="background-color: #f0f1f5 !important; border-top: 1.5px solid ' + full_color + ' !important; color: #0f172a !important; font-weight: 800; font-size: 10px; line-height: 1.2; text-transform: uppercase; letter-spacing: 0.02em;">' + 
						  question_name + '</th>';
		}
		headerHtml += '</tr>';
		$w('#ic-thead').html(headerHtml);

		// Update Body (5 Rating Rows)
		var bodyHtml = '';
		for (var r = 0; r < 5; r++) {
			var rowNum = 5 - r;
			bodyHtml += '<tr><td class="ic-row-num">' + rowNum + '</td>';
			for (var c = 0; c < matrix.length; c++) {
				var cellText = matrix[c].ratings[r] || "";
				// If cellText is empty and weight is > 0, we could auto-calculate if we wanted, 
				// but let's stick to showing the value from DB for now as per the existing logic.
				bodyHtml += '<td><div class="ic-cell" data-score="' + rowNum + '" data-index="' + c + '">' + cellText + '</div></td>';
			}
			bodyHtml += '</tr>';
		}
		$w('#ic-tbody').html(bodyHtml);
		
		// Initialize scores array if not set
		if (state.scores.length !== matrix.length) {
			state.scores = new Array(matrix.length).fill(0);
		}
	}

	function fetch_applicants(auto_select_name) {
		frappe.call({
			method: 'one_fm.one_fm.page.interview_console.interview_console.get_applicant_list',
			args: { hiring_method: 'Bulk Recruitment' },
			callback: function (r) {
				if (r.message) {
					state.applicants = r.message;
					$w('#ic-candidate-count').text(state.applicants.length);
					render_list(state.applicants);

					// If auto-select target was provided, find and select the applicant
					if (auto_select_name) {
						var target_app = state.applicants.find(function(a) { return a.name === auto_select_name; });
						if (target_app) {
							select_applicant(target_app);
						} else {
							frappe.show_alert({ message: 'Applicant ' + auto_select_name + ' not found in list', indicator: 'orange' });
							if (state.applicants.length > 0) load_matrix_silent(state.applicants[0].name);
						}
					} else {
						// Default: load first applicant's matrix silently to avoid "blank" look
						if (state.applicants.length > 0) {
							load_matrix_silent(state.applicants[0].name);
						}
					}
				} else {
					$w('#ic-list').html('<div style="padding:10px;font-size:11px;color:#94a3b8;">No applicants found.</div>');
				}
			}
		});

		$w('#ic-job-offers-count').text('0');
	}

	function load_matrix_silent(applicant_name) {
		frappe.call({
			method: "one_fm.one_fm.page.interview_console.interview_console.get_applicant_data",
			args: { applicant: applicant_name },
			callback: function (r) {
				if (r.message && r.message.matrix) {
					render_dynamic_matrix(r.message.matrix);
				}
			}
		});
	}

	function render_list(list) {
		var html = '';
		for (var i = 0; i < list.length; i++) {
			var app = list[i];
			var score = app.interview_score || 0;
			var status = app.status || "Open";
			var display_status = status;
			if (["Accepted", "Job Offer Issued", "Shortlisted", "Hired", "Rejected", "Hold"].indexOf(status) === -1) {
				display_status = (score > 0) ? "Scored" : "Not Scored";
			}

			var status_class = "status-not-scored";
			if (display_status === "Scored") status_class = "status-scored";
			if (display_status === "Rejected") status_class = "status-rejected";
			if (display_status === "Hold") status_class = "status-hold";
			if (["Accepted", "Job Offer Issued", "Shortlisted", "Hired"].indexOf(display_status) !== -1) status_class = "status-accepted";

			var job_code = app.job_title || '';
			var desg = app.designation || '';
			var sub_text = esc(desg) + (job_code ? ' · ' : '');

			html += '<div class="ic-item" data-name="' + esc(app.name) + '">' +
				'<div class="ic-item-right">' +
				'<span class="ic-status-pill ' + status_class + '">' + esc(display_status) + '</span>' +
				'<span style="font-size:9px;font-weight:700;color:#475569;">' + esc(score) + '</span>' +
				'</div>' +
				'<div class="ic-item-name"><a class="ic-name-link" data-applicant="' + esc(app.name) + '" style="cursor:pointer;color:inherit;text-decoration:none;">' + esc(app.applicant_name) + '</a></div>' +
				'<div class="ic-item-sub">' + sub_text + 
				(job_code ? '<a class="ic-job-link" data-job="' + esc(job_code) + '" title="Open Job Opening" style="cursor:pointer;color:#0369a1;text-decoration:underline;font-size:inherit;">' + esc(job_code) + '</a>' : '') +
				'</div>' +
				'</div>';
		}
		$w('#ic-list').html(html);

		$w('.ic-item').off('click').on('click', function (e) {
			// If clicking the candidate name, open Job Applicant form
			if ($(e.target).hasClass('ic-name-link')) {
				e.stopPropagation();
				var applicant_id = $(e.target).data('applicant');
				if (applicant_id) {
					window.open('/app/job-applicant/' + applicant_id, '_blank');
				}
				return;
			}
			// If clicking job opening link, open Job Opening form
			if ($(e.target).hasClass('ic-job-link')) {
				e.stopPropagation();
				var job_id = $(e.target).data('job');
				if (job_id) {
					window.open('/app/job-opening/' + job_id, '_blank');
				}
				return;
			}
			// Everything else selects the candidate
			var name = $(this).data('name');
			var app = state.applicants.find(function (a) { return a.name === name; });
			select_applicant(app);
		});
	}

	function select_applicant(app) {
		state.selected_applicant = app;
        
        $w('#ic-root').addClass('has-selection');
		$w('.ic-item').removeClass('selected');
		$w('.ic-item[data-name="' + app.name + '"]').addClass("selected");

		// Reset buttons, then set state based on existing status
		enable_action_buttons();
		var st = app.status || '';
		if (st === 'Rejected') disable_action_buttons('ic-reject-btn');
		else if (st === 'Hold') disable_action_buttons('ic-hold-btn');
		else if (['Accepted', 'Job Offer Issued', 'Shortlisted', 'Hired'].indexOf(st) !== -1) disable_action_buttons('ic-save-btn');

		frappe.call({
			method: "one_fm.one_fm.page.interview_console.interview_console.get_applicant_data",
			args: { applicant: app.name },
			callback: function (r) {
				var data = r.message || { age: "--", height: "", remarks: "", score: 0, status: "Open", job_offers: 0, matrix: [] };
				$w('#ic-age').text(data.age);
				$w('#ic-height').val(data.height || "");
				$w('#ic-remarks').val(data.remarks);
				$w('#ic-score-pill').text(data.score + '/100');
				$w('#ic-job-offers-count').text(data.job_offers || 0);

				state.selected_applicant.interview_score = data.score;
				state.selected_applicant.status = data.status;
				state.selected_applicant.job_offer_id = data.job_offer_id || null;
				state.matrix = data.matrix || [];
				state.interview_round = data.interview_round || null;
				
				// Render dynamic matrix
				render_dynamic_matrix(state.matrix);

				// Reset state scores for this matrix
				state.scores = new Array(state.matrix.length).fill(0);
				$w('.ic-cell').removeClass('selected');

				// Update Sidebar UI
				var $item = $w('.ic-item[data-name="' + app.name + '"]');
				$item.find('.ic-item-right span:last').text(data.score);

				var display_status = data.status;
				if (["Accepted", "Job Offer Issued", "Shortlisted", "Hired", "Rejected", "Hold"].indexOf(data.status) === -1) {
					display_status = (data.score > 0) ? "Scored" : "Not Scored";
				}
				var status_class = "status-not-scored";
				if (display_status === "Scored") status_class = "status-scored";
				if (display_status === "Rejected") status_class = "status-rejected";
				if (display_status === "Hold") status_class = "status-hold";
				if (["Accepted", "Job Offer Issued", "Shortlisted", "Hired"].indexOf(display_status) !== -1) status_class = "status-accepted";

				$item.find('.ic-status-pill').text(display_status)
					.removeClass('status-scored status-rejected status-hold status-accepted status-not-scored')
					.addClass(status_class);

				if (["Accepted", "Job Offer Issued", "Shortlisted", "Hired"].indexOf(data.status) !== -1) {
					$w('#ic-save-btn').addClass('disabled');
				} else {
					$w('#ic-save-btn').removeClass('disabled');
				}
			}
		});
	}

	function setup_handlers() {
		// Cell Click Handler (Delegated since matrix is dynamic)
		$w('#ic-tbody').off('click', '.ic-cell').on('click', '.ic-cell', function () {
			if (!state.selected_applicant) {
				frappe.show_alert({ message: "Select a candidate first", indicator: "orange" });
				return;
			}
			var score = $(this).data('score'); // 1-5
			var index = $(this).data('index'); // column index

			if (state.scores[index] === score) {
				state.scores[index] = 0;
				$(this).removeClass('selected');
			} else {
				$w('.ic-cell[data-index="' + index + '"]').removeClass('selected');
				$(this).addClass('selected');
				state.scores[index] = score;
			}
			update_and_save();
		});

		$w('#ic-reset-btn').on('click', function () {
			if (!state.selected_applicant) return;
			state.scores = new Array(state.matrix.length).fill(0);
			$w('.ic-cell').removeClass('selected');
			// Clear Interview + Feedback documents and reset applicant status
			frappe.call({
				method: "one_fm.one_fm.page.interview_console.interview_console.clear_interview_data",
				args: { applicant: state.selected_applicant.name },
				callback: function () {
					state.selected_applicant.status = 'Open';
					state.selected_applicant.interview_score = 0;
					enable_action_buttons();
					update_total_score();
					load_applicants();
				}
			});
		});

		$w('#ic-search').on('input', function () {
			var val = ($(this).val() || "").toLowerCase();
			var filtered = state.applicants.filter(function (a) {
				var name = (a.applicant_name || "").toLowerCase();
				var job = (a.job_opening_title || a.job_title || "").toLowerCase();
				var job_id = (a.job_opening || a.job_title || "").toLowerCase();
				var desg = (a.designation || "").toLowerCase();
				var app_id = (a.name || "").toLowerCase();
				return name.indexOf(val) !== -1 || job.indexOf(val) !== -1 || job_id.indexOf(val) !== -1 || desg.indexOf(val) !== -1 || app_id.indexOf(val) !== -1;
			});
			render_list(filtered);
		});

		$w('#ic-remarks').on('input', function () {
			if (state.selected_applicant) update_and_save();
		});

		$w('#ic-job-offers-pill').on('click', function () {
			if (!state.selected_applicant) return;
			var count = parseInt($w('#ic-job-offers-count').text()) || 0;
			if (count === 1 && state.selected_applicant.job_offer_id) {
				frappe.set_route('Form', 'Job Offer', state.selected_applicant.job_offer_id);
			} else if (count > 1) {
				frappe.set_route('List', 'Job Offer', { job_applicant: state.selected_applicant.name });
			} else {
				frappe.show_alert({ message: "This candidate does not have a Job Offer yet.", indicator: "orange" });
			}
		});

		$w('.ic-btn-circular, .ic-clear-btn, .ic-dashboard-link').on('click', function () {
			var $btn = $(this);
			$btn.addClass('expanded');
			setTimeout(function () { $btn.removeClass('expanded'); }, 800);
		});

		$w('#ic-reject-btn').on('click', function () { 
			if (!state.selected_applicant) {
				frappe.show_alert({ message: "Select a candidate first", indicator: "orange" });
				return;
			}
			update_status("Rejected");
			disable_action_buttons('ic-reject-btn');
		});
		$w('#ic-hold-btn').on('click', function () { 
			if (!state.selected_applicant) {
				frappe.show_alert({ message: "Select a candidate first", indicator: "orange" });
				return;
			}
			update_status("Hold");
			disable_action_buttons('ic-hold-btn');
		});
		$w('#ic-save-btn').on('click', function () {
			if (!state.selected_applicant) {
				frappe.show_alert({ message: "Select a candidate first", indicator: "orange" });
				return;
			}

			let d = new frappe.ui.Dialog({
				title: __("Accept Candidate"),
				fields: [
					{
						fieldname: "info",
						fieldtype: "HTML",
						options: `<p>How would you like to proceed with <b>${esc(state.selected_applicant.applicant_name)}</b>?</p>`
					}
				],
				primary_action_label: __("Accept & Issue Job Offer"),
				primary_action: function () {
					update_status("Accepted");
					d.hide();
					disable_action_buttons('ic-save-btn');
					frappe.show_alert({
						message: __("Applicant Accepted. Magic Link sent to candidate."),
						indicator: "green"
					});
				},
				secondary_action_label: __("Mark as Shortlisted"),
				secondary_action: function () {
					update_status("Shortlisted");
					d.hide();
				}
			});
			d.show();
		});
	}

	function update_and_save() {
		if (!state.selected_applicant) return;
		
		// CALCULATE WEIGHTED SCORE
		// Formula: Sum of ((Selected_Rate / 5) * Weight)
		var weighted_score_sum = 0;
		var total_weight = 0;
		
		for (var i = 0; i < state.matrix.length; i++) {
			var weight = state.matrix[i].weight || 0;
			var selected_rate = state.scores[i] || 0; // 0-5
			
			weighted_score_sum += (selected_rate / 5) * weight;
			total_weight += weight;
		}
		
		var percentage = 0;
		if (total_weight > 0) {
			percentage = Math.round((weighted_score_sum / total_weight) * 100);
		} else {
			// Fallback: If no weights are set, use simple average if scores exist
			var total = 0;
			var active_cols = 0;
			for (var j = 0; j < state.scores.length; j++) {
				if (state.scores[j] > 0) {
					total += state.scores[j];
					active_cols++;
				}
			}
			if (active_cols > 0) percentage = Math.round((total / (active_cols * 5)) * 100);
		}

		var status = state.selected_applicant.status;
		$w('#ic-score-pill').text(percentage + '/100').css({ 'background': '#e0f2fe', 'color': '#0369a1' });
		if (percentage > 0 && status === "Open") status = "Replied";

		save_to_db(percentage, status);

		state.selected_applicant.interview_score = percentage;
		state.selected_applicant.status = status;

		// Refresh UI Pill
		var display_status = status;
		if (["Accepted", "Job Offer Issued", "Shortlisted", "Hired", "Rejected", "Hold"].indexOf(status) === -1) {
			display_status = (percentage > 0) ? "Scored" : "Not Scored";
		}
		var status_class = "status-not-scored";
		if (display_status === "Scored") status_class = "status-scored";
		if (display_status === "Rejected") status_class = "status-rejected";
		if (display_status === "Hold") status_class = "status-hold";
		if (["Accepted", "Job Offer Issued", "Shortlisted", "Hired"].indexOf(display_status) !== -1) status_class = "status-accepted";

		var $item = $w('.ic-item[data-name="' + state.selected_applicant.name + '"]');
		$item.find('.ic-item-right span:last').text(percentage);
		$item.find('.ic-status-pill').text(display_status)
			.removeClass('status-scored status-rejected status-hold status-accepted status-not-scored')
			.addClass(status_class);
	}

	function disable_action_buttons(active_id) {
		// First reset all buttons, then highlight only the active one
		enable_action_buttons();
		var $btn = $w('#' + active_id);
		$btn.addClass('active-state disabled');
		// Change text to past tense
		var labels = { 'ic-reject-btn': 'Rejected', 'ic-hold-btn': 'On Hold', 'ic-save-btn': 'Accepted' };
		if (labels[active_id]) {
			$btn.find('.btn-text').text(labels[active_id]);
		}
	}

	function enable_action_buttons() {
		// Re-enable all buttons and restore original text
		$w('#ic-reject-btn, #ic-hold-btn, #ic-save-btn')
			.removeClass('disabled active-state');
		$w('#ic-reject-btn .btn-text').text('Reject');
		$w('#ic-hold-btn .btn-text').text('Hold');
		$w('#ic-save-btn .btn-text').text('Accept');
	}
	function save_to_db(score, status) {
		// Build per-question scores detail for Interview summary
		var scores_detail = [];
		if (state.matrix && state.scores) {
			for (var i = 0; i < state.matrix.length; i++) {
				scores_detail.push({
					question: state.matrix[i].question,
					category: state.matrix[i].category || "General",
					score: state.scores[i] || 0,
					weight: state.matrix[i].weight || 0
				});
			}
		}
		frappe.call({
			method: "one_fm.one_fm.page.interview_console.interview_console.save_interview_data",
			args: {
				applicant: state.selected_applicant.name,
				score: score,
				remarks: $w('#ic-remarks').val(),
				status: status,
				scores_detail: JSON.stringify(scores_detail),
				interview_round: state.interview_round || "",
				height: $w('#ic-height').val() || ""
			},
			callback: function () { }
		});
	}

	function update_status(status) {
		if (!state.selected_applicant) return frappe.msgprint("Select a candidate");
		var score_text = $w('#ic-score-pill').text();
		var score = parseInt(score_text) || 0;

		state.selected_applicant.status = status;
		save_to_db(score, status);

		// Immediate UI update
		var display_status = status;
		if (["Accepted", "Rejected", "Hold"].indexOf(status) === -1) {
			display_status = (score > 0) ? "Scored" : "Not Scored";
		}
		var status_class = "status-not-scored";
		if (display_status === "Scored") status_class = "status-scored";
		if (display_status === "Rejected") status_class = "status-rejected";
		if (display_status === "Hold") status_class = "status-hold";
		if (display_status === "Accepted") status_class = "status-accepted";

		var $item = $w('.ic-item[data-name="' + state.selected_applicant.name + '"]');
		$item.find('.ic-status-pill').text(display_status)
			.removeClass('status-scored status-rejected status-hold status-accepted status-not-scored')
			.addClass(status_class);

		if (["Accepted", "Job Offer Issued", "Shortlisted", "Hired"].indexOf(status) !== -1) {
			$w('#ic-save-btn').addClass('disabled');
		} else {
			$w('#ic-save-btn').removeClass('disabled');
		}

		frappe.show_alert({ message: "Status updated to " + status, indicator: (status === "Rejected" ? "red" : (status === "Hold" ? "orange" : "green")) });
	}

	init();
}
