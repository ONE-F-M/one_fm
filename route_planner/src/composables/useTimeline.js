import { ref, computed } from "vue";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

dayjs.extend(utc);
dayjs.extend(timezone);

const TZ = "Asia/Kuwait";

/**
 * Composable for timeline time↔pixel conversion, zoom, and pan.
 */
export function useTimeline(opts = {}) {
	const svgWidth = ref(800);
	const rowHeight = ref(100);

	// Plan boundaries (absolute outer limits)
	const planStart = ref(null);
	const planEnd = ref(null);

	// Visible window
	const windowStart = ref(null);
	const windowEnd = ref(null);

	const windowDurationMs = computed(() => {
		if (!windowStart.value || !windowEnd.value) return 1;
		return windowEnd.value.getTime() - windowStart.value.getTime();
	});

	// ── Time ↔ Pixel ──

	function timeToX(t) {
		const ms = new Date(t).getTime() - windowStart.value.getTime();
		return Math.round((ms / windowDurationMs.value) * svgWidth.value);
	}

	function xToTime(x) {
		return new Date(windowStart.value.getTime() + (x / svgWidth.value) * windowDurationMs.value);
	}

	// ── Time formatting ──

	function fmtTime(t) {
		return new Date(t).toLocaleTimeString("en-GB", {
			hour: "2-digit", minute: "2-digit", timeZone: TZ
		});
	}

	function fmtISO(iso) {
		if (!iso) return "—";
		return fmtTime(new Date(iso));
	}

	function durMin(item) {
		return Math.round((new Date(item.end) - new Date(item.start)) / 60000);
	}

	// ── Axis ticks ──

	const axisTicks = computed(() => {
		if (!windowStart.value || !windowEnd.value) return [];
		const durationH = windowDurationMs.value / 3600000;
		let stepMs, labelEvery;
		if (durationH <= 4) {
			stepMs = 15 * 60 * 1000;
			labelEvery = 1;
		} else if (durationH <= 10) {
			stepMs = 30 * 60 * 1000;
			labelEvery = 1;
		} else if (durationH <= 18) {
			stepMs = 30 * 60 * 1000;
			labelEvery = 2;
		} else {
			stepMs = 60 * 60 * 1000;
			labelEvery = 1;
		}

		const origin = new Date(Math.ceil(windowStart.value.getTime() / stepMs) * stepMs);
		const ticks = [];
		let t = new Date(origin);
		let idx = 0;
		while (t <= windowEnd.value) {
			const x = timeToX(t);
			if (x >= -1 && x <= svgWidth.value + 1) {
				const isMajor = t.getMinutes() === 0;
				const showLabel = idx % labelEvery === 0;
				ticks.push({
					key: t.getTime(),
					x,
					isMajor,
					label: showLabel ? fmtTime(t) : null
				});
			}
			t = new Date(t.getTime() + stepMs);
			idx++;
		}
		return ticks;
	});

	// ── Zoom / Pan ──

	function zoomIn() {
		const c = (windowStart.value.getTime() + windowEnd.value.getTime()) / 2;
		const h = windowDurationMs.value * 0.25;
		windowStart.value = new Date(c - h);
		windowEnd.value = new Date(c + h);
	}

	function zoomOut() {
		const c = (windowStart.value.getTime() + windowEnd.value.getTime()) / 2;
		const maxH = (planEnd.value.getTime() - planStart.value.getTime()) / 2;
		const h = Math.min(maxH, windowDurationMs.value * 0.75);
		windowStart.value = new Date(Math.max(planStart.value.getTime(), c - h));
		windowEnd.value = new Date(Math.min(planEnd.value.getTime(), c + h));
	}

	function fitAll() {
		windowStart.value = new Date(planStart.value);
		windowEnd.value = new Date(planEnd.value);
	}

	function onWheel(e, svgEl) {
		e.preventDefault();
		if (e.ctrlKey || e.metaKey) {
			// Zoom to cursor position
			const rect = svgEl.getBoundingClientRect();
			const x = Math.max(0, Math.min(svgWidth.value, e.clientX - rect.left));
			const pivot = xToTime(x);
			const factor = e.deltaY > 0 ? 1.4 : 0.714;
			const minDur = 30 * 60 * 1000;
			const maxDur = planEnd.value.getTime() - planStart.value.getTime();
			const newDur = Math.min(maxDur, Math.max(minDur, windowDurationMs.value * factor));
			const ratio = x / svgWidth.value;
			const newS = pivot.getTime() - ratio * newDur;
			windowStart.value = new Date(Math.max(planStart.value.getTime(), newS));
			windowEnd.value = new Date(Math.min(planEnd.value.getTime(), windowStart.value.getTime() + newDur));
		} else {
			// Pan
			const delta = (e.deltaX || e.deltaY) / svgWidth.value * windowDurationMs.value;
			const newS = windowStart.value.getTime() + delta;
			const newE = windowEnd.value.getTime() + delta;
			if (newS >= planStart.value.getTime() && newE <= planEnd.value.getTime()) {
				windowStart.value = new Date(newS);
				windowEnd.value = new Date(newE);
			}
		}
	}

	// ── Initialize from server data ──

	function init(globalStart, globalEnd) {
		const pS = new Date(globalStart);
		const pE = new Date(globalEnd);
		planStart.value = pS;
		planEnd.value = pE;

		// Smart initial zoom: show working-hours window
		const h03utc = new Date(pS.getTime() + (6 * 3600000));
		const h17utc = new Date(h03utc.getTime() + (14 * 3600000));
		const initStart = new Date(Math.max(pS.getTime(), h03utc.getTime() - 3600000));
		const initEnd = new Date(Math.min(pE.getTime(), h17utc.getTime() + 3600000));
		windowStart.value = initStart;
		windowEnd.value = initEnd;
	}

	// ── SVG block position helpers ──

	function bx(item) { return timeToX(item.start); }
	function bw(item) { return Math.max(8, timeToX(item.end) - timeToX(item.start)); }
	function by(item) {
		const pad = 4;
		const cols = item._totalCols || 1;
		const col = item._col || 0;
		const usable = rowHeight.value - pad * 2;
		return pad + col * (usable / cols);
	}
	function bh(item) {
		const pad = 4;
		const cols = item._totalCols || 1;
		const usable = rowHeight.value - pad * 2;
		return (usable / cols) - 2;
	}
	function bcy(item) { return by(item) + bh(item) / 2; }

	function bfill(item) {
		if (item.conflict) return "#c62828";
		return item.direction === "OUTBOUND" ? "#1565c0" : "#e65100";
	}

	return {
		svgWidth,
		rowHeight,
		planStart,
		planEnd,
		windowStart,
		windowEnd,
		windowDurationMs,

		timeToX,
		xToTime,
		fmtTime,
		fmtISO,
		durMin,
		axisTicks,

		zoomIn,
		zoomOut,
		fitAll,
		onWheel,
		init,

		bx, bw, by, bh, bcy, bfill,
	};
}
