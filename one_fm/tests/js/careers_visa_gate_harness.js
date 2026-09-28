// Runs the SHIPPED show_visa_or_skip / is_kuwaiti from job_application.js against a fake
// page. Which sections a nationality reveals is exactly what this story is about, so the
// methods are read out of the file rather than copied here.

const fs = require("fs");
const path = require("path");

const source = fs.readFileSync(
	path.join(__dirname, "..", "..", "templates", "pages", "job_application.js"),
	"utf8"
);

function extract(name) {
	const start = source.indexOf(`  ${name}: function() {`);
	if (start === -1) {
		throw new Error(`${name} is not in job_application.js`);
	}
	const rest = source.slice(start);
	const end = rest.indexOf("\n  },\n") + "\n  }".length;
	return rest.slice(0, end);
}

const args = JSON.parse(process.argv[2]);
// A second nationality means: reach the visa step as the first one, then change the
// dropdown to the second, exactly as a candidate correcting their answer does.
let nationality = args.nationality;

// Each selector is a section with a `hide` class, exactly as the page ships it.
const sections = {
	".visa": { hidden: true },
	".visa_type": { hidden: true },
	".in_kuwait": { hidden: true },
};

// What the candidate has answered, and what the submit would read back off the page.
const answers = {
	visa: args.answered_visa === undefined ? null : args.answered_visa,
	visa_type: args.answered_visa_type === undefined ? null : args.answered_visa_type,
};

function $(selector) {
	if (selector === ".nationality_list") {
		return { val: () => nationality };
	}
	if (selector === "#visa input[type='radio']") {
		return {
			prop: (name, value) => {
				if (name === "checked" && value === false) answers.visa = null;
			},
		};
	}
	const section = sections[selector];
	if (!section) {
		throw new Error(`the page has no ${selector}`);
	}
	return {
		val: (value) => {
			if (value === undefined) return answers[selector.slice(1)];
			answers[selector.slice(1)] = value === "" ? null : value;
		},
		hasClass: (name) => name === "hide" && section.hidden,
		addClass: (name) => {
			if (name === "hide") section.hidden = true;
		},
		removeClass: (name) => {
			if (name === "hide") section.hidden = false;
		},
	};
}

const page = eval(
	`({${extract("show_visa_or_skip")},${extract("apply_visa_gate")},${extract("is_kuwaiti")}})`
);
page.show_visa_or_skip();

if (args.then_nationality !== undefined) {
	nationality = args.then_nationality;
	// What the nationality handler does once the flow has reached the visa step.
	if (page.visa_step_reached) {
		page.apply_visa_gate();
	}
}

process.stdout.write(
	JSON.stringify({
		is_kuwaiti: page.is_kuwaiti(),
		shown: Object.keys(sections).filter((key) => !sections[key].hidden),
		// What submit_job_application would send.
		answers: answers,
	})
);
