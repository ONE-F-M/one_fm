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

// Each selector is a section with a `hide` class, exactly as the page ships it.
const sections = {
	".visa": { hidden: true },
	".visa_type": { hidden: true },
	".in_kuwait": { hidden: true },
};

function $(selector) {
	if (selector === ".nationality_list") {
		return { val: () => args.nationality };
	}
	const section = sections[selector];
	if (!section) {
		throw new Error(`the page has no ${selector}`);
	}
	return {
		hasClass: (name) => name === "hide" && section.hidden,
		addClass: (name) => {
			if (name === "hide") section.hidden = true;
		},
		removeClass: (name) => {
			if (name === "hide") section.hidden = false;
		},
	};
}

const page = eval(`({${extract("show_visa_or_skip")},${extract("is_kuwaiti")}})`);
page.show_visa_or_skip();

process.stdout.write(
	JSON.stringify({
		is_kuwaiti: page.is_kuwaiti(),
		shown: Object.keys(sections).filter((key) => !sections[key].hidden),
	})
);
