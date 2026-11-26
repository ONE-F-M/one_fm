/**
 * Transportation Schedules board: the lobby TV of one accommodation.
 *
 * URL: /app/transportation-schedules-board?camp=<Accommodation>&theme=charcoal|light
 * The setup bar picks camp and theme; in board mode (full screen, or a kiosk window
 * that fills the screen) only the board shows and nothing invites interaction.
 * Status, window and countdown are derived from the server clock, never stored.
 */

// ── Board rules (pure; test_board_rules.js reads this block)
const WINDOW_MINUTES = 120;
const DEPARTED_GRACE_MINUTES = 15;
const BOARDING_LEAD_MINUTES = 20;
const ROTATE_MS = 7000;
const POLL_MS = 60000;

const TSB_MINUTE = 60000;

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

function windowEnd(now) {
	return now + WINDOW_MINUTES * TSB_MINUTE;
}

function windowLabel(now) {
	return `${clockText(now)} → ${clockText(windowEnd(now))}`;
}

// Departed up to the grace period ago, up to the end of the window, earliest first.
function visibleTrips(trips, now) {
	return (trips || [])
		.filter((t) => {
			const dep = naiveMs(t.departure);
			return dep >= now - DEPARTED_GRACE_MINUTES * TSB_MINUTE && dep <= windowEnd(now);
		})
		.sort((a, b) => naiveMs(a.departure) - naiveMs(b.departure));
}

// Boarding wins over QoA from the lead time before departure.
function statusOf(trip, now) {
	const dep = naiveMs(trip.departure);
	if (now >= dep) return "departed";
	if (dep - now <= BOARDING_LEAD_MINUTES * TSB_MINUTE) return "boarding";
	if (trip.qoa_at && now >= naiveMs(trip.qoa_at)) return "qoa";
	return "scheduled";
}

function statusText(trip, now) {
	return {
		departed: __("Departed"),
		boarding: __("Boarding now"),
		qoa: __("QoA {0}", [trip.qoa]),
		scheduled: __("Scheduled"),
	}[statusOf(trip, now)];
}

function countdownText(trip, now) {
	const dep = naiveMs(trip.departure);
	if (now >= dep) return __("Departed {0} min ago", [Math.floor((now - dep) / TSB_MINUTE)]);
	const left = Math.ceil((dep - now) / TSB_MINUTE);
	if (left < 60) return __("Departs in {0} min", [left]);
	return __("Departs in {0} h {1} min", [Math.floor(left / 60), left % 60]);
}

function layoutFor(count) {
	if (!count) return "empty";
	if (count === 1) return "single";
	return count <= 6 ? "pair" : "grid";
}

function emptyText() {
	const hours = WINDOW_MINUTES / 60;
	if (WINDOW_MINUTES === 60) {
		return { en: __("No departures in the next hour"), ar: "لا توجد رحلات خلال الساعة القادمة" };
	}
	if (WINDOW_MINUTES === 120) {
		return { en: __("No departures in the next 2 hours"), ar: "لا توجد رحلات خلال الساعتين القادمتين" };
	}
	if (Number.isInteger(hours)) {
		return { en: __("No departures in the next {0} hours", [hours]), ar: `لا توجد رحلات خلال ${hours} ساعات القادمة` };
	}
	return { en: __("No departures in the next {0} minutes", [WINDOW_MINUTES]), ar: `لا توجد رحلات خلال ${WINDOW_MINUTES} دقيقة القادمة` };
}

function initials(name) {
	return String(name || "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
}
// ── End of board rules

const TSB_API = "one_fm.one_fm.doctype.transportation_manifest.manifest_board.";
const TSB_THEMES = ["charcoal", "light"];

const TSB_MARK = `<svg xmlns="http://www.w3.org/2000/svg" class="tsb-mark" fill="currentColor" role="img" aria-label="ONE FM" viewBox="0 0 175.591 68.494"><g transform="translate(-71.377 -66.91)"><g><path d="M136.057,116.522a19.824,19.824,0,0,1-7.508-7.734,23.1,23.1,0,0,1,0-21.569,20.085,20.085,0,0,1,7.508-7.733,23.1,23.1,0,0,1,22.3,0,20.041,20.041,0,0,1,7.537,7.733,23.1,23.1,0,0,1,0,21.569,19.781,19.781,0,0,1-7.537,7.734,23.308,23.308,0,0,1-22.3,0Zm4.387-30.709a13.491,13.491,0,0,0-4.921,5.034A14.159,14.159,0,0,0,133.7,97.99a14.31,14.31,0,0,0,1.828,7.17,13.434,13.434,0,0,0,4.921,5.063,13.478,13.478,0,0,0,13.555,0,13.237,13.237,0,0,0,4.892-5.063,14.49,14.49,0,0,0,1.8-7.17,14.336,14.336,0,0,0-1.8-7.143A13.292,13.292,0,0,0,154,85.813a13.478,13.478,0,0,0-13.555,0Z" /><path d="M209.668,118.575,182.559,94.109v20.753a3.343,3.343,0,0,1-3.713,3.713h-4.1V77.4h.843l27.053,24.916v-21.2a3.344,3.344,0,0,1,3.712-3.713h4.162v41.171Z" /><path d="M216.7,77.4h30.258v3.488A3.381,3.381,0,0,1,246,83.479a3.87,3.87,0,0,1-2.755.9h-18.73V94.671h17.661v3.262a3.343,3.343,0,0,1-3.712,3.712H224.514V111.6h18.673a3.654,3.654,0,0,1,3.768,3.768v3.207H216.7Z" /><g><path d="M125.872,131.309v-6.621h3.9v1.018h-2.748v1.676h2.443v1.009h-2.443v2.918Z" /><path d="M130.929,131.309h-1.178l3.256-6.836h.091l3.142,6.836h-1.224l-.534-1.178h-3.01Zm.973-2.123h2.169L133,126.715Z" /><path d="M142,130.88a3.508,3.508,0,0,1-.95.479,3.342,3.342,0,0,1-1.041.164,3.265,3.265,0,0,1-2.06-.721,3.329,3.329,0,0,1-.947-1.222,3.752,3.752,0,0,1-.331-1.582,3.518,3.518,0,0,1,.961-2.528,3.19,3.19,0,0,1,2.4-1.006,3.277,3.277,0,0,1,1.007.155,3.6,3.6,0,0,1,.938.47l-.118,1.293a2.852,2.852,0,0,0-.832-.635,2.193,2.193,0,0,0-2.534.477,2.511,2.511,0,0,0-.63,1.765,2.472,2.472,0,0,0,.614,1.724,2.018,2.018,0,0,0,1.564.678,2.337,2.337,0,0,0,1.032-.238,3.612,3.612,0,0,0,.991-.744Z" /><path d="M143.461,131.309v-6.621h1.169v6.621Z" /><path d="M146.015,131.309v-6.621h1.16v5.585h2.845v1.036Z" /><path d="M151.412,131.309v-6.621h1.169v6.621Z" /><path d="M157.382,125.7v5.612h-1.169V125.7h-2.238v-1.009h5.631V125.7Z" /><path d="M160.989,131.309v-6.621h1.168v6.621Z" /><path d="M163.549,131.309v-6.621H167.4v1.018h-2.722v1.63h2.338v1.009h-2.338v1.937h2.768v1.027Z" /><path d="M168.845,129.838a5.153,5.153,0,0,0,.987.512,2.484,2.484,0,0,0,.85.164,1.315,1.315,0,0,0,.844-.258.814.814,0,0,0,.324-.668.962.962,0,0,0-.216-.615,2.838,2.838,0,0,0-.756-.591l-.5-.3a3.584,3.584,0,0,1-1.075-.88,1.621,1.621,0,0,1-.318-.988,1.6,1.6,0,0,1,.557-1.263,2.132,2.132,0,0,1,1.453-.486,3.619,3.619,0,0,1,.842.1,3.842,3.842,0,0,1,.824.3l-.036,1.054a5.47,5.47,0,0,0-.87-.394,2.158,2.158,0,0,0-.673-.126,1.15,1.15,0,0,0-.72.2.664.664,0,0,0-.262.555.751.751,0,0,0,.191.5,2.97,2.97,0,0,0,.713.53l.479.278a3.92,3.92,0,0,1,1.183.98,1.857,1.857,0,0,1,.351,1.116,1.808,1.808,0,0,1-.623,1.43,2.439,2.439,0,0,1-1.66.543,4.337,4.337,0,0,1-.924-.1,3.944,3.944,0,0,1-.861-.295Z" /><path d="M176.845,131.309l1.356-6.836h.078l2.365,4.845L183,124.473h.073l1.346,6.836h-1.136l-.722-3.74-1.872,3.964h-.1l-1.945-3.964-.722,3.74Z" /><path d="M186.992,131.309h-1.177l3.255-6.836h.092l3.141,6.836h-1.224l-.534-1.178h-3.009Zm.973-2.123h2.17l-1.074-2.471Z" /><path d="M193.7,131.309v-6.836h.123l4.265,4.425v-4.21h1.133v6.835H199.1l-4.275-4.424v4.21Z" /><path d="M201.788,131.309H200.61l3.255-6.836h.092l3.142,6.836h-1.225l-.534-1.178h-3.009Zm.972-2.123h2.17l-1.074-2.471Z" /><path d="M213.046,126.373a3.345,3.345,0,0,0-.966-.642,2.589,2.589,0,0,0-1.024-.213,2.221,2.221,0,0,0-1.69.686,2.487,2.487,0,0,0-.649,1.785,2.421,2.421,0,0,0,.649,1.758,2.252,2.252,0,0,0,1.7.671,2.854,2.854,0,0,0,.6-.066,4.406,4.406,0,0,0,.688-.212v-1.384h-1.6v-1.018H213.5v3.133a5.326,5.326,0,0,1-1.206.495,4.73,4.73,0,0,1-1.237.167,3.54,3.54,0,1,1,0-7.078,4.149,4.149,0,0,1,1.068.137,4.558,4.558,0,0,1,1.028.415Z" /><path d="M214.881,131.309v-6.621h3.854v1.018h-2.722v1.63h2.339v1.009h-2.339v1.937h2.768v1.027Z" /><path d="M220.17,131.309l1.357-6.836h.077l2.365,4.845,2.357-4.845h.072l1.348,6.836h-1.138l-.721-3.74-1.872,3.964h-.1l-1.945-3.964-.721,3.74Z" /><path d="M229.13,131.309v-6.621h3.854v1.018h-2.721v1.63H232.6v1.009h-2.338v1.937h2.767v1.027Z" /><path d="M234.422,131.309v-6.836h.124l4.264,4.425v-4.21h1.133v6.835h-.123l-4.274-4.424v4.21Z" /><path d="M244.745,125.7v5.612h-1.169V125.7h-2.238v-1.009h5.63V125.7Z" /></g><path d="M104.036,82.88l-15.7,9.134L71.377,80.578l23.5-13.668Z" fill-rule="evenodd"/><path d="M94.855,135.4l18.6-10.625V77.127L94.877,66.91Z" class="tsb-mark-dim" fill-rule="evenodd"/></g></g></svg>`;

const TSB_CSS = `
.tsb-board { --tsb-primary: #9a4500; --tsb-accent: #f97316; --tsb-success: #22c55e;
	--tsb-outbound: #1565c0; --tsb-return: #c2410c; --tsb-error: #ef4444;
	--tsb-t-hero: clamp(46px, 5.6vw, 104px); --tsb-t-clock: clamp(28px, 2.7vw, 50px);
	--tsb-t-name: clamp(15px, 1.18vw, 22px); --tsb-t-row: clamp(14px, 1.08vw, 20px);
	--tsb-t-body: clamp(14px, 1.05vw, 20px); --tsb-t-label: clamp(11px, .78vw, 15px);
	--tsb-s1: 8px; --tsb-s2: 16px; --tsb-s3: 24px; --tsb-radius: 14px;
	--tsb-mono: "Roboto Mono", ui-monospace, monospace;
	display: grid; grid-template-rows: auto 1fr auto; gap: var(--tsb-s2); height: 80vh;
	padding: var(--tsb-s3) var(--tsb-s3) var(--tsb-s2); overflow: hidden; border-radius: var(--tsb-radius);
	background: var(--tsb-surface); color: var(--tsb-text); font-feature-settings: "tnum" 1; }
.tsb-board[data-theme="charcoal"] { --tsb-surface: #16181b; --tsb-surface-low: #1b1e22; --tsb-surface-high: #2a2f35;
	--tsb-text: #eef0f3; --tsb-muted: #a8afb7; --tsb-outline: #767d85; --tsb-line: #333940;
	--tsb-out-text: color-mix(in srgb, var(--tsb-outbound) 55%, #fff);
	--tsb-ret-text: color-mix(in srgb, var(--tsb-return) 70%, #fff); --tsb-focus: var(--tsb-accent); }
.tsb-board[data-theme="light"] { --tsb-surface: #ffffff; --tsb-surface-low: #fafafa; --tsb-surface-high: #f0f0f0;
	--tsb-text: #1f1f1f; --tsb-muted: #525252; --tsb-outline: #737373; --tsb-line: #e2e2e2;
	--tsb-out-text: var(--tsb-outbound); --tsb-ret-text: var(--tsb-return); --tsb-focus: var(--tsb-primary); }
.tsb-board.tsb-fill { position: fixed; inset: 0; z-index: 1050; height: 100vh; border-radius: 0; cursor: none; }
.tsb-board.tsb-fill * { cursor: none; }
.tsb-board:fullscreen { height: 100vh; border-radius: 0; cursor: none; }
.tsb-head { display: flex; align-items: center; gap: var(--tsb-s3); padding-bottom: var(--tsb-s2);
	border-bottom: 1px solid var(--tsb-line); }
.tsb-mark { height: clamp(32px, 3vw, 58px); width: auto; flex: 0 0 auto; }
.tsb-mark-dim { opacity: .6; }
.tsb-title b { display: block; font-size: clamp(18px, 1.5vw, 28px); font-weight: 700; }
.tsb-title span, .tsb-where span, .tsb-clock small { display: block; font-size: var(--tsb-t-label); color: var(--tsb-muted); }
.tsb-where { margin-left: auto; text-align: right; }
.tsb-where b { display: block; font-size: clamp(16px, 1.3vw, 25px); }
.tsb-clock { text-align: right; }
.tsb-clock b { display: block; font-family: var(--tsb-mono); font-size: var(--tsb-t-clock); line-height: 1; }
.tsb-clock small { font-family: var(--tsb-mono); margin-top: 5px; }
.tsb-main { display: grid; grid-template-columns: minmax(0, 27fr) minmax(0, 73fr); gap: var(--tsb-s3); min-height: 0; }
.tsb-h { font-size: var(--tsb-t-label); font-weight: 700; letter-spacing: .18em; text-transform: uppercase;
	color: var(--tsb-muted); margin: 0 0 var(--tsb-s2); }
.tsb-rail { display: flex; flex-direction: column; min-height: 0; }
.tsb-rail ul { list-style: none; margin: 0; padding: 0; overflow: hidden; min-height: 0; }
.tsb-row { display: grid; grid-template-columns: auto 1fr auto; gap: 2px var(--tsb-s2); align-items: center;
	padding: var(--tsb-s1) var(--tsb-s1); border-bottom: 1px solid var(--tsb-line); }
.tsb-row-time { font-family: var(--tsb-mono); font-weight: 700; font-size: var(--tsb-t-row); grid-row: span 2; }
.tsb-row-name { font-weight: 700; font-size: var(--tsb-t-row); }
.tsb-row-dest { grid-column: 2 / 4; font-size: var(--tsb-t-label); color: var(--tsb-muted);
	overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tsb-row.is-on { background: var(--tsb-surface-high); box-shadow: inset 4px 0 0 var(--tsb-focus); }
.tsb-row.is-gone { opacity: .45; }
.tsb-dir { font-size: var(--tsb-t-label); font-weight: 700; letter-spacing: .1em; text-transform: uppercase; white-space: nowrap; text-align: right; }
.tsb-dir small { display: block; font-weight: 500; letter-spacing: 0; text-transform: none; color: var(--tsb-muted); }
.tsb-out { color: var(--tsb-out-text); }
.tsb-ret { color: var(--tsb-ret-text); }
.tsb-focus { display: grid; grid-template-rows: auto auto 1fr; gap: var(--tsb-s2); min-height: 0; padding: var(--tsb-s3);
	background: var(--tsb-surface-low); border: 1px solid var(--tsb-line); border-radius: var(--tsb-radius); }
.tsb-focus.is-boarding { border-color: var(--tsb-success); }
.tsb-fhead { display: grid; grid-template-columns: auto 1fr auto; gap: var(--tsb-s3); align-items: center; }
.tsb-when { display: flex; align-items: baseline; gap: var(--tsb-s2); }
.tsb-dep { font-family: var(--tsb-mono); font-weight: 700; font-size: var(--tsb-t-hero); line-height: .9; letter-spacing: -.04em; }
.tsb-code b { display: block; font-size: clamp(20px, 1.8vw, 34px); line-height: 1; }
.tsb-code small, .tsb-dirbox small { display: block; font-size: var(--tsb-t-label); color: var(--tsb-muted);
	letter-spacing: .12em; text-transform: uppercase; margin-top: 5px; }
.tsb-mid { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.tsb-dest { font-weight: 700; font-size: clamp(17px, 1.5vw, 29px); line-height: 1.15; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tsb-meta { font-size: var(--tsb-t-body); color: var(--tsb-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tsb-meta b { color: var(--tsb-text); font-weight: 500; }
.tsb-tel { font-family: var(--tsb-mono); font-weight: 700; color: var(--tsb-text); }
.tsb-dirbox { text-align: right; }
.tsb-dirbox b { display: block; font-size: clamp(20px, 1.9vw, 36px); font-weight: 900; line-height: 1.1; }
.tsb-status { display: flex; flex-wrap: wrap; align-items: center; gap: var(--tsb-s2); padding: var(--tsb-s1) 0;
	border-top: 1px solid var(--tsb-line); border-bottom: 1px solid var(--tsb-line); font-size: var(--tsb-t-body); }
.tsb-status b { font-weight: 700; }
.tsb-info { color: var(--tsb-muted); }
.tsb-info b { color: var(--tsb-text); font-weight: 500; }
.tsb-seats { margin-left: auto; font-family: var(--tsb-mono); color: var(--tsb-muted); }
.tsb-seats b { color: var(--tsb-text); }
.tsb-chip { display: inline-flex; align-items: center; gap: 7px; padding: 5px 12px; border-radius: 999px; border: 1px solid transparent;
	font-size: var(--tsb-t-label); font-weight: 700; letter-spacing: .12em; text-transform: uppercase; white-space: nowrap; }
.tsb-chip-boarding { color: var(--tsb-success); border-color: var(--tsb-success); background: color-mix(in srgb, var(--tsb-success) 14%, transparent);
	animation: tsb-pulse 1.9s ease-in-out infinite; }
.tsb-chip-qoa { color: var(--tsb-accent); border-color: var(--tsb-accent); background: color-mix(in srgb, var(--tsb-accent) 14%, transparent); }
.tsb-chip-scheduled { color: var(--tsb-muted); background: var(--tsb-surface-high); }
.tsb-chip-departed { color: var(--tsb-outline); border-color: var(--tsb-line); }
@keyframes tsb-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
.tsb-pax { display: flex; flex-direction: column; min-height: 0; }
.tsb-pax-head { display: flex; align-items: baseline; margin-bottom: var(--tsb-s1); }
.tsb-pax-head .tsb-h { margin: 0; }
.tsb-pg { margin-left: auto; font-family: var(--tsb-mono); font-size: var(--tsb-t-label); color: var(--tsb-muted); }
.tsb-pax-body { flex: 1; min-height: 0; overflow: hidden; }
.tsb-grid { display: grid; height: 100%; grid-auto-flow: column; gap: 0 var(--tsb-s2); align-content: start;
	grid-template-rows: repeat(var(--tsb-rows, 1), auto); grid-template-columns: repeat(var(--tsb-cols, 1), minmax(0, 1fr)); }
.tsb-p { display: grid; grid-template-columns: auto 1fr auto; gap: var(--tsb-s1); align-items: center; padding: 5px 0;
	border-bottom: 1px solid var(--tsb-line); min-width: 0; }
.tsb-n { font-family: var(--tsb-mono); font-size: var(--tsb-t-label); color: var(--tsb-outline); min-width: 2.2em; }
.tsb-nm { font-size: var(--tsb-t-name); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tsb-dp { font-size: var(--tsb-t-label); color: var(--tsb-muted); white-space: nowrap; max-width: 10em; overflow: hidden; text-overflow: ellipsis; }
.tsb-reliever .tsb-nm, .tsb-reliever b, .tsb-sub { color: var(--tsb-out-text); }
.tsb-pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--tsb-s2) var(--tsb-s3); align-content: space-evenly; height: 100%; }
.tsb-card { display: flex; align-items: center; gap: var(--tsb-s2); min-width: 0; padding: var(--tsb-s1) 0; border-bottom: 1px solid var(--tsb-line); }
.tsb-av { flex: 0 0 auto; display: grid; place-items: center; width: clamp(40px, 2.9vw, 56px); aspect-ratio: 1; border-radius: 50%;
	background: var(--tsb-surface-high); font-weight: 700; font-size: clamp(14px, 1.05vw, 20px); }
.tsb-card b { display: block; font-size: clamp(17px, 1.4vw, 26px); line-height: 1.15; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tsb-card span span { display: block; font-size: var(--tsb-t-label); color: var(--tsb-muted); margin-top: 3px; }
.tsb-card > span:last-child { min-width: 0; }
.tsb-solo { display: flex; align-items: center; justify-content: center; gap: var(--tsb-s3); height: 100%; }
.tsb-solo .tsb-av { width: clamp(60px, 4.6vw, 88px); font-size: clamp(20px, 1.6vw, 30px); }
.tsb-solo b { display: block; font-size: clamp(24px, 2vw, 38px); }
.tsb-solo span span { display: block; font-size: var(--tsb-t-body); color: var(--tsb-muted); margin-top: 6px; }
.tsb-sub { font-size: var(--tsb-t-label); margin-top: var(--tsb-s1); }
.tsb-notice { display: flex; align-items: center; gap: var(--tsb-s3); padding: var(--tsb-s3); margin: auto 0;
	border: 1px dashed var(--tsb-outline); border-radius: var(--tsb-radius); }
.tsb-notice-mark { font-weight: 900; font-size: clamp(28px, 2.4vw, 46px); color: var(--tsb-outline); }
.tsb-notice b { display: block; font-size: clamp(18px, 1.5vw, 28px); }
.tsb-notice span span { display: block; font-size: var(--tsb-t-body); color: var(--tsb-muted); margin-top: 6px; }
.tsb-none { grid-row: 2; display: grid; place-content: center; text-align: center; gap: var(--tsb-s2); }
.tsb-none b { font-size: clamp(22px, 2vw, 38px); }
.tsb-none span { font-size: var(--tsb-t-body); color: var(--tsb-muted); }
.tsb-foot { display: flex; align-items: center; gap: var(--tsb-s3); padding-top: var(--tsb-s1); border-top: 1px solid var(--tsb-line);
	font-size: var(--tsb-t-label); color: var(--tsb-muted); letter-spacing: .1em; text-transform: uppercase; }
.tsb-prog { width: clamp(120px, 14vw, 300px); height: 3px; border-radius: 2px; overflow: hidden; background: var(--tsb-surface-high); }
.tsb-prog i { display: block; height: 100%; width: 100%; background: var(--tsb-muted); transform-origin: left;
	animation: tsb-prog var(--tsb-rotate, 7000ms) linear forwards; }
@keyframes tsb-prog { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.tsb-legend { margin-left: auto; display: flex; gap: var(--tsb-s3); }
.tsb-legend span::before { content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 7px; background: currentColor; }
.tsb-legend .tsb-lg-board { color: var(--tsb-success); }
.tsb-legend .tsb-lg-qoa { color: var(--tsb-accent); }
`;

function esc(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
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
		this.focusKey = null;
		this.paxPage = 0;
		this.pages = 1;
		this.shown = null;

		this.$root = $(`
			<div class="tsb-page">
				<style>${TSB_CSS}</style>
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
		this.$board[0].style.setProperty("--tsb-rotate", `${ROTATE_MS}ms`);
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
		let pending = false;
		new ResizeObserver(() => {
			if (pending) return;
			pending = true;
			requestAnimationFrame(() => {
				pending = false;
				this.render();
			});
		}).observe(this.$board[0]);

		this.loadCamps();
		this.syncMode();
		setInterval(() => this.active() && this.fetch(), POLL_MS);
		setInterval(() => this.active() && this.tick(), 1000);
		setInterval(() => this.active() && this.advance(), ROTATE_MS);
	}

	active() {
		return $(this.wrapper).is(":visible");
	}

	loadCamps() {
		frappe.xcall(TSB_API + "get_active_accommodations").then((camps) => {
			camps = camps || [];
			this.$camp.empty().append(`<option value="">${__("Select accommodation")}</option>`);
			camps.forEach((c) => {
				this.$camp.append($("<option>").val(c.name).text(c.accommodation || c.name));
			});
			if (!camps.some((c) => c.name === this.camp)) this.camp = "";
			this.$camp.val(this.camp);
			this.syncMode();
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
			this.focusKey = null;
			this.fetch();
		}
		this.syncMode();
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
		this.$board.toggleClass("tsb-fill", board && !document.fullscreenElement);
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
			const first = !this.data;
			this.data = data;
			this.offset = naiveMs(data.server_now) - Date.now();
			// Later polls are picked up by the next tick and rotation step.
			if (first) this.render();
		}).catch(() => {});
	}

	now() {
		return Date.now() + this.offset;
	}

	visible() {
		return this.data ? visibleTrips(this.data.trips, this.now()) : [];
	}

	// The focused trip; first focus is the first trip not departed.
	focused(list) {
		let trip = list.find((t) => t.key === this.focusKey);
		if (!trip) {
			trip = list.find((t) => statusOf(t, this.now()) !== "departed") || list[0];
			this.focusKey = trip ? trip.key : null;
			this.paxPage = 0;
		}
		return trip;
	}

	advance() {
		const list = this.visible();
		if (this.paxPage + 1 < this.pages) {
			this.paxPage += 1;
		} else if (list.length) {
			const at = list.findIndex((t) => t.key === this.focusKey);
			this.focusKey = list[(at + 1) % list.length].key;
			this.paxPage = 0;
		}
		this.render();
	}

	render() {
		this.$board.attr("data-theme", this.theme);
		if (!this.camp) {
			this.shown = null;
			this.$board.html(`<div class="tsb-none"><b>${__("Select an accommodation to start the board")}</b></div>`);
			return;
		}
		const now = this.now();
		const list = this.visible();
		const name = this.data ? this.data.accommodation_name : "";
		const date = new Date(now).toLocaleDateString(undefined, {
			timeZone: "UTC", weekday: "long", day: "numeric", month: "long", year: "numeric",
		});
		this.$board.html(`
			<header class="tsb-head">
				${TSB_MARK}
				<span class="tsb-title"><b>${__("Transportation Schedules")}</b><span lang="ar" dir="rtl">جدول مواعيد النقل</span></span>
				<span class="tsb-where"><b>${esc(name)}</b><span>${this.data ? esc(date) : ""}</span></span>
				<span class="tsb-clock"><b></b><small></small></span>
			</header>
			<main class="tsb-main"></main>
			<footer class="tsb-foot">
				<span class="tsb-prog"><i></i></span>
				<span class="tsb-showing"></span>
				<span class="tsb-legend">
					<span class="tsb-lg-board">${__("Boarding")}</span>
					<span class="tsb-lg-qoa">${__("QoA")}</span>
					<span class="tsb-out">${__("Outward")}</span>
					<span class="tsb-ret">${__("Return")}</span>
				</span>
			</footer>
		`);
		const $main = this.$board.find(".tsb-main");
		this.pages = 1;
		if (!this.data) {
			// Waiting for the first poll.
		} else if (!list.length) {
			const text = emptyText();
			$main.replaceWith(`<section class="tsb-none"><b>${text.en}</b><span lang="ar" dir="rtl">${text.ar}</span><span>${esc(name)}</span></section>`);
		} else {
			$main.html(`
				<section class="tsb-rail"><h2 class="tsb-h">${__("Schedule")} · الجدول</h2><ul></ul></section>
				<section class="tsb-focus">
					<div class="tsb-fhead"></div>
					<div class="tsb-status"></div>
					<div class="tsb-pax">
						<div class="tsb-pax-head"><span class="tsb-h">${__("Passengers")} · الركاب</span><span class="tsb-pg"></span></div>
						<div class="tsb-pax-body"></div>
					</div>
				</section>
			`);
		}
		this.shown = null;
		this.tick();
		// After the header and status line are drawn, so the grid measures the space left.
		if (this.data && list.length) this.renderPassengers(this.focused(list));
	}

	// Once a second: clock, window, rail, focus header and status line.
	tick() {
		if (!this.camp || !this.data) return;
		const now = this.now();
		const list = this.visible();
		const shown = list.map((t) => t.key).join(",");
		if (this.shown !== null && shown !== this.shown) return this.render();
		this.shown = shown;
		this.$board.find(".tsb-clock b").text(clockText(now, true));
		this.$board.find(".tsb-clock small").text(windowLabel(now));
		if (!list.length) return;
		const trip = this.focused(list);
		this.$board.find(".tsb-showing").text(__("Showing {0} of {1}", [list.indexOf(trip) + 1, list.length]));
		this.$board.find(".tsb-rail ul").html(list.map((t) => this.railRow(t, t === trip, now)).join(""));
		this.$board.find(".tsb-focus").toggleClass("is-boarding", statusOf(trip, now) === "boarding");
		this.$board.find(".tsb-fhead").html(this.focusHead(trip));
		this.$board.find(".tsb-status").html(this.statusLine(trip, now));
	}

	direction(trip) {
		const leg = trip.own_leg || trip.direction;
		return {
			cls: leg === "Return" ? "tsb-ret" : "tsb-out",
			text: leg === "Return" ? __("Return") : __("Outward"),
			mixed: trip.direction === "Mixed" ? __("Mixed trip") : "",
		};
	}

	railRow(trip, on, now) {
		const dir = this.direction(trip);
		const classes = ["tsb-row", on ? "is-on" : "", statusOf(trip, now) === "departed" ? "is-gone" : ""].join(" ");
		const dest = [trip.first_destination, trip.passengers.length ? "" : __("empty run")].filter(Boolean).map(esc).join(" · ");
		return `<li class="${classes}">
			<span class="tsb-row-time">${esc(trip.trip_time)}</span>
			<span class="tsb-row-name">${esc(trip.trip_name)}</span>
			<span class="tsb-dir ${dir.cls}">${dir.text}${dir.mixed ? `<small>${dir.mixed}</small>` : ""}</span>
			<span class="tsb-row-dest">${dest}</span>
		</li>`;
	}

	focusHead(trip) {
		const dir = this.direction(trip);
		const vehicle = [trip.vehicle_type, trip.capacity ? __("{0} seats", [trip.capacity]) : ""].filter(Boolean).map(esc).join(" · ");
		return `
			<span class="tsb-when"><span class="tsb-dep">${esc(trip.trip_time)}</span>
				<span class="tsb-code"><b>${esc(trip.trip_name)}</b><small>${vehicle}</small></span></span>
			<span class="tsb-mid">
				<span class="tsb-dest">${esc(trip.first_destination || "")}</span>
				<span class="tsb-meta">${__("Plate")} <b>${esc(trip.license_plate || "—")}</b> · ${__("Driver")} <b>${esc(trip.driver || "—")}</b>
					${trip.driver_mobile ? ` · <span class="tsb-tel">${esc(trip.driver_mobile)}</span>` : ""}</span>
			</span>
			<span class="tsb-dirbox"><small>${__("Direction")}</small><b class="${dir.cls}">${dir.text}</b>${dir.mixed ? `<small>${dir.mixed}</small>` : ""}</span>
		`;
	}

	statusLine(trip, now) {
		const status = statusOf(trip, now);
		const paired = trip.paired_return
			? [trip.paired_return.trip_time, trip.paired_return.trip_name].filter(Boolean).map(esc).join(" · ")
			: "—";
		const capacity = esc(trip.capacity || "—");
		let seats = `${__("Seats")} <b>${trip.passengers.length}</b> / ${capacity}`;
		if (!trip.passengers.length && trip.joins_elsewhere.length) {
			const joins = trip.joins_elsewhere.map((j) => __("{0} join at {1}", [j.count, esc(j.accommodation)])).join(" · ");
			seats = `${__("Seats")} <b>0</b> / ${capacity} ${__("here")} · ${joins}`;
		}
		return `
			<span class="tsb-chip tsb-chip-${status}">${esc(statusText(trip, now))}</span>
			<b>${esc(countdownText(trip, now))}</b>
			<span class="tsb-info">${__("QoA")} <b>${esc(trip.qoa || "—")}</b> · ${__("Return")} <b>${paired}</b></span>
			<span class="tsb-seats">${seats}</span>
		`;
	}

	renderPassengers(trip) {
		const people = trip.passengers;
		const $body = this.$board.find(".tsb-pax-body");
		const $pg = this.$board.find(".tsb-pg");
		const dropOff = (p) => `${__("Drop-off")} · ${esc(p.drop_off || "")}`;
		const star = (p) => (p.is_reliever ? " ★" : "");
		const card = (p) => `<div class="tsb-card${p.is_reliever ? " tsb-reliever" : ""}"><span class="tsb-av">${esc(initials(p.name))}</span>
			<span><b>${esc(p.name)}${star(p)}</b><span>${dropOff(p)}</span></span></div>`;
		const layout = layoutFor(people.length);
		const subs = people.filter((p) => p.is_reliever);
		if (subs.length) {
			this.$board.find(".tsb-pax").append(subs.map((p) => `<div class="tsb-sub">★ ${__("Reliever {0} replaces {1}", [esc(p.name), esc(p.replaces)])}</div>`).join(""));
		}
		$pg.text(people.length ? __("{0} assigned", [people.length]) : __("0 boarding here"));

		if (layout === "empty") {
			const joins = trip.joins_elsewhere.map((j) => `
				<span>${__("{0} staff join at {1}", [j.count, esc(j.accommodation)])}</span>
				<span lang="ar" dir="rtl">ينضم ${j.count} موظفاً في ${esc(j.accommodation)}</span>`).join("");
			$body.html(`<div class="tsb-notice"><span class="tsb-notice-mark">0</span><span>
				<b>${__("No passengers from this accommodation")}</b>
				<span lang="ar" dir="rtl">لا يوجد ركاب من هذا السكن</span>${joins}</span></div>`);
			return;
		}
		if (layout === "single") {
			$body.html(card(people[0]).replace("tsb-card", "tsb-solo"));
		} else if (layout === "pair") {
			$body.html(`<div class="tsb-pair">${people.map(card).join("")}</div>`);
		} else {
			this.renderGrid($body, people, $pg);
		}
	}

	// Rows per column from one measured row, columns from the width; pages in place.
	renderGrid($body, people, $pg) {
		const row = (p, i) => `<div class="tsb-p${p.is_reliever ? " tsb-reliever" : ""}"><span class="tsb-n">${String(i + 1).padStart(2, "0")}</span>
			<span class="tsb-nm">${esc(p.name)}${p.is_reliever ? " ★" : ""}</span><span class="tsb-dp">${esc(p.drop_off || "")}</span></div>`;
		const $grid = $(`<div class="tsb-grid">${row(people[0], 0)}</div>`).appendTo($body);
		const rowHeight = $grid.children()[0].getBoundingClientRect().height || 1;
		const box = $grid[0].getBoundingClientRect();
		const rows = Math.max(1, Math.floor(box.height / rowHeight));
		// ponytail: a column is taken as ten row heights wide; measure a real column if drop-offs clip.
		const cols = Math.max(1, Math.min(4, Math.floor(box.width / (rowHeight * 10))));
		const size = rows * cols;
		this.pages = Math.max(1, Math.ceil(people.length / size));
		const page = this.paxPage % this.pages;
		const start = page * size;
		$grid[0].style.setProperty("--tsb-rows", String(rows));
		$grid[0].style.setProperty("--tsb-cols", String(cols));
		$grid.html(people.slice(start, start + size).map((p, i) => row(p, start + i)).join(""));
		if (this.pages > 1) $pg.text(`${page + 1} / ${this.pages}`);
	}
}
