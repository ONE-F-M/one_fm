/**
 * Interview Console - Bulk Recruitment Evaluation Interface
 *
 * CSS is auto-loaded from interview_console.css in this page directory
 * and scoped via body[data-route="interview_console"] to prevent leakage.
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

	// Helper to ensure scores structure holds the right size


	var state = {
		selected_applicant: null,
		scores: [], // Dynamic: will be array of selected row (1-5) for each question
		matrix: [],
		applicants: []
	};
	const SAVE_DEBOUNCE_MS = 500;
	let saveTimeoutId = null;
	let pendingSaveFn = null;
	let save_in_flight = false;
	let queued_save_fn = null;

	function run_serialized_save(saveFn) {
		if (!saveFn) return;
		if (save_in_flight) {
			queued_save_fn = saveFn;
			return;
		}
		save_in_flight = true;
		Promise.resolve(saveFn())
			.catch(function (err) {
				console.error("Interview score save failed:", err);
			})
			.finally(function () {
				save_in_flight = false;
				if (queued_save_fn) {
					var nextFn = queued_save_fn;
					queued_save_fn = null;
					run_serialized_save(nextFn);
				}
			});
	}

	function flush_pending_save() {
		if (saveTimeoutId !== null) {
			clearTimeout(saveTimeoutId);
			saveTimeoutId = null;
			if (pendingSaveFn) {
				run_serialized_save(pendingSaveFn);
				pendingSaveFn = null;
			}
		}
	}

	function init() {
		// Check for deep-link: if arriving from Job Applicant with applicant route_option
		var auto_select_applicant = null;
		if (frappe.route_options && frappe.route_options.applicant) {
			auto_select_applicant = frappe.route_options.applicant;
			frappe.route_options = null; // Consume the option
		}
		
		if (!wrapper._ic_handlers_bound) {
			window.addEventListener('visibilitychange', function() {
				if (document.visibilityState === 'hidden') {
					flush_pending_save();
				}
			});
			if (frappe.router) frappe.router.on('change', flush_pending_save);
			wrapper._ic_handlers_bound = true;
		}

		fetch_applicants(auto_select_applicant);
		setup_handlers();

		// Expose for on_page_show re-navigation
		wrapper._ic_state = state;
		wrapper._ic_select_applicant = select_applicant;
		wrapper._ic_fetch_applicants = fetch_applicants;
	}

	function render_dynamic_matrix(matrix, errorMsg) {
		if (!matrix || matrix.length === 0) {
			$w('.ic-table').hide();
			$w('.ic-remarks-area').hide();
			var errMsg = errorMsg || 'Click the <span style="display:inline-flex; align-items:center; justify-content:center; padding:4px; margin:0 2px; color:#64748b; background:transparent; vertical-align:middle;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="3" x2="12" y2="21"></line><line x1="3" y1="12" x2="21" y2="12"></line></svg></span> button above and <strong style="color:#0f172a; font-weight:800;">select a round</strong> to launch the evaluation matrix.';
			$w('#ic-no-matrix-msg-text').html(errMsg);
			$w('#ic-no-matrix-msg').css('display', 'flex');
			return;
		}

		$w('.ic-table').show();
		$w('.ic-remarks-area').show();
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

		var categoryClassMap = {
			"PHYSICAL": "ic-category-physical",
			"CULTURE / ATTITUDE": "ic-category-culture",
			"MOTIVATION": "ic-category-motivation",
			"KNOWLEDGE / SKILLSET": "ic-category-knowledge",
			"COMMUNICATION": "ic-category-communication"
		};

		for (var j = 0; j < categories.length; j++) {
			var cat = categories[j];
			var catKey = cat.name.trim().toUpperCase();
			var cssClass = categoryClassMap[catKey] || "ic-category-default";
			var display_name = cat.name.trim();
			
			headerHtml += '<th colspan="' + cat.count + '">';
			headerHtml += '<div class="ic-category-pill ' + cssClass + '">' + display_name + '</div></th>';
		}
		headerHtml += '</tr><tr>';

		// Row 2: Questions
		for (var k = 0; k < matrix.length; k++) {
			var q = matrix[k];
			var question_name = q.question;
			var cat_name = q.category || "General";
			var full_color = categoryTextColors[cat_name.trim().toUpperCase()] || "#475569";
			headerHtml += '<th class="ic-question-header" style="border-top-color: ' + full_color + ';">' + 
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
				bodyHtml += '<td><div class="ic-cell" tabindex="0" data-score="' + rowNum + '" data-index="' + c + '">' + cellText + '</div></td>';
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
							frappe.show_alert({ message: __('Applicant {0} not found in list', [auto_select_name]), indicator: 'orange' });
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
	
	function load_matrix_for_round(applicant_name, round_name) {
		frappe.call({
			method: "one_fm.one_fm.page.interview_console.interview_console.get_applicant_data",
			args: { applicant: applicant_name, interview_round_name: round_name },
			callback: function (r) {
				var data = r.message;
				if (data) {
					state.matrix = data.matrix || [];
					state.interview_round = data.interview_round || null;
					render_dynamic_matrix(state.matrix, data.matrix_error || null);
					state.scores = new Array(state.matrix.length).fill(0);
					$w('.ic-cell').removeClass('selected');
					$w('#ic-score-pill').text('0/100');
					
					// Flash visual feedback that round changed
					frappe.show_alert({message: __('Switched to round: {0}', [round_name]), indicator: "blue"});
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
		flush_pending_save();
		state.selected_applicant = app;
        
        $w('#ic-root').addClass('has-selection');
		$w('.ic-item').removeClass('selected');
		var $selected_item = $w('.ic-item[data-name="' + app.name + '"]');
		$selected_item.addClass("selected");
		
		// Auto-scroll the sidebar to ensure the candidate is physically visible on the screen
		if ($selected_item.length) {
			var container = $w('.ic-list'); // Changed from .ic-left to correctly target the candidate list
			if (container.length) {
				var container_offset = container.offset();
				var item_offset = $selected_item.offset();
				if (container_offset && item_offset) {
					var item_top_in_container = item_offset.top - container_offset.top + container.scrollTop();
					var offset = item_top_in_container - (container.height() / 2) + ($selected_item.height() / 2);
					container.animate({ scrollTop: offset }, 300);
				}
			}
		}

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
				
				// Reset photo thumbnail and data
				$w('#ic-photo-thumbnail-container').hide();
				$w('#ic-photo-thumbnail').attr('src', '');
				state.selected_applicant.photo_data_url = "";
				
				$w('#ic-job-offers-count').text(data.job_offers || 0);
				$w('#ic-feedback-count').text(data.interview_count || 0);
				
				// Photo Attachments Counter
				if (data.photo_count !== undefined) {
					$w('#ic-photo-count').text(data.photo_count || 0);
				}

				state.selected_applicant.interview_score = data.score;
				state.selected_applicant.status = data.status;
				state.selected_applicant.job_offer_id = data.job_offer_id || null;
				state.matrix = data.matrix || [];
				state.interview_round = data.interview_round || null;
				
				// Render dynamic matrix (pass error message if any)
				render_dynamic_matrix(state.matrix, data.matrix_error || null);

				// Reset state scores for this matrix
				state.scores = new Array(state.matrix.length).fill(0);
				$w('.ic-cell').removeClass('selected');
				
				// Populate Available Rounds Dropdown only when provided by the backend
				var roundsHtml = '';
				var has_available_rounds = Array.isArray(data.available_rounds) && data.available_rounds.length > 0;
				if (has_available_rounds) {
					data.available_rounds.forEach(function(round_name) {
						roundsHtml += '<div class="ic-dropdown-item">' + esc(round_name) + '</div>';
					});
					$w('#ic-interview-dropdown-list').html(roundsHtml);
					$w('#ic-interview-dropdown-list').show();
					$w('#ic-interview-round-selector, #ic-interview-round-dropdown-trigger').show();
				} else {
					$w('#ic-interview-dropdown-list').empty().hide();
					$w('#ic-interview-dropdown').hide();
					$w('#ic-interview-round-selector, #ic-interview-round-dropdown-trigger').hide();
				}

				// Bind Dropdown Items securely
				$w('.ic-dropdown-item').off('click').on('click', function() {
					$w('#ic-interview-dropdown').hide();
					var selected_round = $(this).text();
					load_matrix_for_round(app.name, selected_round);
				});

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
		// Cell Keyboard Navigation (Arrow Keys + Enter)
		$w('#ic-tbody').off('keydown', '.ic-cell').on('keydown', '.ic-cell', function (e) {
			if (!state.selected_applicant) return;
            
			// Enter key to select
			if (e.key === "Enter" || e.keyCode === 13) {
				e.preventDefault();
				$(this).click();
				return;
			}
            
			// Arrow Key Navigation
			if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].indexOf(e.key) !== -1) {
				e.preventDefault();
				var currentScore = parseInt($(this).data('score'));
				var currentIndex = parseInt($(this).data('index'));
                
				var targetScore = currentScore;
				var targetIndex = currentIndex;
                
				if (e.key === "ArrowUp") {
					targetScore = currentScore < 5 ? currentScore + 1 : 1; 
				} else if (e.key === "ArrowDown") {
					targetScore = currentScore > 1 ? currentScore - 1 : 5;
				} else if (e.key === "ArrowLeft") {
					targetIndex = currentIndex > 0 ? currentIndex - 1 : state.matrix.length - 1;
				} else if (e.key === "ArrowRight") {
					var maxIndex = state.matrix.length - 1;
					targetIndex = currentIndex < maxIndex ? currentIndex + 1 : 0;
				}
                
				var targetCell = $w('.ic-cell[data-score="' + targetScore + '"][data-index="' + targetIndex + '"]');
				if (targetCell.length) {
					targetCell.focus();
				}
			}
		});

		// Cell Click Handler (Delegated since matrix is dynamic)
		$w('#ic-tbody').off('click', '.ic-cell').on('click', '.ic-cell', function () {
			if (!state.selected_applicant) {
				frappe.show_alert({ message: __("Select a candidate first"), indicator: "orange" });
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
					$w("#ic-score-pill").text("0/100");
					fetch_applicants();
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
				var passport = (a.one_fm_passport_number || "").toLowerCase();
				return name.indexOf(val) !== -1 || job.indexOf(val) !== -1 || job_id.indexOf(val) !== -1 || desg.indexOf(val) !== -1 || app_id.indexOf(val) !== -1 || passport.indexOf(val) !== -1;
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

		$w('.ic-btn-circular, .ic-clear-btn, .ic-dashboard-link, #ic-camera-btn').on('click', function () {
			var $btn = $(this);
			$btn.addClass('expanded');
			setTimeout(function () { $btn.removeClass('expanded'); }, 800);
		});

		// Dropdown logic for Plus Button
		$w('#ic-add-interview-btn').off('click').on('click', function(e) {
			e.stopPropagation();
			var dropdown = $w('#ic-interview-dropdown');
			if (dropdown.is(':visible')) {
				dropdown.hide();
			} else {
				dropdown.show();
			}
		});

		// Hide dropdown if clicked outside
		$(document)
			.off('click.ic_interview_dropdown')
			.on('click.ic_interview_dropdown', function(e) {
				if (!$(e.target).closest('#ic-add-interview-btn, #ic-interview-dropdown').length) {
					$w('#ic-interview-dropdown').hide();
				}
			});
		
		// Camera Photo Counter Navigation
		$w('#ic-photo-count-btn').off('click').on('click', function(e) {
			e.stopPropagation();
			if (!state.selected_applicant) return;
			// Route to the global File List pre-filtered by this exact Applicant
			frappe.set_route('List', 'File', {
				attached_to_doctype: 'Job Applicant', 
				attached_to_name: state.selected_applicant.name 
			});
		});

		// Camera Setup Helpers
		let stream = null;
		
		function stopCamera() {
			if (stream) {
				stream.getTracks().forEach(track => track.stop());
				stream = null;
			}
			$w('#ic-camera-modal').hide();
		}
		
		$w('#ic-camera-btn').off('click').on('click', function() {
			if (!state.selected_applicant) {
				frappe.show_alert({ message: __("Select a candidate first."), indicator: "orange" });
				return;
			}
			$w('#ic-camera-modal').css('display', 'flex');
			$w('#ic-photo-preview-large').hide();
			$w('#ic-video-stream').show();
			$w('#ic-camera-capture-btn').show();
			$w('#ic-camera-retake-btn').hide();
			$w('#ic-camera-save-btn').hide();
			
			navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } })
				.then(function(mediaStream) {
					stream = mediaStream;
					var video = document.getElementById('ic-video-stream');
					video.srcObject = stream;
					video.play();
				})
				.catch(function(err) {
					frappe.show_alert({ message: "Camera access denied or unavailable: " + err, indicator: "red" });
					stopCamera();
				});
		});
		
		$w('#ic-camera-capture-btn').off('click').on('click', function() {
			var video = document.getElementById('ic-video-stream');
			var canvas = document.getElementById('ic-video-canvas');
			canvas.width = video.videoWidth;
			canvas.height = video.videoHeight;
			canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
			
			var dataUrl = canvas.toDataURL('image/jpeg', 0.85);
			$w('#ic-photo-preview-large').attr('src', dataUrl).show();
			$w('#ic-video-stream').hide();
			
			$(this).hide();
			$w('#ic-camera-retake-btn').show();
			$w('#ic-camera-save-btn').show();
		});
		
		$w('#ic-camera-retake-btn').off('click').on('click', function() {
			$w('#ic-photo-preview-large').hide();
			$w('#ic-video-stream').show();
			$w('#ic-camera-capture-btn').show();
			$w('#ic-camera-retake-btn').hide();
			$w('#ic-camera-save-btn').hide();
		});
		
		$w('#ic-camera-close-btn').off('click').on('click', stopCamera);
		
		$w('#ic-camera-save-btn').off('click').on('click', function() {
			var dataUrl = $w('#ic-photo-preview-large').attr('src');
			state.selected_applicant.photo_data_url = dataUrl;
			$w('#ic-photo-thumbnail').attr('src', dataUrl);
			$w('#ic-photo-thumbnail-container').css('display', 'flex');
			stopCamera();
			update_and_save(); // Immediately save when photo is attached
		});
		
		$w('#ic-remove-photo').off('click').on('click', function(e) {
			e.stopPropagation();
			state.selected_applicant.photo_data_url = "";
			$w('#ic-photo-thumbnail').attr('src', '');
			$w('#ic-photo-thumbnail-container').hide();
			update_and_save();
		});

		$w('#ic-feedbacks-pill').off('click').on('click', function () {
			if (!state.selected_applicant) return;
			var count = parseInt($w('#ic-feedback-count').text()) || 0;
			if (count > 0) {
				frappe.set_route('List', 'Interview', { job_applicant: state.selected_applicant.name });
			} else {
				frappe.show_alert({ message: "No interviews yet for this candidate.", indicator: "orange" });
			}
		});

		$w('#ic-reject-btn').off('click').on('click', function () {
			if (!state.selected_applicant) {
				frappe.show_alert({ message: __("Select a candidate first"), indicator: "orange" });
				return;
			}
			update_status("Rejected");
			disable_action_buttons('ic-reject-btn');
		});
		$w('#ic-hold-btn').off('click').on('click', function () {
			if (!state.selected_applicant) {
				frappe.show_alert({ message: __("Select a candidate first"), indicator: "orange" });
				return;
			}
			update_status("Hold");
			disable_action_buttons('ic-hold-btn');
		});
		$w('#ic-save-btn').off('click').on('click', function () {
			if (!state.selected_applicant) {
				frappe.show_alert({ message: __("Select a candidate first"), indicator: "orange" });
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

		const currentApplicantName = state.selected_applicant && state.selected_applicant.name;
		if (saveTimeoutId !== null) clearTimeout(saveTimeoutId);
		
		pendingSaveFn = function() {
			return save_to_db(percentage, status);
		};

		saveTimeoutId = setTimeout(function() {
			saveTimeoutId = null;
			if (state.selected_applicant && state.selected_applicant.name === currentApplicantName) {
				if (pendingSaveFn) {
					run_serialized_save(pendingSaveFn);
					pendingSaveFn = null;
				}
			} else {
				pendingSaveFn = null;
				queued_save_fn = null;
			}
		}, SAVE_DEBOUNCE_MS);

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
		return frappe.call({
			method: "one_fm.one_fm.page.interview_console.interview_console.save_interview_data",
			args: {
				applicant: state.selected_applicant.name,
				score: score,
				remarks: $w('#ic-remarks').val(),
				status: status,
				scores_detail: JSON.stringify(scores_detail),
				interview_round: state.interview_round || "",
				height: $w('#ic-height').val() || "",
				photo_data: state.selected_applicant.photo_data_url || ""
			},
			callback: function () {
				if (state.selected_applicant) {
					state.selected_applicant.photo_data_url = "";
					frappe.call({
						method: "one_fm.one_fm.page.interview_console.interview_console.get_applicant_data",
						args: { applicant: state.selected_applicant.name },
						callback: function (r) {
							if (r.message && r.message.interview_count !== undefined) {
								$w('#ic-feedback-count').text(r.message.interview_count);
							}
							if (r.message && r.message.photo_count !== undefined) {
								$w('#ic-photo-count').text(r.message.photo_count);
							}
						}
					});
				}
			}
		});
	}

	function update_status(status) {
		if (!state.selected_applicant) return frappe.msgprint("Select a candidate");
		
		// Cancel any pending debounced save to prevent it from overwriting this hard save in the future
		if (saveTimeoutId !== null) {
			clearTimeout(saveTimeoutId);
			saveTimeoutId = null;
			pendingSaveFn = null;
		}

		var score_text = $w('#ic-score-pill').text();
		var score = parseInt(score_text) || 0;

		state.selected_applicant.status = status;
		
		run_serialized_save(function() {
			return save_to_db(score, status);
		});

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
