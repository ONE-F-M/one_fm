<template>
	<div class="rp-timeline" ref="timelineEl">
		<!-- Toolbar -->
		<div class="rp-toolbar">
			<div class="rp-zoom-controls">
				<Button variant="subtle" size="sm" @click="tl.zoomIn()">+</Button>
				<Button variant="subtle" size="sm" @click="tl.zoomOut()">−</Button>
				<Button variant="subtle" size="sm" @click="tl.fitAll()">⊝ Fit</Button>
			</div>
			<div class="rp-hint">Drag cards to lanes · Drag blocks to reposition · Scroll to pan · Ctrl+Scroll to zoom</div>
			<div class="rp-legend">
				<span class="rp-legend-item rp-legend-out">Outbound</span>
				<span class="rp-legend-item rp-legend-ret">Return</span>
				<span class="rp-legend-item rp-legend-conflict">Conflict</span>
				<span class="rp-legend-item rp-legend-overcap">Overcapacity</span>
			</div>
		</div>

		<!-- Grid -->
		<div class="rp-grid">
			<!-- Sticky axis -->
			<div class="rp-axis-row">
				<div class="rp-lane-label rp-label-stub"></div>
				<div class="rp-axis-wrap" ref="axisWrap">
					<svg :width="tl.svgWidth.value" height="44" style="display:block;overflow:visible">
						<line v-for="tick in tl.axisTicks.value" :key="'tl'+tick.key"
							:x1="tick.x" :x2="tick.x" :y1="tick.isMajor ? 20 : 32" y2="44"
							:stroke="tick.isMajor ? '#aaa' : '#e0e0e0'" stroke-width="1"/>
						<text v-for="tick in tl.axisTicks.value.filter(t => t.label)" :key="'lb'+tick.key"
							:x="tick.x" y="16" text-anchor="middle"
							:font-weight="tick.isMajor ? '600' : '400'"
							:fill="tick.isMajor ? '#444' : '#aaa'"
							font-size="11" font-family="Inter, sans-serif">
							{{ tick.label }}
						</text>
					</svg>
				</div>
			</div>

			<!-- Vehicle lanes -->
			<div class="rp-lanes-area">
				<div v-for="(vehicle, vi) in store.vehicles" :key="vehicle.id"
					:class="['rp-lane-row', vi % 2 === 1 ? 'rp-lane-alt' : '']"
					:data-vehicle-id="vehicle.id">
					<div class="rp-lane-label">
						<div class="rp-gv-plate">{{ vehicle.label }}</div>
						<div class="rp-gv-meta">{{ vehicle.driver }} · {{ vehicle.seats }} seats</div>
						<div class="rp-gv-acc">{{ vehicle.accommodation }}</div>
					</div>
					<div class="rp-lane-svg-wrap"
						@dragover.prevent="$event.dataTransfer.dropEffect='move'"
						@drop.prevent="onLaneDrop($event, vehicle)"
						@click="onLaneTap($event, vehicle)">
						<svg :width="tl.svgWidth.value" :height="tl.rowHeight.value"
							class="rp-lane-svg"
							@wheel.prevent="(e) => tl.onWheel(e, e.currentTarget)"
							@click.self="store.selectedItem = null">
							<!-- Grid lines -->
							<line v-for="tick in tl.axisTicks.value" :key="'g'+tick.key"
								:x1="tick.x" :x2="tick.x" y1="0" :y2="tl.rowHeight.value"
								:stroke="tick.isMajor ? '#ebebeb' : '#f6f6f6'" stroke-width="1"/>
							<!-- Drop highlight -->
							<rect v-if="store.draggingCard" x="0" y="0"
								:width="tl.svgWidth.value" :height="tl.rowHeight.value"
								fill="rgba(249,115,22,0.04)" stroke="#f97316"
								stroke-width="1.5" stroke-dasharray="6,4"/>
							<!-- Swim blocks -->
							<template v-for="entry in store.mergedItemsByVehicle[vehicle.id]"
								:key="entry.type==='merged' ? 'trip_'+entry.tripId : entry.item.id">
								<SwimBlock v-if="entry.type==='single'"
									:item="entry.item" :timeline="tl" />
								<MergedBlock v-else :entry="entry" :timeline="tl" />
							</template>
						</svg>
					</div>
				</div>
				<div v-if="store.vehicles.length === 0" class="rp-empty-state">
					No vehicles available for today
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import { usePlannerStore } from "@/stores/plannerStore";
import { useTimeline } from "@/composables/useTimeline";
import SwimBlock from "@/components/SwimBlock.vue";
import MergedBlock from "@/components/MergedBlock.vue";

const store = usePlannerStore();
const tl = useTimeline();
const axisWrap = ref(null);
const timelineEl = ref(null);
let ro = null;

function updateWidth() {
	if (axisWrap.value && axisWrap.value.clientWidth > 0) {
		tl.svgWidth.value = axisWrap.value.clientWidth;
	}
}

// Init timeline when data loads
watch(() => store.globalStart, (val) => {
	if (val && store.globalEnd) {
		tl.init(val, store.globalEnd);
	}
});

onMounted(() => {
	updateWidth();
	ro = new ResizeObserver(updateWidth);
	if (axisWrap.value) ro.observe(axisWrap.value);
});

onBeforeUnmount(() => { if (ro) ro.disconnect(); });

function onLaneDrop(e, vehicle) {
	const card = store.draggingCard;
	store.draggingCard = null;
	if (!card) return;
	handleDrop(card, vehicle);
}

function onLaneTap(e, vehicle) {
	if (!store.selectedPoolCard) return;
	handleDrop(store.selectedPoolCard, vehicle);
}

function handleDrop(card, vehicle) {
	const peakLoad = store.peakLoadDuringCardWindows(card, vehicle.id);
	if (peakLoad + card.headcount > vehicle.seats) {
		frappe.show_alert({
			message: `Not enough seats — ${vehicle.seats - peakLoad} available on ${vehicle.label}`,
			indicator: "red"
		});
		return;
	}

	// Trip chaining detection
	const PROXIMITY_MS = 2 * 60 * 60 * 1000;
	const cardOutStart = new Date(card.outbound_window_start).getTime();
	const cardOutEnd = new Date(card.outbound_window_end).getTime();
	const nearbyOutbound = store.swimItems.filter(i => {
		if (i.vehicleId !== vehicle.id || i.direction !== "OUTBOUND") return false;
		const existingCard = store.shipmentCards.find(c => c.id === i.cardId);
		if (!existingCard || existingCard.accommodation !== card.accommodation) return false;
		const bE = new Date(i.end).getTime(), bS = new Date(i.start).getTime();
		return bE > (cardOutStart - PROXIMITY_MS) && bS < (cardOutEnd + PROXIMITY_MS);
	});

	if (nearbyOutbound.length > 0) {
		const existingSites = nearbyOutbound.map(i => {
			const c = store.shipmentCards.find(sc => sc.id === i.cardId);
			return c ? c.site_location : i.cardId;
		});
		frappe.confirm(
			`<strong>${vehicle.label}</strong> already picks up from <strong>${card.accommodation}</strong>.<br><br>` +
			existingSites.map((s, i) => `&nbsp;&nbsp;${i+1}. ${s}`).join("<br>") +
			`<br><br>Add <strong>${card.site_location}</strong> as next stop?`,
			() => setTimeout(() => store.chainToTrip(card, nearbyOutbound, vehicle.id), 300),
			() => showPlaceDialog(card, vehicle.id)
		);
		return;
	}

	showPlaceDialog(card, vehicle.id);
}

function showPlaceDialog(card, vehicleId) {
	const placed = store.placedDirections(card.id);
	if (placed.has("OUTBOUND") && !placed.has("RETURN")) {
		quickPlaceDialog(card, vehicleId, "Return", false, true);
		return;
	}
	if (placed.has("RETURN") && !placed.has("OUTBOUND")) {
		quickPlaceDialog(card, vehicleId, "Outbound", true, false);
		return;
	}
	const d = new frappe.ui.Dialog({
		title: `Assign — ${card.site_location}`,
		fields: [
			{ fieldtype: "HTML", options: `<p style="margin:0 0 12px;color:#555;font-size:13px"><strong>${card.shift_name}</strong><br>${card.headcount} employee(s)</p>` },
			{ fieldtype: "Select", fieldname: "direction", label: "Trip Direction", reqd: 1,
				options: "Both (Outbound + Return)\nOutbound Only (→ To Site)\nReturn Only (← From Site)",
				default: "Both (Outbound + Return)" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Int", fieldname: "duration_min", label: "Trip Duration (minutes)", default: 60, reqd: 1 }
		],
		primary_action_label: "Place on Timeline",
		primary_action(vals) {
			d.hide();
			const durMs = (vals.duration_min || 60) * 60000;
			const ch = vals.direction;
			store.doPlace(card, vehicleId, durMs, ch.startsWith("Both") || ch.startsWith("Outbound"), ch.startsWith("Both") || ch.startsWith("Return"));
		}
	});
	d.show();
}

function quickPlaceDialog(card, vehicleId, dirLabel, placeOut, placeRet) {
	const d = new frappe.ui.Dialog({
		title: `Assign ${dirLabel} — ${card.site_location}`,
		fields: [
			{ fieldtype: "Int", fieldname: "duration_min", label: `${dirLabel} Duration (minutes)`, default: 60, reqd: 1 }
		],
		primary_action_label: `Place ${dirLabel}`,
		primary_action(vals) { d.hide(); store.doPlace(card, vehicleId, (vals.duration_min || 60) * 60000, placeOut, placeRet); }
	});
	d.show();
}
</script>

<style scoped>
.rp-timeline { display: flex; flex-direction: column; height: 100%; background: var(--bg-color, #fafafa); }
.dark .rp-timeline { background: #111827; }
.rp-toolbar { display: flex; align-items: center; gap: 12px; padding: 6px 12px; border-bottom: 1px solid var(--border-color, #e2e2e2); flex-wrap: wrap; }
.dark .rp-toolbar { border-color: #374151; }
.rp-zoom-controls { display: flex; gap: 4px; }
.rp-hint { font-size: 11px; color: var(--text-muted, #999); flex: 1; }
.rp-legend { display: flex; gap: 8px; font-size: 10px; }
.rp-legend-item { padding: 2px 8px; border-radius: 10px; font-weight: 600; }
.rp-legend-out { background: #e3f2fd; color: #1565c0; }
.rp-legend-ret { background: #fff3e0; color: #e65100; }
.rp-legend-conflict { background: #ffebee; color: #c62828; }
.rp-legend-overcap { background: #f3e5f5; color: #7b1fa2; }
.rp-grid { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.rp-axis-row { display: flex; border-bottom: 1px solid var(--border-color, #ddd); position: sticky; top: 0; z-index: 5; background: var(--bg-color, #fff); }
.dark .rp-axis-row { background: #1f2937; border-color: #374151; }
.rp-axis-wrap { flex: 1; overflow: hidden; }
.rp-lanes-area { flex: 1; overflow-y: auto; }
.rp-lane-row { display: flex; border-bottom: 1px solid var(--border-color, #eee); min-height: 100px; }
.dark .rp-lane-row { border-color: #1f2937; }
.rp-lane-alt { background: rgba(0,0,0,0.015); }
.dark .rp-lane-alt { background: rgba(255,255,255,0.02); }
.rp-lane-label { width: 140px; flex-shrink: 0; padding: 8px 10px; border-right: 1px solid var(--border-color, #eee); display: flex; flex-direction: column; justify-content: center; gap: 2px; }
.dark .rp-lane-label { border-color: #374151; }
.rp-label-stub { min-height: 44px; }
.rp-gv-plate { font-size: 12px; font-weight: 700; color: var(--text-color, #333); }
.dark .rp-gv-plate { color: #e5e7eb; }
.rp-gv-meta { font-size: 10px; color: var(--text-muted, #888); }
.rp-gv-acc { font-size: 10px; color: var(--text-muted, #aaa); }
.rp-lane-svg-wrap { flex: 1; overflow: hidden; cursor: crosshair; }
.rp-lane-svg { display: block; }
.rp-empty-state { padding: 40px; text-align: center; color: var(--text-muted, #999); font-size: 14px; }

@media (max-width: 767px) {
	.rp-toolbar { padding: 4px 8px; gap: 6px; }
	.rp-hint { display: none; }
	.rp-legend { display: none; }
	.rp-lane-label { width: 70px; padding: 4px 6px; }
	.rp-label-stub { width: 70px; min-height: 36px; }
	.rp-gv-plate { font-size: 10px; }
	.rp-gv-meta { font-size: 8px; }
	.rp-gv-acc { display: none; }
	.rp-lane-row { min-height: 70px; }
}
</style>
