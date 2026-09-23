// Runs the SHIPPED uncheckedRowIds and bulkPresentBtnHtml from
// transportation_manifest_page.js. Which chips the bulk action picks up is exactly the
// kind of off-by-one a grep cannot see, so the functions are read out of the file rather
// than copied here.

const fs = require("fs");
const path = require("path");

const source = fs.readFileSync(
	path.join(
		__dirname,
		"..",
		"..",
		"one_fm",
		"page",
		"transportation_manifest_page",
		"transportation_manifest_page.js"
	),
	"utf8"
);

function extract(name) {
	const start = source.indexOf(`function ${name}(`);
	if (start === -1) {
		throw new Error(`${name} is not in transportation_manifest_page.js`);
	}
	// Up to the blank line before the next top-level function in the same block.
	const rest = source.slice(start);
	const end = rest.indexOf("\n\t}\n") + "\n\t}\n".length;
	return rest.slice(0, end);
}

const window = { checkerState: {} };
eval(extract("uncheckedRowIds"));
eval(extract("bulkPresentBtnHtml"));

const args = JSON.parse(process.argv[2]);
window.checkerState = args.checkerState || {};

process.stdout.write(
	JSON.stringify({
		pending: uncheckedRowIds(args.employees),
		html: bulkPresentBtnHtml(args.employees),
	})
);
