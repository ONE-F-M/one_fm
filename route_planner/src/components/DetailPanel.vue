<template>
	<aside class="rp-detail" v-if="store.selectedItem && store.selectedCard">
		<div class="rp-detail-header">
			<div class="rp-detail-title">SHIPMENT DETAILS</div>
			<button class="rp-detail-close" @click="store.selectedItem = null">✕</button>
		</div>

		<div class="rp-detail-body">
			<!-- Direction + Vehicle badges -->
			<div class="rp-detail-badges">
				<span :class="['rp-dir-badge', store.selectedItem.direction === 'OUTBOUND' ? 'rp-dir-out' : 'rp-dir-ret']">
					{{ store.selectedItem.direction === 'OUTBOUND' ? '→ Outbound' : '← Return' }}
				</span>
				<span v-if="tripStops.length > 0" class="rp-dir-badge rp-dir-trip">
					{{ tripStops.length }} Stops
				</span>
				<span class="rp-dir-badge rp-dir-vehicle">
					{{ store.vehicleLabelForItem(store.selectedItem) }}
				</span>
			</div>

			<!-- ═══ TRIP VIEW: multiple stops ═══ -->
			<template v-if="tripStops.length > 0">
				<!-- Trip time summary -->
				<div class="rp-detail-card">
					<div class="rp-section-label">TRIP TIMELINE</div>
					<div class="rp-time-big">
						{{ fmtISO(tripStops[0].item.start) }}
						<span class="rp-time-arrow">→</span>
						{{ fmtISO(tripStops[tripStops.length - 1].item.end) }}
						<span class="rp-time-dur">({{ tripDurationMin }} min)</span>
					</div>
				</div>

				<!-- Each stop as a numbered card -->
				<div v-for="stop in tripStops" :key="stop.item.id"
					class="rp-detail-card rp-stop-card"
					:style="'border-left:3px solid ' + (stop.item.id === store.selectedItem.id ? '#f97316' : '#1565c0')">
					<div class="rp-stop-header">
						<span class="rp-stop-num">{{ stop.stopNum }}</span>
						<div class="rp-stop-site">{{ stop.card.site_location || 'Unknown' }}</div>
					</div>
					<div class="rp-info-row">
						<span class="rp-info-icon">🕐</span>
						<div>
							<div class="rp-info-label">SHIFT</div>
							<div class="rp-info-value">{{ stop.card.shift_name || '—' }}</div>
						</div>
					</div>
					<div class="rp-info-row">
						<span class="rp-info-icon">📍</span>
						<div>
							<div class="rp-info-label">STOP LOCATION</div>
							<div class="rp-info-value">{{ stop.card.stop_location || '—' }}</div>
						</div>
					</div>
					<div class="rp-info-row">
						<span class="rp-info-icon">👥</span>
						<div>
							<div class="rp-info-label">HEADCOUNT</div>
							<div class="rp-info-value">{{ stop.item.headcount || 0 }} employees</div>
						</div>
					</div>
					<div class="rp-time-pills">
						<span class="rp-pill rp-pill-start">{{ fmtISO(stop.item.start) }}</span>
						<span class="rp-pill-arrow">→</span>
						<span class="rp-pill rp-pill-end">{{ fmtISO(stop.item.end) }}</span>
					</div>
				</div>

				<!-- Accommodation (shared for all stops) -->
				<div class="rp-detail-card">
					<div class="rp-info-row" style="border:none">
						<span class="rp-info-icon">🏠</span>
						<div>
							<div class="rp-info-label">ACCOMMODATION</div>
							<div class="rp-info-value">{{ store.selectedCard.accommodation }}</div>
						</div>
					</div>
				</div>

				<!-- All employees across all stops -->
				<div class="rp-detail-card">
					<div class="rp-section-label">
						👥 ALL EMPLOYEES ({{ tripTotalHeadcount }})
					</div>
					<div class="rp-emp-list">
						<template v-for="stop in tripStops" :key="'emp_'+stop.item.id">
							<span v-for="e in (stop.card.employees || [])" :key="stop.item.id + '_' + e"
								class="rp-emp-chip">{{ e }}</span>
						</template>
					</div>
				</div>
			</template>

			<!-- ═══ SINGLE ITEM VIEW (non-trip) ═══ -->
			<template v-else>
				<!-- OLM badge -->
				<div v-if="store.selectedCard.type === 'OLM'" class="rp-detail-card rp-olm-card">
					<div class="rp-info-row" style="border:none">
						<span class="rp-info-icon">📍</span>
						<div>
							<div class="rp-info-label" style="color:#7c3aed">SHARED BUS STOP</div>
							<div class="rp-info-value">{{ store.selectedCard.stop_location }}</div>
						</div>
					</div>
				</div>

				<!-- OLM: Per-site route breakdown -->
				<template v-if="store.selectedCard.type === 'OLM' && store.selectedCard.sites && store.selectedCard.sites.length">
					<div v-for="(s, si) in store.selectedCard.sites" :key="si"
						class="rp-detail-card" style="border-left:3px solid #7c3aed">
						<div class="rp-stop-header">
							<span class="rp-stop-num rp-stop-olm">{{ si + 1 }}</span>
							<div class="rp-stop-site">{{ s.site }}</div>
						</div>
						<div v-for="sh in s.shifts" :key="sh" class="rp-shift-line">🕐 {{ sh }}</div>
					</div>
				</template>

				<!-- DIRECT / OSM: Full info card -->
				<div v-if="store.selectedCard.type !== 'OLM'" class="rp-detail-card">
					<div class="rp-info-row">
						<span class="rp-info-icon">🏢</span>
						<div>
							<div class="rp-info-label">SITE</div>
							<div class="rp-info-value">{{ store.selectedCard.site_location }}</div>
						</div>
					</div>
					<div class="rp-info-row">
						<span class="rp-info-icon">🕐</span>
						<div>
							<div class="rp-info-label">SHIFT</div>
							<div class="rp-info-value">{{ store.selectedCard.shift_name }}</div>
						</div>
					</div>
					<div class="rp-info-row">
						<span class="rp-info-icon">📍</span>
						<div>
							<div class="rp-info-label">STOP LOCATION</div>
							<div class="rp-info-value">{{ store.selectedCard.stop_location }}</div>
						</div>
					</div>
					<div class="rp-info-row">
						<span class="rp-info-icon">👥</span>
						<div>
							<div class="rp-info-label">HEADCOUNT</div>
							<div class="rp-info-value">{{ store.selectedCard.headcount }} employees</div>
						</div>
					</div>
					<div class="rp-info-row">
						<span class="rp-info-icon">🏠</span>
						<div>
							<div class="rp-info-label">ACCOMMODATION</div>
							<div class="rp-info-value">{{ store.selectedCard.accommodation }}</div>
						</div>
					</div>
				</div>

				<!-- Time card -->
				<div class="rp-detail-card">
					<div class="rp-section-label">TIME ON LANE</div>
					<div class="rp-time-big">
						{{ fmtISO(store.selectedItem.start) }}
						<span class="rp-time-arrow">→</span>
						{{ fmtISO(store.selectedItem.end) }}
						<span class="rp-time-dur">({{ durMin(store.selectedItem) }} min)</span>
					</div>
					<div class="rp-shift-pills">
						<div class="rp-shift-pill rp-spill-start">
							<div class="rp-spill-label">SHIFT START</div>
							<div class="rp-spill-value">{{ fmtISO(store.selectedCard.shift_start) }}</div>
						</div>
						<div class="rp-shift-pill rp-spill-end">
							<div class="rp-spill-label">SHIFT END</div>
							<div class="rp-spill-value">{{ fmtISO(store.selectedCard.shift_end) }}</div>
						</div>
					</div>
				</div>

				<!-- Employees -->
				<div class="rp-detail-card">
					<div class="rp-section-label">
						👥 EMPLOYEES ({{ store.selectedCard.headcount }})
					</div>
					<div class="rp-emp-list">
						<span v-for="e in (store.selectedCard.employees || [])" :key="e"
							class="rp-emp-chip">{{ e }}</span>
					</div>
				</div>
			</template>
		</div>

		<!-- Footer actions -->
		<div class="rp-detail-footer">
			<button class="rp-action-btn rp-action-primary" @click="reassignVehicle">
				🚌 Reassign Vehicle
			</button>
			<button class="rp-action-btn rp-action-danger" @click="store.removeSelectedFromLane">
				✕ Remove from Lane
			</button>
		</div>
	</aside>
</template>

<script setup>
import { computed } from "vue";
import { usePlannerStore } from "@/stores/plannerStore";
const store = usePlannerStore();

// Use local computed to avoid any reactivity issues
const tripStops = computed(() => store.selectedTripStops);
const tripDurationMin = computed(() => {
	if (tripStops.value.length === 0) return 0;
	const first = tripStops.value[0].item;
	const last = tripStops.value[tripStops.value.length - 1].item;
	return Math.round((new Date(last.end) - new Date(first.start)) / 60000);
});
const tripTotalHeadcount = computed(() => {
	return tripStops.value.reduce((sum, s) => sum + (s.item.headcount || 0), 0);
});

function fmtISO(t) {
	if (!t) return "—";
	return new Date(t).toLocaleTimeString("en-GB", {
		hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kuwait"
	});
}

function durMin(item) {
	return Math.round((new Date(item.end) - new Date(item.start)) / 60000);
}

function reassignVehicle() {
	const item = store.selectedItem;
	if (!item) return;

	const currentVehicle = store.vehicleLabelForItem(item);
	const options = store.vehicles
		.filter(v => v.id !== item.vehicleId)
		.map(v => v.label)
		.join("\n");

	const d = new frappe.ui.Dialog({
		title: __("Reassign Vehicle"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<p style="margin:0 0 8px;font-size:13px;color:#555">
					Currently on <strong>${currentVehicle}</strong>
				</p>`
			},
			{
				fieldname: "new_vehicle", label: "New Vehicle", fieldtype: "Select",
				options: options, reqd: 1
			}
		],
		primary_action_label: __("Move"),
		primary_action(vals) {
			d.hide();
			const newV = store.vehicles.find(v => v.label === vals.new_vehicle);
			if (!newV) return;

			// Check seat capacity
			const card = store.findCard(item.cardId);
			const peak = store.peakLoadDuringCardWindows(card, newV.id);
			if (peak + (item.headcount || 0) > newV.seats) {
				frappe.show_alert({
					message: `Cannot move — ${newV.label} only has ${newV.seats - peak} seats available`,
					indicator: "red"
				}, 5);
				return;
			}

			// Move all items in trip chain (if any)
			const toMove = item.tripId
				? store.swimItems.filter(i => i.tripId === item.tripId)
				: [item];

			toMove.forEach(i => { i.vehicleId = newV.id; });
			store.checkConflicts();
			store.canSave = store.assignedCards.size > 0;
			store.persistAssignments();

			frappe.show_alert({
				message: `Moved to ${newV.label}`,
				indicator: "blue"
			}, 3);
		}
	});
	d.show();
}
</script>

<style scoped>
.rp-detail { display: flex; flex-direction: column; height: 100%; overflow: hidden; background: var(--bg-color, #fff); }

/* Header */
.rp-detail-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid var(--border-color, #e2e2e2); flex-shrink: 0; }
.rp-detail-title { font-size: 13px; font-weight: 800; letter-spacing: 0.06em; color: var(--text-color, #111); }
.rp-detail-close { background: none; border: none; font-size: 18px; cursor: pointer; color: var(--text-muted, #999); padding: 4px 8px; border-radius: 4px; }
.rp-detail-close:hover { background: #f0f0f0; }

/* Body */
.rp-detail-body { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }

/* Badges */
.rp-detail-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.rp-dir-badge { font-size: 11px; font-weight: 700; padding: 4px 12px; border-radius: 14px; letter-spacing: 0.02em; }
.rp-dir-out { background: #e3f2fd; color: #1565c0; }
.rp-dir-ret { background: #fff3e0; color: #e65100; }
.rp-dir-trip { background: #f3e8fd; color: #7c3aed; }
.rp-dir-vehicle { background: #e3f2fd; color: #1565c0; }

/* Cards */
.rp-detail-card { background: var(--bg-light-gray, #fafafa); border: 1px solid var(--border-color, #eee); border-radius: 12px; padding: 12px 16px; }

/* Section labels */
.rp-section-label { font-size: 10px; font-weight: 800; letter-spacing: 0.08em; color: var(--text-muted, #888); text-transform: uppercase; padding: 0 0 8px 0; }

/* Info rows (icon + label + value) */
.rp-info-row { display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.rp-info-row:last-child { border-bottom: none; }
.rp-info-icon { font-size: 16px; margin-top: 2px; flex-shrink: 0; }
.rp-info-label { font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted, #999); }
.rp-info-value { font-size: 13px; font-weight: 500; color: var(--text-color, #222); line-height: 1.4; }

/* Time displays */
.rp-time-big { font-size: 18px; font-weight: 700; color: var(--text-color, #111); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.rp-time-arrow { color: var(--text-muted, #aaa); font-size: 14px; }
.rp-time-dur { font-size: 12px; font-weight: 400; color: var(--text-muted, #999); }

/* Stop header */
.rp-stop-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.rp-stop-num { width: 26px; height: 26px; border-radius: 50%; background: #bbdefb; color: #1565c0; font-size: 12px; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.rp-stop-olm { background: #e8d5f5; color: #7c3aed; }
.rp-stop-site { font-size: 15px; font-weight: 700; color: var(--text-color, #111); }

/* Time pills */
.rp-time-pills { display: flex; gap: 6px; align-items: center; margin-top: 8px; padding-left: 36px; }
.rp-pill { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 6px; }
.rp-pill-start { background: #e3f2fd; color: #1565c0; }
.rp-pill-end { background: #fff3e0; color: #e65100; }
.rp-pill-arrow { color: #aaa; font-size: 10px; }

/* Shift pills */
.rp-shift-pills { display: flex; gap: 10px; margin-top: 10px; }
.rp-shift-pill { flex: 1; padding: 8px 10px; border-radius: 8px; }
.rp-spill-start { background: #e3f2fd; }
.rp-spill-end { background: #fff3e0; }
.rp-spill-label { font-size: 8px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #999; }
.rp-spill-value { font-size: 15px; font-weight: 700; color: #333; margin-top: 2px; }

/* OLM */
.rp-olm-card { background: #f3e8fd; border-color: #e0cffc; }
.rp-shift-line { font-size: 12px; color: #888; margin-left: 36px; padding: 3px 0; }

/* Employees */
.rp-emp-list { display: flex; flex-wrap: wrap; gap: 5px; }
.rp-emp-chip { font-size: 11px; padding: 4px 10px; border-radius: 6px; background: #f0f0f0; color: #444; border: 1px solid #e2e2e2; font-weight: 500; }

/* Footer */
.rp-detail-footer { padding: 12px 14px; border-top: 1px solid #e2e2e2; flex-shrink: 0; display: flex; flex-direction: column; gap: 8px; }
.rp-action-btn { display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: 1px solid; transition: background 0.15s, transform 0.1s; }
.rp-action-btn:active { transform: scale(0.98); }
.rp-action-primary { background: #e3f2fd; color: #1565c0; border-color: #90caf9; }
.rp-action-primary:hover { background: #bbdefb; }
.rp-action-danger { background: #fff; color: #c62828; border-color: #ef9a9a; }
.rp-action-danger:hover { background: #ffebee; }
</style>
