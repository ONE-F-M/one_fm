/**
 * Transportation Schedules board: the lobby TV of one accommodation.
 *
 * URL: /app/transportation-schedules-board?camp=<Accommodation>&theme=charcoal|light
 * The setup bar picks camp and theme; in board mode (full screen, or a kiosk window
 * that fills the screen) only the board shows and nothing invites interaction.
 */

const POLL_MS = 60000;

const TSB_API = "one_fm.one_fm.doctype.transportation_manifest.manifest_board.";
const TSB_THEMES = ["charcoal", "light"];
const TSB_MINUTE = 60000;

const TSB_MARK = `<svg xmlns="http://www.w3.org/2000/svg" class="tsb-mark" fill="currentColor" role="img" aria-label="ONE FM" viewBox="0 0 175.591 68.494"><g transform="translate(-71.377 -66.91)"><g><path d="M136.057,116.522a19.824,19.824,0,0,1-7.508-7.734,23.1,23.1,0,0,1,0-21.569,20.085,20.085,0,0,1,7.508-7.733,23.1,23.1,0,0,1,22.3,0,20.041,20.041,0,0,1,7.537,7.733,23.1,23.1,0,0,1,0,21.569,19.781,19.781,0,0,1-7.537,7.734,23.308,23.308,0,0,1-22.3,0Zm4.387-30.709a13.491,13.491,0,0,0-4.921,5.034A14.159,14.159,0,0,0,133.7,97.99a14.31,14.31,0,0,0,1.828,7.17,13.434,13.434,0,0,0,4.921,5.063,13.478,13.478,0,0,0,13.555,0,13.237,13.237,0,0,0,4.892-5.063,14.49,14.49,0,0,0,1.8-7.17,14.336,14.336,0,0,0-1.8-7.143A13.292,13.292,0,0,0,154,85.813a13.478,13.478,0,0,0-13.555,0Z" /><path d="M209.668,118.575,182.559,94.109v20.753a3.343,3.343,0,0,1-3.713,3.713h-4.1V77.4h.843l27.053,24.916v-21.2a3.344,3.344,0,0,1,3.712-3.713h4.162v41.171Z" /><path d="M216.7,77.4h30.258v3.488A3.381,3.381,0,0,1,246,83.479a3.87,3.87,0,0,1-2.755.9h-18.73V94.671h17.661v3.262a3.343,3.343,0,0,1-3.712,3.712H224.514V111.6h18.673a3.654,3.654,0,0,1,3.768,3.768v3.207H216.7Z" /><g><path d="M125.872,131.309v-6.621h3.9v1.018h-2.748v1.676h2.443v1.009h-2.443v2.918Z" /><path d="M130.929,131.309h-1.178l3.256-6.836h.091l3.142,6.836h-1.224l-.534-1.178h-3.01Zm.973-2.123h2.169L133,126.715Z" /><path d="M142,130.88a3.508,3.508,0,0,1-.95.479,3.342,3.342,0,0,1-1.041.164,3.265,3.265,0,0,1-2.06-.721,3.329,3.329,0,0,1-.947-1.222,3.752,3.752,0,0,1-.331-1.582,3.518,3.518,0,0,1,.961-2.528,3.19,3.19,0,0,1,2.4-1.006,3.277,3.277,0,0,1,1.007.155,3.6,3.6,0,0,1,.938.47l-.118,1.293a2.852,2.852,0,0,0-.832-.635,2.193,2.193,0,0,0-2.534.477,2.511,2.511,0,0,0-.63,1.765,2.472,2.472,0,0,0,.614,1.724,2.018,2.018,0,0,0,1.564.678,2.337,2.337,0,0,0,1.032-.238,3.612,3.612,0,0,0,.991-.744Z" /><path d="M143.461,131.309v-6.621h1.169v6.621Z" /><path d="M146.015,131.309v-6.621h1.16v5.585h2.845v1.036Z" /><path d="M151.412,131.309v-6.621h1.169v6.621Z" /><path d="M157.382,125.7v5.612h-1.169V125.7h-2.238v-1.009h5.631V125.7Z" /><path d="M160.989,131.309v-6.621h1.168v6.621Z" /><path d="M163.549,131.309v-6.621H167.4v1.018h-2.722v1.63h2.338v1.009h-2.338v1.937h2.768v1.027Z" /><path d="M168.845,129.838a5.153,5.153,0,0,0,.987.512,2.484,2.484,0,0,0,.85.164,1.315,1.315,0,0,0,.844-.258.814.814,0,0,0,.324-.668.962.962,0,0,0-.216-.615,2.838,2.838,0,0,0-.756-.591l-.5-.3a3.584,3.584,0,0,1-1.075-.88,1.621,1.621,0,0,1-.318-.988,1.6,1.6,0,0,1,.557-1.263,2.132,2.132,0,0,1,1.453-.486,3.619,3.619,0,0,1,.842.1,3.842,3.842,0,0,1,.824.3l-.036,1.054a5.47,5.47,0,0,0-.87-.394,2.158,2.158,0,0,0-.673-.126,1.15,1.15,0,0,0-.72.2.664.664,0,0,0-.262.555.751.751,0,0,0,.191.5,2.97,2.97,0,0,0,.713.53l.479.278a3.92,3.92,0,0,1,1.183.98,1.857,1.857,0,0,1,.351,1.116,1.808,1.808,0,0,1-.623,1.43,2.439,2.439,0,0,1-1.66.543,4.337,4.337,0,0,1-.924-.1,3.944,3.944,0,0,1-.861-.295Z" /><path d="M176.845,131.309l1.356-6.836h.078l2.365,4.845L183,124.473h.073l1.346,6.836h-1.136l-.722-3.74-1.872,3.964h-.1l-1.945-3.964-.722,3.74Z" /><path d="M186.992,131.309h-1.177l3.255-6.836h.092l3.141,6.836h-1.224l-.534-1.178h-3.009Zm.973-2.123h2.17l-1.074-2.471Z" /><path d="M193.7,131.309v-6.836h.123l4.265,4.425v-4.21h1.133v6.835H199.1l-4.275-4.424v4.21Z" /><path d="M201.788,131.309H200.61l3.255-6.836h.092l3.142,6.836h-1.225l-.534-1.178h-3.009Zm.972-2.123h2.17l-1.074-2.471Z" /><path d="M213.046,126.373a3.345,3.345,0,0,0-.966-.642,2.589,2.589,0,0,0-1.024-.213,2.221,2.221,0,0,0-1.69.686,2.487,2.487,0,0,0-.649,1.785,2.421,2.421,0,0,0,.649,1.758,2.252,2.252,0,0,0,1.7.671,2.854,2.854,0,0,0,.6-.066,4.406,4.406,0,0,0,.688-.212v-1.384h-1.6v-1.018H213.5v3.133a5.326,5.326,0,0,1-1.206.495,4.73,4.73,0,0,1-1.237.167,3.54,3.54,0,1,1,0-7.078,4.149,4.149,0,0,1,1.068.137,4.558,4.558,0,0,1,1.028.415Z" /><path d="M214.881,131.309v-6.621h3.854v1.018h-2.722v1.63h2.339v1.009h-2.339v1.937h2.768v1.027Z" /><path d="M220.17,131.309l1.357-6.836h.077l2.365,4.845,2.357-4.845h.072l1.348,6.836h-1.138l-.721-3.74-1.872,3.964h-.1l-1.945-3.964-.721,3.74Z" /><path d="M229.13,131.309v-6.621h3.854v1.018h-2.721v1.63H232.6v1.009h-2.338v1.937h2.767v1.027Z" /><path d="M234.422,131.309v-6.836h.124l4.264,4.425v-4.21h1.133v6.835h-.123l-4.274-4.424v4.21Z" /><path d="M244.745,125.7v5.612h-1.169V125.7h-2.238v-1.009h5.63V125.7Z" /></g><path d="M104.036,82.88l-15.7,9.134L71.377,80.578l23.5-13.668Z" fill-rule="evenodd"/><path d="M94.855,135.4l18.6-10.625V77.127L94.877,66.91Z" class="tsb-mark-dim" fill-rule="evenodd"/></g></g></svg>`;

// Site wall-clock "YYYY-MM-DD HH:MM:SS" as ms on a UTC axis, so the TV's own zone never applies.
function naiveMs(text) {
	const m = String(text || "").match(/(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/);
	return m ? Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) : NaN;
}

function clockText(ms, seconds) {
	const d = new Date(ms);
	const parts = [d.getUTCHours(), d.getUTCMinutes()].concat(seconds ? [d.getUTCSeconds()] : []);
	return parts.map((n) => String(n).padStart(2, "0")).join(":");
}

frappe.pages["transportation-schedules-board"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({ parent: wrapper, title: __("Transportation Schedules"), single_column: true });
	$(wrapper).find(".page-head").hide();
	wrapper.tsb = new TransportationSchedulesBoard(wrapper);
};

class TransportationSchedulesBoard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		const q = new URLSearchParams(window.location.search);
		this.camp = q.get("camp") || "";
		this.theme = TSB_THEMES.includes(q.get("theme")) ? q.get("theme") : "charcoal";
		this.data = null;
		this.offset = 0;

		this.$root = $(`
			<div class="tsb-page">
				<div class="tsb-setup d-flex flex-wrap align-items-end p-3 mb-3 frappe-card">
					<label class="mr-3 mb-2">
						<span class="d-block small text-muted">${__("Accommodation")}</span>
						<select class="form-control tsb-camp"></select>
					</label>
					<label class="mr-3 mb-2">
						<span class="d-block small text-muted">${__("Theme")}</span>
						<select class="form-control tsb-theme">
							<option value="charcoal">${__("Charcoal")}</option>
							<option value="light">${__("Light")}</option>
						</select>
					</label>
					<button class="btn btn-primary mb-2 tsb-go">${__("Go full screen")}</button>
				</div>
				<div class="tsb-board"></div>
			</div>
		`).appendTo($(wrapper).find(".layout-main-section").empty());
		this.$setup = this.$root.find(".tsb-setup");
		this.$board = this.$root.find(".tsb-board");
		this.$camp = this.$root.find(".tsb-camp");
		this.$theme = this.$root.find(".tsb-theme").val(this.theme);

		this.$camp.on("change", () => this.select(this.$camp.val(), this.theme));
		this.$theme.on("change", () => this.select(this.camp, this.$theme.val()));
		this.$root.find(".tsb-go").on("click", () => {
			const board = this.$board[0];
			if (board.requestFullscreen) board.requestFullscreen().catch(() => {});
		});
		document.addEventListener("fullscreenchange", () => this.syncMode());
		window.addEventListener("resize", () => this.syncMode());

		this.loadCamps();
		this.syncMode();
		setInterval(() => this.active() && this.fetch(), POLL_MS);
		setInterval(() => this.active() && this.tick(), 1000);
	}

	active() {
		return $(this.wrapper).is(":visible");
	}

	loadCamps() {
		frappe.xcall(TSB_API + "get_active_accommodations").then((camps) => {
			camps = camps || [];
			this.camps = camps;
			this.$camp.empty().append(`<option value="">${__("Select accommodation")}</option>`);
			camps.forEach((c) => {
				this.$camp.append($("<option>").val(c.name).text(c.accommodation || c.name));
			});
			if (!camps.some((c) => c.name === this.camp)) this.camp = "";
			this.$camp.val(this.camp);
			this.fetch();
		});
	}

	select(camp, theme) {
		const changed = camp !== this.camp;
		this.camp = camp || "";
		this.theme = TSB_THEMES.includes(theme) ? theme : "charcoal";
		const url = new URL(window.location.href);
		url.searchParams.delete("camp");
		url.searchParams.delete("theme");
		if (this.camp) url.searchParams.set("camp", this.camp);
		url.searchParams.set("theme", this.theme);
		history.replaceState(history.state, "", url.toString());
		if (changed) {
			this.data = null;
			this.fetch();
		}
		this.render();
	}

	// Full screen, an installed full-screen app, or a kiosk / F11 window.
	boardMode() {
		return !!(
			document.fullscreenElement
			|| window.matchMedia("(display-mode: fullscreen)").matches
			|| (window.innerWidth >= screen.width && window.innerHeight >= screen.height)
		);
	}

	syncMode() {
		const board = this.boardMode() && !!this.camp;
		this.$setup.toggleClass("d-none", board);
		this.$board.toggleClass("tsb-fill", board);
		if (!board) {
			this.$camp.val(this.camp);
			this.$theme.val(this.theme);
		}
	}

	fetch() {
		if (!this.camp) {
			this.render();
			return;
		}
		const camp = this.camp;
		frappe.xcall(TSB_API + "get_lobby_board", { accommodation: camp }).then((data) => {
			if (camp !== this.camp) return;
			this.data = data;
			this.offset = naiveMs(data.server_now) - Date.now();
			this.render();
		}).catch(() => {});
	}

	now() {
		return Date.now() + this.offset;
	}

	render() {
		this.$board.attr("data-theme", this.theme);
		if (!this.camp) {
			this.$board.html(`<div class="tsb-empty"><b>${__("Select an accommodation to start the board")}</b></div>`);
			return;
		}
		const name = this.data ? this.data.accommodation_name : "";
		this.$board.html(`
			<header class="tsb-head">
				<span class="tsb-brand">${TSB_MARK}</span>
				<span class="tsb-title"><b>${__("Transportation Schedules")}</b><span lang="ar">جدول مواعيد النقل</span></span>
				<span class="tsb-where"><b>${frappe.utils.escape_html(name)}</b></span>
				<span class="tsb-clock"></span>
			</header>
			<main class="tsb-main"></main>
		`);
		this.tick();
	}

	tick() {
		if (!this.data) return;
		this.$board.find(".tsb-clock").text(clockText(this.now(), true));
	}
}
