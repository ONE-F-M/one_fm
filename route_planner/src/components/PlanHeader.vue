<template>
	<header class="rp-header">
		<div class="rp-header-left">
			<h1 class="rp-title">Route Planner</h1>
			<div class="rp-plan-controls">
				<select
					:value="store.currentPlan ? store.currentPlan.name : ''"
					@change="store.switchPlan($event.target.value)"
					class="rp-select"
				>
					<option value="" disabled>Select a plan…</option>
					<option v-for="p in store.planList" :key="p.name" :value="p.name">
						{{ p.title }} ({{ p.status }})
					</option>
				</select>
				<Button variant="subtle" size="sm" @click="store.createNewPlan">
					+ New Plan
				</Button>
				<span
					v-if="store.currentPlan"
					class="indicator-pill"
					:class="statusClass"
				>
					{{ store.currentPlan.status }}
				</span>
				<Button
					v-if="store.currentPlan && store.currentPlan.status === 'Draft'"
					variant="solid"
					theme="green"
					size="sm"
					@click="store.togglePlanStatus('Active')"
				>
					✓ Activate
				</Button>
				<Button
					v-if="store.currentPlan && store.currentPlan.status === 'Active'"
					variant="outline"
					theme="orange"
					size="sm"
					@click="store.togglePlanStatus('Draft')"
				>
					↩ Deactivate
				</Button>
				<Button
					v-if="store.currentPlan && (store.currentPlan.status === 'Draft' || store.currentPlan.status === 'Active')"
					variant="ghost"
					size="sm"
					@click="store.togglePlanStatus('Expired')"
				>
					✕ Expire
				</Button>
				<span v-if="store.currentPlan && store.currentPlan.effective_from" class="rp-dates">
					{{ store.currentPlan.effective_from }}{{ store.currentPlan.effective_until ? ' → ' + store.currentPlan.effective_until : ' → ∞' }}
				</span>
				<span v-if="store.planLoading" class="rp-loading-text">Loading…</span>
			</div>
		</div>
		<div class="rp-header-right">
			<Button
				variant="solid"
				size="sm"
				:disabled="!store.currentPlan"
				@click="store.savePlan"
				:title="!store.currentPlan ? 'Create or select a plan first' : ''"
			>
				Save Plan
			</Button>
			<Button
				variant="outline"
				size="sm"
				:disabled="!store.currentPlan"
				@click="store.openManifest()"
			>
				Manifest
			</Button>
			<ThemeToggle />
		</div>
	</header>
</template>

<script setup>
import { computed } from "vue";
import { usePlannerStore } from "@/stores/plannerStore";
import ThemeToggle from "@/components/ThemeToggle.vue";

const store = usePlannerStore();

const statusClass = computed(() => {
	if (!store.currentPlan) return "";
	const s = store.currentPlan.status;
	if (s === "Active") return "green";
	if (s === "Draft") return "orange";
	return "gray";
});
</script>

<style scoped>
.rp-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 8px 16px;
	border-bottom: 1px solid var(--border-color, #e2e2e2);
	background: var(--bg-color, #fff);
	flex-shrink: 0;
	gap: 12px;
	flex-wrap: wrap;
}

.dark .rp-header {
	background: #1f2937;
	border-color: #374151;
}

.rp-header-left {
	display: flex;
	align-items: flex-start;
	flex-direction: column;
	gap: 4px;
}

.rp-title {
	font-size: 16px;
	font-weight: 600;
	margin: 0;
	color: var(--text-color, #333);
}

.dark .rp-title {
	color: #f3f4f6;
}

.rp-plan-controls {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}

.rp-select {
	height: 28px;
	font-size: 12px;
	padding: 0 8px;
	border: 1px solid var(--border-color, #d1d5db);
	border-radius: 6px;
	background: var(--bg-color, #fff);
	color: var(--text-color, #333);
	min-width: 160px;
}

.dark .rp-select {
	background: #374151;
	border-color: #4b5563;
	color: #e5e7eb;
}

.rp-dates {
	font-size: 11px;
	color: var(--text-muted, #999);
}

.rp-loading-text {
	font-size: 11px;
	color: var(--text-muted, #999);
}

.rp-header-right {
	display: flex;
	align-items: center;
	gap: 8px;
}

@media (max-width: 768px) {
	.rp-header {
		flex-direction: column;
		align-items: stretch;
		padding: 6px 10px;
		gap: 6px;
	}
	.rp-title {
		font-size: 14px;
	}
	.rp-plan-controls {
		gap: 6px;
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
		scrollbar-width: none;
		padding-bottom: 2px;
	}
	.rp-plan-controls::-webkit-scrollbar { display: none; }
	.rp-select {
		min-width: 130px;
		font-size: 11px;
		height: 26px;
	}
	.rp-header-right {
		justify-content: flex-end;
	}
	.rp-dates {
		display: none;
	}
}
</style>
