<template>
	<div class="manifest-container">
		<div class="manifest-body">
			<div class="manifest-info">
				<div class="manifest-icon">📋</div>
				<h3>Route Manifest</h3>
				<p>The manifest will open in a new browser tab with a print-ready view of all vehicle routes and employee assignments.</p>
				<div class="manifest-stats" v-if="routeCount > 0">
					<span class="manifest-stat">{{ routeCount }} vehicle routes</span>
					<span class="manifest-stat">{{ assignmentCount }} assignments</span>
				</div>
				<div v-else class="manifest-empty">
					No assignments on the timeline yet. Drag cards to vehicle lanes first.
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { usePlannerStore } from "@/stores/plannerStore";

const store = usePlannerStore();

const routeCount = computed(() => {
	const vehiclesUsed = new Set();
	store.swimItems.forEach(i => vehiclesUsed.add(i.vehicleId));
	return vehiclesUsed.size;
});

const assignmentCount = computed(() => store.swimItems.length);

// Auto-open manifest in new tab when dialog mounts
onMounted(() => {
	if (store.swimItems.length > 0) {
		openManifestTab();
	}
});

function openManifestTab() {
	const routeData = buildManifestData();

	if (!routeData.response.routes.length) {
		frappe.show_alert({
			message: "No assigned shipments to generate a manifest from.",
			indicator: "orange"
		});
		return;
	}

	// Fetch the existing HTML template and inject data
	fetch("/assets/one_fm/html/route_manifest_template.html?v=" + Date.now())
		.then(res => {
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return res.text();
		})
		.then(tpl => {
			const safeJson = JSON.stringify(routeData).replace(/<\//g, "<\\/");
			const dataLine = "const ROUTE_DATA = " + safeJson + ";\n";
			const finalHtml = tpl.replace(/(<body>[\s\S]*?<script>)/, "$1\n" + dataLine);
			const blob = new Blob([finalHtml], { type: "text/html" });
			const url = URL.createObjectURL(blob);
			window.open(url, "_blank");
			setTimeout(() => URL.revokeObjectURL(url), 60000);

			frappe.show_alert({
				message: `Manifest opened — ${routeData.response.routes.length} vehicles`,
				indicator: "green"
			}, 4);

			// Close the dialog
			store.showManifest = false;
		})
		.catch(err => {
			frappe.show_alert({
				message: `Template load failed: ${err.message}`,
				indicator: "red"
			}, 8);
		});
}

function buildManifestData() {
	const slug = s => (s || "").replace(/[\s_]+/g, "-").replace(/[^a-zA-Z0-9\-]/g, "");

	const shipments = [], vehiclesList = [], routes = [];
	const shipEmp = {}, shipReturnEmp = {}, shipSite = {}, shipShift = {}, vMeta = {}, cMap = {};
	let si = 0;

	// Build shipments from swimItems (per direction actually placed)
	store.swimItems.forEach(item => {
		const card = store.shipmentCards.find(c => c.id === item.cardId);
		if (!card) return;

		const dirKey = `${item.cardId}_${item.direction}`;
		if (cMap[dirKey]) return;

		const lbl = `${slug(card.accommodation)}_${si}_${slug(card.site_location)}_${item.direction}`;
		const idx = si++;

		shipments.push({ label: lbl, pickups: [{}], deliveries: [{}] });

		if (item.direction === "RETURN") {
			shipEmp[lbl] = (card.return_employees && card.return_employees.length > 0) ? card.return_employees : [];
		} else {
			shipEmp[lbl] = card.employees || [];
		}
		shipReturnEmp[lbl] = card.return_employees || [];
		shipSite[lbl] = card.site_location;
		shipShift[lbl] = card.shift_name || "";
		cMap[dirKey] = { idx, label: lbl };
	});

	// Build vehicles and routes
	store.vehicles.forEach((v, vi) => {
		vehiclesList.push({
			label: v.label,
			startLocation: { latitude: 0, longitude: 0 },
			endLocation: { latitude: 0, longitude: 0 },
			loadLimits: { seats: { maxLoad: String(v.seats || 0) } },
		});
		vMeta[v.label] = {
			driver: v.driver,
			accommodation: v.accommodation,
			seats: v.seats,
		};

		const vItems = store.swimItems
			.filter(i => i.vehicleId === v.id)
			.sort((a, b) => new Date(a.start) - new Date(b.start));
		if (!vItems.length) return;

		const visits = [], trans = [];
		trans.push({ travelDuration: "0s", waitDuration: "0s", travelDistanceMeters: 0 });

		vItems.forEach((item, idx) => {
			const dirKey = `${item.cardId}_${item.direction}`;
			const info = cMap[dirKey]; if (!info) return;
			const sIdx = info.idx;
			const hc = item.headcount || 0;
			const iS = new Date(item.start).toISOString();
			const iE = new Date(item.end).toISOString();
			const dSec = Math.round((new Date(item.end) - new Date(item.start)) / 1000);

			visits.push({
				shipmentIndex: sIdx, isPickup: true, startTime: iS,
				loadDemands: { seats: { amount: String(hc) } },
				tripId: item.tripId || null,
				stopIndex: item.stopIndex || 0
			});
			trans.push({
				travelDuration: `${dSec}s`, waitDuration: "0s",
				travelDistanceMeters: Math.round(dSec * 10)
			});
			visits.push({
				shipmentIndex: sIdx, isPickup: false, startTime: iE,
				loadDemands: { seats: { amount: String(-hc) } },
				tripId: item.tripId || null,
				stopIndex: item.stopIndex || 0
			});

			const nxt = vItems[idx + 1];
			const gap = nxt ? Math.max(0, new Date(nxt.start) - new Date(item.end)) : 0;
			trans.push({
				travelDuration: `${Math.round(gap / 1000)}s`, waitDuration: "0s",
				travelDistanceMeters: Math.round(gap / 1000 * 8)
			});
		});

		const rS = new Date(vItems[0].start).toISOString();
		const rE = new Date(vItems[vItems.length - 1].end).toISOString();
		const totMs = new Date(rE) - new Date(rS);

		routes.push({
			vehicleIndex: vi, vehicleLabel: v.label,
			vehicleStartTime: rS, vehicleEndTime: rE,
			visits, transitions: trans,
			metrics: {
				travelDistanceMeters: 0,
				totalDuration: `${Math.round(totMs / 1000)}s`,
				travelDuration: `${Math.round(totMs / 1000)}s`
			}
		});
	});

	return {
		request: {
			model: {
				shipments, vehicles: vehiclesList,
				globalStartTime: store.globalStart,
				globalEndTime: store.globalEnd
			}
		},
		response: { routes, skippedShipments: [], metrics: { totalCost: 0 } },
		shipmentEmployees: shipEmp,
		shipmentReturnEmployees: shipReturnEmp,
		shipmentSiteLocations: shipSite,
		shipmentShiftNames: shipShift,
		vehicleMeta: vMeta
	};
}
</script>

<style scoped>
.manifest-container {
	padding: 24px;
}

.manifest-body {
	text-align: center;
}

.manifest-info {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 8px;
}

.manifest-icon {
	font-size: 40px;
	margin-bottom: 4px;
}

.manifest-info h3 {
	font-size: 16px;
	font-weight: 600;
	color: var(--text-color, #333);
	margin: 0;
}

.manifest-info p {
	font-size: 13px;
	color: var(--text-muted, #888);
	max-width: 400px;
	line-height: 1.5;
}

.manifest-stats {
	display: flex;
	gap: 12px;
	margin-top: 8px;
}

.manifest-stat {
	font-size: 12px;
	font-weight: 600;
	padding: 4px 12px;
	border-radius: 16px;
	background: #e8f5e9;
	color: #2e7d32;
}

.manifest-empty {
	font-size: 13px;
	color: #e65100;
	margin-top: 8px;
}
</style>
