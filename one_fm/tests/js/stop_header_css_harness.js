// Parses the SHIPPED stylesheet and returns one rule's declarations, so the tests assert
// the properties that prevent the overflow rather than the text someone wrote.
const fs = require("fs");
const [, , canvasPath, payload] = process.argv;
const { selectors } = JSON.parse(payload);

const src = fs.readFileSync(canvasPath, "utf8");
const out = {};

for (const selector of selectors) {
	// Only the rule whose whole selector is this one - not ".x:active .y {...}", whose
	// declarations do not apply on their own. Last definition wins, as in the browser.
	const re = new RegExp("(?:^|\\n)\\s*" + selector.replace(".", "\\.") + "\\s*\\{([^}]*)\\}", "g");
	let match, body = null;
	while ((match = re.exec(src)) !== null) body = match[1];
	if (body === null) { out[selector] = null; continue; }
	const decls = {};
	for (const part of body.split(";")) {
		const i = part.indexOf(":");
		if (i === -1) continue;
		decls[part.slice(0, i).trim()] = part.slice(i + 1).trim();
	}
	out[selector] = decls;
}
process.stdout.write(JSON.stringify(out));
