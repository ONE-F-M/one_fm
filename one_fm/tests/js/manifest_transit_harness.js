// Runs the SHIPPED calcTransit from transportation_manifest_page.js.
// The point is to execute the leg rule rather than assert on its source text: which
// stop carries a leg is exactly the kind of off-by-one a grep cannot see.

function secondsOfDay(value) {
		if (!value) return null;
		const d = new Date(value);
		if (isNaN(d)) return null;
		const [h, m, sec] = d.toLocaleTimeString("en-GB", {
			hour: "2-digit", minute: "2-digit", second: "2-digit",
			hour12: false, timeZone: "Asia/Kuwait"
		}).split(":").map(Number);
		return h * 3600 + m * 60 + sec;
	}
function calcTransit(t1, t2, stop) {
				const zero = { travelDuration: "0s", waitDuration: "0s", travelDistanceMeters: 0 };

				// AC3: the clock gap, read as time of day and wrapped at midnight. Taking
				// the raw difference meant two stops whose timestamps carried different
				// lock dates reported a drive of roughly a day, which fmtDuration then
				// clamped to a flat "24h" - the overflow fallback the AC names.
				const from = secondsOfDay(t1), to = secondsOfDay(t2);
				let gap = (from === null || to === null) ? null : to - from;
				if (gap !== null && gap < 0) gap += 24 * 3600;   // the leg ran past midnight

				// A drop-off and the pick-up that follows it at the same place and minute
				// are ONE physical stop printed twice. Nothing is driven between them, so
				// the minutes belonging to the leg out of that stop must not be drawn in
				// the gap - they belong further down, against the stop the bus leaves for.
				if (gap === 0) return zero;

				const transit = (stop && (stop.transitMinutes ?? stop.transit_minutes)) || 0;
				const buffer = (stop && (stop.bufferMinutes ?? stop.buffer_minutes)) || 0;
				if (transit || buffer) {
					return {
						travelDuration: transit * 60 + "s",
						waitDuration: buffer * 60 + "s",
						travelDistanceMeters: 0
					};
				}
				// A leg with no minutes of its own is measured by the clock alone.
				if (gap === null || gap <= 0) return zero;
				return { travelDuration: gap + "s", waitDuration: "0s", travelDistanceMeters: 0 };
			}

const mins = (t) => ({
    drive: Math.round(parseInt(t.travelDuration) / 60),
    buffer: Math.round(parseInt(t.waitDuration) / 60),
});
const args = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(mins(calcTransit(args.from, args.to, args.stop || null))));

