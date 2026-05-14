<template>
	<g class="rp-block-grab" @click.stop="onClick">
		<!-- Shadow -->
		<rect :x="x + 1" :y="y + 2" :width="w" :height="h" fill="rgba(0,0,0,0.10)" rx="5"/>
		<!-- Body -->
		<rect :x="x" :y="y" :width="w" :height="h"
			:fill="entry.conflict ? '#c62828' : (entry.direction === 'OUTBOUND' ? '#1565c0' : '#e65100')"
			:stroke="isAnySelected ? '#f97316' : 'transparent'"
			stroke-width="2.5" rx="5"/>
		<!-- Direction -->
		<text v-if="w >= 18" :x="x + 6" :y="y + 14"
			fill="rgba(255,255,255,0.9)" font-size="10" font-weight="700"
			dominant-baseline="middle" style="user-select:none;pointer-events:none">
			{{ entry.direction === 'OUTBOUND' ? '→ To' : '← From' }}
		</text>
		<!-- Stop labels -->
		<template v-for="(label, si) in entry.stopLabels" :key="'sl'+si">
			<text v-if="w >= 40 && (y + 28 + si * 13) < (y + h - 16)"
				:x="x + 6" :y="y + 27 + si * 13"
				fill="white" font-size="10" font-weight="600"
				dominant-baseline="middle"
				style="user-select:none;pointer-events:none">
				{{ entry.stopLabels.length > 1 ? '- ' : '' }}{{ label }}
			</text>
		</template>
		<!-- Time + headcount -->
		<text v-if="w >= 60 && h >= 34" :x="x + 6" :y="y + h - 6"
			fill="rgba(255,255,255,0.7)" font-size="9"
			dominant-baseline="middle" style="user-select:none;pointer-events:none">
			{{ tl.fmtTime(entry.start) }}-{{ tl.fmtTime(entry.end) }} · 👥{{ entry.headcount }}
		</text>
	</g>
</template>

<script setup>
import { computed } from "vue";
import { usePlannerStore } from "@/stores/plannerStore";

const props = defineProps({
	entry: { type: Object, required: true },
	timeline: { type: Object, required: true },
});

const store = usePlannerStore();
const tl = props.timeline;

const x = computed(() => tl.timeToX(props.entry.start));
const y = computed(() => {
	const pad = 4, cols = props.entry._totalCols || 1, col = props.entry._col || 0;
	const usable = tl.rowHeight.value - pad * 2;
	return pad + col * (usable / cols);
});
const w = computed(() => Math.max(8, tl.timeToX(props.entry.end) - tl.timeToX(props.entry.start)));
const h = computed(() => {
	const pad = 4, cols = props.entry._totalCols || 1;
	return (tl.rowHeight.value - pad * 2) / cols - 2;
});
const isAnySelected = computed(() => {
	return store.selectedItem && props.entry.stops.some(s => s.id === store.selectedItem.id);
});

function onClick() {
	store.selectedItem = props.entry.primaryItem;
}
</script>
