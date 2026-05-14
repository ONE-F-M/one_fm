<template>
	<div class="rp-root">
		<!-- Header -->
		<PlanHeader />

		<!-- Body: Card Pool + Timeline + Detail Panel -->
		<div class="rp-body">
			<!-- Left: Card Pool (slide drawer on mobile) -->
			<transition name="rp-slide-left">
				<aside v-if="showPool" class="rp-sidebar rp-sidebar-left">
					<CardPool />
				</aside>
			</transition>

			<!-- Center: Timeline Lanes -->
			<div class="rp-center">
				<TimelineGrid />
			</div>

			<!-- Right: Detail Panel (slide drawer on mobile) -->
			<transition name="rp-slide-right">
				<aside v-if="plannerStore.selectedItem && showDetail"
					class="rp-sidebar rp-sidebar-right">
					<DetailPanel />
				</aside>
			</transition>
		</div>

		<!-- Mobile backdrop -->
		<div v-if="isMobileDrawerOpen" class="rp-backdrop" @click="closeMobileDrawers" />

		<!-- Mobile floating action buttons -->
		<div class="rp-mobile-fab">
			<button class="rp-fab-btn rp-fab-pool" :class="{ active: showPool }"
				@click="togglePool">
				📋 <span class="rp-fab-label">Cards</span>
			</button>
			<button v-if="plannerStore.selectedItem"
				class="rp-fab-btn rp-fab-detail" :class="{ active: showDetail }"
				@click="toggleDetail">
				📝 <span class="rp-fab-label">Details</span>
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { usePlannerStore } from "@/stores/plannerStore";
import PlanHeader from "@/components/PlanHeader.vue";
import CardPool from "@/components/CardPool.vue";
import TimelineGrid from "@/components/TimelineGrid.vue";
import DetailPanel from "@/components/DetailPanel.vue";

const plannerStore = usePlannerStore();

const showPool = ref(true);
const showDetail = ref(true);
const isMobile = ref(false);

function checkMobile() {
	isMobile.value = window.innerWidth < 768;
	if (isMobile.value) {
		showPool.value = false;
		showDetail.value = false;
	} else {
		showPool.value = true;
		showDetail.value = true;
	}
}

const isMobileDrawerOpen = computed(() => {
	return isMobile.value && (showPool.value || showDetail.value);
});

function togglePool() {
	if (isMobile.value) {
		showDetail.value = false;
		showPool.value = !showPool.value;
	} else {
		showPool.value = !showPool.value;
	}
}

function toggleDetail() {
	if (isMobile.value) {
		showPool.value = false;
		showDetail.value = !showDetail.value;
	} else {
		showDetail.value = !showDetail.value;
	}
}

function closeMobileDrawers() {
	showPool.value = false;
	showDetail.value = false;
}

onMounted(() => {
	checkMobile();
	window.addEventListener("resize", checkMobile);
	plannerStore.fetchData();
});

onUnmounted(() => {
	window.removeEventListener("resize", checkMobile);
});
</script>

<style scoped>
/* Root */
.rp-root {
	display: flex;
	flex-direction: column;
	height: 100%;
	overflow: hidden;
	position: relative;
}

/* Body */
.rp-body {
	display: flex;
	flex: 1;
	overflow: hidden;
	position: relative;
}

/* Center timeline */
.rp-center {
	flex: 1;
	overflow: hidden;
	min-width: 0;
}

/* Sidebars (desktop: inline, mobile: overlay drawers) */
.rp-sidebar {
	flex-shrink: 0;
	overflow: hidden;
	border-color: var(--border-color, #e2e2e2);
}

.rp-sidebar-left {
	width: 288px;
	border-right: 1px solid var(--border-color, #e2e2e2);
}

.rp-sidebar-right {
	width: 320px;
	border-left: 1px solid var(--border-color, #e2e2e2);
}

/* Mobile FAB - hidden on desktop */
.rp-mobile-fab {
	display: none;
}

/* Mobile backdrop */
.rp-backdrop {
	display: none;
}

/* ── Transitions ── */
.rp-slide-left-enter-active,
.rp-slide-left-leave-active,
.rp-slide-right-enter-active,
.rp-slide-right-leave-active {
	transition: transform 0.25s ease, opacity 0.25s ease;
}

.rp-slide-left-enter-from,
.rp-slide-left-leave-to {
	transform: translateX(-100%);
	opacity: 0;
}

.rp-slide-right-enter-from,
.rp-slide-right-leave-to {
	transform: translateX(100%);
	opacity: 0;
}

/* ══════════════════ MOBILE ══════════════════ */
@media (max-width: 767px) {
	/* Sidebars become full-height overlay drawers */
	.rp-sidebar {
		position: absolute;
		top: 0;
		bottom: 0;
		z-index: 50;
		background: var(--bg-color, #fff);
		box-shadow: 4px 0 24px rgba(0,0,0,0.15);
	}

	.rp-sidebar-left {
		left: 0;
		width: 85vw;
		max-width: 320px;
	}

	.rp-sidebar-right {
		right: 0;
		width: 85vw;
		max-width: 340px;
	}

	/* Backdrop */
	.rp-backdrop {
		display: block;
		position: absolute;
		inset: 0;
		z-index: 40;
		background: rgba(0,0,0,0.4);
	}

	/* FAB buttons at bottom */
	.rp-mobile-fab {
		display: flex;
		position: absolute;
		bottom: 16px;
		left: 50%;
		transform: translateX(-50%);
		gap: 10px;
		z-index: 30;
	}

	.rp-fab-btn {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 10px 16px;
		border-radius: 24px;
		border: none;
		background: #fff;
		box-shadow: 0 2px 12px rgba(0,0,0,0.18);
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
		color: #333;
		transition: background 0.15s, transform 0.1s;
	}

	.rp-fab-btn:active {
		transform: scale(0.95);
	}

	.rp-fab-btn.active {
		background: #1565c0;
		color: #fff;
	}

	.rp-fab-label {
		font-size: 12px;
	}
}

/* ══════════════════ TABLET ══════════════════ */
@media (min-width: 768px) and (max-width: 1023px) {
	.rp-sidebar-left {
		width: 240px;
	}

	.rp-sidebar-right {
		width: 280px;
	}
}
</style>
