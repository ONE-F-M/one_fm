// Loads the real job_offer.js and exercises visa_request_blockers against fixed dates.
// The point is to run the shipped rule rather than assert on its source text: the 18-month
// and 21-year boundaries are the story, and a grep would pass on an off-by-one.
const fs = require("fs");
const path = require("path");

const SOURCE = path.join(__dirname, "..", "..", "public", "js", "doctype_js", "job_offer.js");

function pad(n) { return String(n).padStart(2, "0"); }
function fmt(d) { return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`; }
function parse(s) { const [y, m, d] = s.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); }

const TODAY = process.env.TODAY || "2026-09-18";

global.frappe = {
	ui: { form: { on() {} } },
	datetime: {
		get_today: () => TODAY,
		add_months(dateStr, months) {
			const d = parse(dateStr);
			const day = d.getUTCDate();
			d.setUTCDate(1);
			d.setUTCMonth(d.getUTCMonth() + months);
			// clamp, the way a month-end date has to be clamped
			const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
			d.setUTCDate(Math.min(day, last));
			return fmt(d);
		},
		get_day_diff: (a, b) => Math.round((parse(a) - parse(b)) / 86400000),
	},
};
global.__ = (s) => s;
global.frappe.db = { get_value() {} };
global.frappe.model = {};
global.frappe.call = () => {};

// The file declares the helper at top level; eval keeps it in reach.
eval(fs.readFileSync(SOURCE, "utf8"));

const doc_fields = JSON.parse(process.argv[2] || "{}");
const applicant = JSON.parse(process.argv[3] || "{}");
process.stdout.write(JSON.stringify(visa_request_blockers({ doc: doc_fields }, applicant)));
