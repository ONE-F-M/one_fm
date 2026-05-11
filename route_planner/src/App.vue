<template>
	<div class="rp-root bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
		<PlannerPage />
	</div>
</template>

<script setup>
import PlannerPage from "@/pages/PlannerPage.vue";
</script>

<style scoped>
.rp-root {
	height: 100%;
	min-height: calc(100vh - 60px); /* Account for Frappe navbar */
	display: flex;
	flex-direction: column;
}
</style>
