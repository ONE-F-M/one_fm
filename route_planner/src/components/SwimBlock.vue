<template>
	<g :class="store.isDraggingBlock && isSelected ? 'rp-block-grabbing' : 'rp-block-grab'"
		@mousedown.stop="onMouseDown"
		@touchstart.prevent.stop="onTouchStart"
		@click.stop="onClick">
		<!-- Shadow -->
		<rect :x="x + 1" :y="y + 2" :width="w" :height="h" fill="rgba(0,0,0,0.10)" rx="5"/>
		<!-- Body -->
		<rect :x="x" :y="y" :width="w" :height="h"
			:fill="tl.bfill(item)"
			:stroke="isSelected ? '#f97316' : 'transparent'"
			stroke-width="2.5" rx="5"/>
		<!-- Direction label -->
		<text v-if="w >= 18" :x="x + 6" :y="y + Math.min(15, h * 0.3)"
			fill="rgba(255,255,255,0.9)" :font-size="Math.min(10, h * 0.28)"
			font-weight="700" dominant-baseline="middle"
			style="user-select:none;pointer-events:none">
			{{ item.direction === 'OUTBOUND' ? '→ To' : '← From' }}
		</text>
		<!-- Site name -->
		<text v-if="w >= 40 && h >= 30" :x="x + 6" :y="y + h / 2"
			fill="white" :font-size="Math.min(11, h * 0.28)" font-weight="600"
			dominant-baseline="middle"
			:textLength="Math.max(0, w - 14)" lengthAdjust="spacing"
			style="user-select:none;pointer-events:none;overflow:hidden">
			{{ card.site_location }}
		</text>
		<!-- Time + headcount -->
		<text v-if="w >= 60 && h >= 40" :x="x + 6" :y="y + h - Math.min(8, h * 0.15)"
			fill="rgba(255,255,255,0.7)" :font-size="Math.min(9, h * 0.22)"
			dominant-baseline="middle"
			style="user-select:none;pointer-events:none">
			{{ tl.fmtTime(item.start) }}-{{ tl.fmtTime(item.end) }} · 👥{{ item.headcount }}
		</text>
	</g>
</template>

<script setup>
import { computed } from "vue";
import { usePlannerStore } from "@/stores/plannerStore";

const props = defineProps({
	item: { type: Object, required: true },
	timeline: { type: Object, required: true },
});

const store = usePlannerStore();
const tl = props.timeline;

const x = computed(() => tl.bx(props.item));
const y = computed(() => tl.by(props.item));
const w = computed(() => tl.bw(props.item));
const h = computed(() => tl.bh(props.item));
const card = computed(() => store.findCard(props.item.cardId));
const isSelected = computed(() => store.selectedItem && store.selectedItem.id === props.item.id);

function onClick(e) {
	if (store.isDraggingBlock) return;
	store.selectedItem = (store.selectedItem && store.selectedItem.id === props.item.id) ? null : props.item;
}

function onMouseDown(e) {
	const startX = e.clientX, startY = e.clientY;
	const origStart = new Date(props.item.start).getTime();
	const origEnd = new Date(props.item.end).getTime();
	const origVid = props.item.vehicleId;
	let moved = false, targetVid = origVid;

	const onMove = (me) => {
		const dx = me.clientX - startX, dy = me.clientY - startY;
		if (!moved && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) moved = true;
		if (!moved) return;
		store.isDraggingBlock = true;
		const deltaMs = (dx / tl.svgWidth.value) * tl.windowDurationMs.value;
		props.item.start = new Date(origStart + deltaMs);
		props.item.end = new Date(origEnd + deltaMs);
		const el = document.elementFromPoint(me.clientX, me.clientY);
		if (el) {
			const row = el.closest(".rp-lane-row");
			if (row && row.dataset.vehicleId) targetVid = row.dataset.vehicleId;
		}
		store.checkConflicts();
	};

	const onUp = () => {
		document.removeEventListener("mousemove", onMove);
		document.removeEventListener("mouseup", onUp);
		setTimeout(() => { store.isDraggingBlock = false; }, 60);
		if (moved) {
			if (targetVid !== origVid) {
				const tv = store.vehicles.find(v => v.id === targetVid);
				if (tv) {
					props.item.vehicleId = targetVid;
					const pk = store.peakLoadDuringCardWindows(card.value, targetVid);
					if (pk > tv.seats) {
						props.item.vehicleId = origVid;
						props.item.start = new Date(origStart);
						props.item.end = new Date(origEnd);
						frappe.show_alert({ message: `Cannot move — ${tv.label} full`, indicator: "red" }, 4);
					} else {
						frappe.show_alert({ message: `Moved to ${tv.label}`, indicator: "blue" }, 3);
					}
				}
			}
			store.checkConflicts();
			store.canSave = store.assignedCards.size > 0;
			store.persistAssignments();
		}
	};

	document.addEventListener("mousemove", onMove);
	document.addEventListener("mouseup", onUp);
}

function onTouchStart(e) {
	const touch = e.touches[0];
	const startX = touch.clientX;
	const origStart = new Date(props.item.start).getTime();
	const origEnd = new Date(props.item.end).getTime();
	let moved = false;

	const onTouchMove = (te) => {
		te.preventDefault();
		const dx = te.touches[0].clientX - startX;
		if (!moved && Math.abs(dx) > 5) moved = true;
		if (!moved) return;
		store.isDraggingBlock = true;
		const deltaMs = (dx / tl.svgWidth.value) * tl.windowDurationMs.value;
		props.item.start = new Date(origStart + deltaMs);
		props.item.end = new Date(origEnd + deltaMs);
	};

	const onTouchEnd = () => {
		document.removeEventListener("touchmove", onTouchMove);
		document.removeEventListener("touchend", onTouchEnd);
		setTimeout(() => { store.isDraggingBlock = false; }, 60);
		if (moved) { store.checkConflicts(); store.canSave = store.assignedCards.size > 0; store.persistAssignments(); }
	};

	document.addEventListener("touchmove", onTouchMove, { passive: false });
	document.addEventListener("touchend", onTouchEnd);
}
</script>

<style>
.rp-block-grab { cursor: grab; }
.rp-block-grabbing { cursor: grabbing; }
</style>
