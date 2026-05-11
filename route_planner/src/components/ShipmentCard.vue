<template>
	<div
		:class="['rp-card', isSelected ? 'rp-card-selected' : '']"
		draggable="true"
		@dragstart="onDragStart"
		@dragend="onDragEnd"
		@click="onTap"
	>
		<div class="rp-card-top">
			<span class="rp-card-site">{{ card.site_location }}</span>
			<span :class="['rp-card-type', card.type === 'OLM' ? 'rp-tag-olm' : 'rp-tag-osm']">
				{{ card.type }}
			</span>
		</div>
		<div v-if="assignLabel" class="rp-card-assign-label">
			<span class="rp-assign-badge">{{ assignLabel }} — drag to assign other direction</span>
		</div>
		<div class="rp-card-shift">{{ card.shift_name }}</div>
		<div class="rp-card-meta">
			<span class="rp-card-meta-item">👥 {{ card.headcount }} employees</span>
			<span class="rp-card-meta-item">📍 {{ card.stop_location }}</span>
		</div>
		<div class="rp-card-windows">
			<div class="rp-window rp-window-out">
				<span class="rp-window-label">SHIFT START</span>
				<span class="rp-window-time">{{ fmtISO(card.shift_start) }}</span>
			</div>
			<div class="rp-window rp-window-ret">
				<span class="rp-window-label">SHIFT END</span>
				<span class="rp-window-time">{{ fmtISO(card.shift_end) }}</span>
			</div>
		</div>
		<div class="rp-card-employees">
			<span v-for="e in card.employees.slice(0, 3)" :key="e" class="rp-emp-chip">{{ e }}</span>
			<span v-if="card.employees.length > 3" class="rp-emp-chip rp-emp-more">
				+{{ card.employees.length - 3 }} more
			</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { usePlannerStore } from "@/stores/plannerStore";

const props = defineProps({
	card: { type: Object, required: true },
});

const store = usePlannerStore();

const isSelected = computed(() => {
	return store.selectedPoolCard && store.selectedPoolCard.id === props.card.id;
});

const assignLabel = computed(() => store.cardAssignmentLabel(props.card.id));

function fmtISO(iso) {
	if (!iso) return "—";
	return new Date(iso).toLocaleTimeString("en-GB", {
		hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kuwait"
	});
}

function onDragStart(e) {
	store.draggingCard = props.card;
	e.dataTransfer.effectAllowed = "move";
	e.dataTransfer.setData("text/plain", props.card.id);
}

function onDragEnd() {
	setTimeout(() => { store.draggingCard = null; }, 150);
}

function onTap() {
	const isMobile = "ontouchstart" in window || navigator.maxTouchPoints > 0;
	if (!isMobile) return;
	if (store.selectedPoolCard && store.selectedPoolCard.id === props.card.id) {
		store.selectedPoolCard = null;
	} else {
		store.selectedPoolCard = props.card;
		frappe.show_alert({
			message: `Selected: ${props.card.site_location} — tap a vehicle lane to assign`,
			indicator: "orange"
		}, 3);
	}
}
</script>

<style scoped>
.rp-card {
	background: var(--bg-color, #fff);
	border: 1px solid var(--border-color, #e2e2e2);
	border-radius: 8px;
	padding: 8px 10px;
	margin-bottom: 6px;
	cursor: grab;
	transition: box-shadow 0.15s, border-color 0.15s;
}

.dark .rp-card {
	background: #1f2937;
	border-color: #374151;
}

.rp-card:hover {
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	border-color: #3b82f6;
}

.rp-card-selected {
	border-color: #f97316 !important;
	box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.2);
}

.rp-card-top {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 4px;
}

.rp-card-site {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-color, #333);
}

.dark .rp-card-site {
	color: #e5e7eb;
}

.rp-card-type {
	font-size: 9px;
	font-weight: 700;
	padding: 1px 6px;
	border-radius: 10px;
	text-transform: uppercase;
}

.rp-tag-olm { background: #e3f2fd; color: #1565c0; }
.rp-tag-osm { background: #fff3e0; color: #e65100; }

.dark .rp-tag-olm { background: #1e3a5f; color: #93c5fd; }
.dark .rp-tag-osm { background: #4a2500; color: #fdba74; }

.rp-card-assign-label {
	margin-bottom: 4px;
}

.rp-assign-badge {
	font-size: 10px;
	font-weight: 600;
	padding: 2px 8px;
	border-radius: 10px;
	background: #e8f5e9;
	color: #2e7d32;
}

.dark .rp-assign-badge {
	background: #14532d;
	color: #86efac;
}

.rp-card-shift {
	font-size: 11px;
	color: var(--text-muted, #777);
	margin-bottom: 4px;
}

.rp-card-meta {
	display: flex;
	gap: 10px;
	font-size: 10px;
	color: var(--text-muted, #888);
	margin-bottom: 6px;
}

.rp-card-windows {
	display: flex;
	gap: 6px;
	margin-bottom: 6px;
}

.rp-window {
	flex: 1;
	padding: 4px 6px;
	border-radius: 4px;
	font-size: 10px;
}

.rp-window-out {
	background: #e3f2fd;
}

.rp-window-ret {
	background: #fff3e0;
}

.dark .rp-window-out { background: #1e3a5f; }
.dark .rp-window-ret { background: #4a2500; }

.rp-window-label {
	display: block;
	font-size: 8px;
	font-weight: 600;
	text-transform: uppercase;
	color: var(--text-muted, #999);
	margin-bottom: 1px;
}

.rp-window-time {
	font-weight: 600;
	color: var(--text-color, #333);
}

.dark .rp-window-time {
	color: #e5e7eb;
}

.rp-card-employees {
	display: flex;
	flex-wrap: wrap;
	gap: 3px;
}

.rp-emp-chip {
	font-size: 9px;
	padding: 1px 6px;
	border-radius: 10px;
	background: var(--bg-light-gray, #f3f3f3);
	color: var(--text-muted, #666);
}

.dark .rp-emp-chip {
	background: #374151;
	color: #9ca3af;
}

.rp-emp-more {
	font-weight: 600;
}
</style>
