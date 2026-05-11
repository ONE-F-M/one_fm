<template>
	<aside class="rp-pool">
		<div class="rp-pool-header">
			<div class="rp-pool-title">Unassigned Shipments</div>
			<div class="rp-pool-count">{{ store.filteredPoolCards.length }} cards</div>
		</div>
		<div class="rp-pool-search">
			<FormControl
				type="text"
				placeholder="Search shift, site, accommodation..."
				size="sm"
				variant="subtle"
				v-model="store.searchQuery"
			/>
		</div>
		<div class="rp-pool-groups">
			<div v-for="group in store.poolGroups" :key="group.acc" class="rp-pool-group">
				<div class="rp-group-header" @click="store.collapsedGroups[group.acc] = !store.collapsedGroups[group.acc]">
					<span class="rp-group-label">{{ group.acc }}</span>
					<span class="rp-group-count">{{ group.cards.length }}</span>
					<span class="rp-group-chevron">{{ store.collapsedGroups[group.acc] ? '▸' : '▾' }}</span>
				</div>
				<div v-show="!store.collapsedGroups[group.acc]" class="rp-group-cards">
					<ShipmentCard
						v-for="card in group.cards"
						:key="card.id"
						:card="card"
					/>
				</div>
			</div>
			<!-- Empty state -->
			<div v-if="store.poolGroups.length === 0" class="rp-pool-empty">
				<div v-if="store.assignedCards.size > 0 && store.filteredPoolCards.length === 0">✓ All cards assigned</div>
				<div v-else>No cards match your search</div>
			</div>
		</div>
	</aside>
</template>

<script setup>
import { usePlannerStore } from "@/stores/plannerStore";
import ShipmentCard from "@/components/ShipmentCard.vue";

const store = usePlannerStore();
</script>

<style scoped>
.rp-pool {
	display: flex;
	flex-direction: column;
	height: 100%;
	overflow: hidden;
	background: var(--bg-color, #fff);
}

.dark .rp-pool {
	background: #1f2937;
}

.rp-pool-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 10px 12px;
	border-bottom: 1px solid var(--border-color, #e2e2e2);
}

.dark .rp-pool-header {
	border-color: #374151;
}

.rp-pool-title {
	font-size: 13px;
	font-weight: 600;
	color: var(--text-color, #333);
}

.dark .rp-pool-title {
	color: #e5e7eb;
}

.rp-pool-count {
	font-size: 11px;
	color: var(--text-muted, #999);
}

.rp-pool-search {
	padding: 8px 12px;
	border-bottom: 1px solid var(--border-color, #e2e2e2);
}

.dark .rp-pool-search {
	border-color: #374151;
}

.rp-pool-groups {
	flex: 1;
	overflow-y: auto;
	padding: 4px;
}

.rp-group-header {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 6px 8px;
	cursor: pointer;
	border-radius: 6px;
	font-size: 12px;
	color: var(--text-color, #444);
	user-select: none;
}

.rp-group-header:hover {
	background: var(--bg-light-gray, #f5f5f5);
}

.dark .rp-group-header {
	color: #d1d5db;
}

.dark .rp-group-header:hover {
	background: #374151;
}

.rp-group-label {
	font-weight: 600;
	flex: 1;
}

.rp-group-count {
	background: var(--bg-light-gray, #f0f0f0);
	padding: 1px 6px;
	border-radius: 10px;
	font-size: 10px;
	font-weight: 600;
}

.dark .rp-group-count {
	background: #374151;
	color: #9ca3af;
}

.rp-group-chevron {
	color: var(--text-muted, #999);
	font-size: 10px;
}

.rp-group-cards {
	padding: 0 4px 4px;
}

.rp-pool-empty {
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 40px 16px;
	color: var(--text-muted, #999);
	font-size: 13px;
}
</style>
