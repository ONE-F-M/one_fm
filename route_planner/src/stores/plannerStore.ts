import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const usePlannerStore = defineStore("planner", () => {
	// ── Raw data from server ──
	const vehicles = ref([]);
	const shipmentCards = ref([]);
	const globalStart = ref(null);
	const globalEnd = ref(null);

	// ── Swim items (assignments on timeline) ──
	const swimItems = ref([]);
	const assignedCards = ref(new Set());

	// ── Plan management ──
	const currentPlan = ref(null);
	const planList = ref([]);
	const planLoading = ref(false);

	// ── UI state ──
	const selectedItem = ref(null);
	const searchQuery = ref("");
	const showManifest = ref(false);
	const dataLoading = ref(false);
	const draggingCard = ref(null);
	const isDraggingBlock = ref(false);
	const selectedPoolCard = ref(null);
	const collapsedGroups = ref({});
	const canSave = ref(false);

	// ── Data fetch ──
	function fetchData() {
		dataLoading.value = true;
		frappe.call({
			method: "one_fm.one_fm.page.route_planner.route_planner.get_route_planner_data",
			callback: (r) => {
				if (!r.message || r.message.status === "error") {
					frappe.msgprint(r.message ? r.message.message : "Failed to load data");
					dataLoading.value = false;
					return;
				}
				vehicles.value = r.message.vehicles || [];
				shipmentCards.value = r.message.shipment_cards || [];
				globalStart.value = r.message.global_start;
				globalEnd.value = r.message.global_end;
				dataLoading.value = false;
				console.log("[RP] fetchData done:", vehicles.value.length, "vehicles,", shipmentCards.value.length, "cards, start:", globalStart.value);
				// Load saved plan assignments now that all data is ready
				loadSavedAssignments();
			},
			error: () => {
				dataLoading.value = false;
			},
		});
	}

	// ── Computed: filtered cards ──
	const filteredPoolCards = computed(() => {
		const q = searchQuery.value.toLowerCase().trim();
		return shipmentCards.value.filter((c) => {
			if (isFullyAssigned(c.id)) return false;
			if (!q) return true;
			return (
				c.shift_name.toLowerCase().includes(q) ||
				c.site_location.toLowerCase().includes(q) ||
				c.accommodation.toLowerCase().includes(q) ||
				c.stop_location.toLowerCase().includes(q)
			);
		});
	});

	const poolGroups = computed(() => {
		const map = {};
		filteredPoolCards.value.forEach((c) => {
			if (!map[c.accommodation]) map[c.accommodation] = [];
			map[c.accommodation].push(c);
		});
		return Object.entries(map).map(([acc, cards]) => ({ acc, cards }));
	});

	// ── Assignment checks ──

	function placedDirections(cardId) {
		const dirs = new Set();
		swimItems.value.forEach((i) => {
			if (i.cardId === cardId) dirs.add(i.direction);
		});
		return dirs;
	}

	function isFullyAssigned(cardId) {
		const dirs = placedDirections(cardId);
		return dirs.has("OUTBOUND") && dirs.has("RETURN");
	}

	function cardAssignmentLabel(cardId) {
		const dirs = placedDirections(cardId);
		if (dirs.has("OUTBOUND") && !dirs.has("RETURN")) return "→ Outbound placed";
		if (dirs.has("RETURN") && !dirs.has("OUTBOUND")) return "← Return placed";
		return null;
	}

	// ── Vehicle helpers ──

	function vehicleLabelForItem(item) {
		const v = vehicles.value.find((v) => v.id === item.vehicleId);
		return v ? v.label : item.vehicleId;
	}

	function findCard(cardId) {
		return shipmentCards.value.find((c) => c.id === cardId) || {};
	}

	// ── Peak load calculation ──

	function peakLoadDuringCardWindows(card, vehicleId) {
		const DEF = 3600000;
		const outEnd = new Date(card.outbound_window_end).getTime();
		const outStart = outEnd - DEF;
		const retStart = new Date(card.return_window_start).getTime();
		const retEnd = retStart + DEF;

		const vItems = swimItems.value.filter((i) => i.vehicleId === vehicleId);

		const loadDuring = (wS, wE) => {
			return vItems
				.filter((i) => {
					const iS = new Date(i.start).getTime();
					const iE = new Date(i.end).getTime();
					return iS < wE && iE > wS;
				})
				.reduce((sum, i) => sum + (i.headcount || 0), 0);
		};

		return Math.max(loadDuring(outStart, outEnd), loadDuring(retStart, retEnd));
	}

	// ── Core placement ──

	function doPlace(card, vehicleId, durMs, placeOutbound, placeReturn) {
		const outEnd = new Date(card.outbound_window_end);
		const outStart = new Date(outEnd.getTime() - durMs);
		const retStart = new Date(card.return_window_start);
		const retEnd = new Date(retStart.getTime() + durMs);
		const uid = Math.random().toString(36).slice(2, 10);

		if (placeOutbound) {
			swimItems.value.push({
				id: `${card.id}_OUT_${uid}`, cardId: card.id, vehicleId,
				direction: "OUTBOUND", start: outStart, end: outEnd,
				headcount: card.headcount, conflict: false
			});
		}
		if (placeReturn) {
			swimItems.value.push({
				id: `${card.id}_RET_${uid}`, cardId: card.id, vehicleId,
				direction: "RETURN", start: retStart, end: retEnd,
				headcount: card.headcount, conflict: false
			});
		}

		assignedCards.value.add(card.id);
		selectedPoolCard.value = null;
		checkConflicts();
		canSave.value = assignedCards.value.size > 0;
		persistAssignments();

		const dirLabel = (placeOutbound && placeReturn) ? "Both trips"
			: placeOutbound ? "Outbound (→)" : "Return (←)";
		frappe.show_alert({
			message: `${dirLabel} placed on ${vehicleLabelForItem({ vehicleId })}`,
			indicator: "green"
		}, 4);
	}

	// ── Trip chaining ──

	function chainToTrip(newCard, existingItems, vehicleId, presetTransitMin) {
		// ── Capacity check before chaining ──
		const vehicle = vehicles.value.find((v) => v.id === vehicleId);
		if (vehicle) {
			const currentLoad = peakLoadDuringCardWindows(newCard, vehicleId);
			if (currentLoad + newCard.headcount > vehicle.seats) {
				frappe.show_alert({
					message: `Cannot add stop — ${vehicle.label} would exceed capacity (${currentLoad + newCard.headcount}/${vehicle.seats} seats)`,
					indicator: "red"
				}, 5);
				return;
			}
		}

		// Find or create trip ID
		let tripId = existingItems.find((i) => i.tripId)?.tripId;
		if (!tripId) {
			tripId = `TRIP_${vehicleId}_${Math.random().toString(36).slice(2, 8)}`;
			existingItems
				.sort((a, b) => new Date(a.start) - new Date(b.start))
				.forEach((item, idx) => {
					item.tripId = tripId;
					item.stopIndex = idx + 1;
				});
		}

		// Shared placement logic (transitMin = travel time, dwellMin = buffer at previous stop)
		const doChain = (transitMin, dwellMin) => {
			const dwellMs = (dwellMin || 0) * 60000;
			const transitMs = (transitMin || 30) * 60000;
			const lastEnd = new Date(Math.max(
				...existingItems.map((i) => new Date(i.end).getTime())
			));
			const totalStops = swimItems.value.filter((i) => i.tripId === tripId).length;

			// Buffer: gap after last stop ends before transit to next stop begins
			const segStart = new Date(lastEnd.getTime() + dwellMs);
			const segEnd = new Date(segStart.getTime() + transitMs);
			const uid = Math.random().toString(36).slice(2, 10);

			swimItems.value.push({
				id: `${newCard.id}_OUT_${uid}`, cardId: newCard.id, vehicleId,
				direction: "OUTBOUND", start: segStart, end: segEnd,
				headcount: newCard.headcount, conflict: false,
				tripId, stopIndex: totalStops + 1
			});

			const allTrip = swimItems.value.filter((i) => i.tripId === tripId);
			allTrip.forEach((i) => { i.totalStops = allTrip.length; });

			assignedCards.value.add(newCard.id);
			selectedPoolCard.value = null;
			checkConflicts();
			canSave.value = assignedCards.value.size > 0;
			persistAssignments();

			const bufferNote = dwellMin > 0 ? ` +${dwellMin}min buffer` : "";
			frappe.show_alert({
				message: `Stop ${totalStops + 1}: ${newCard.site_location} (${transitMin}min transit${bufferNote})`,
				indicator: "green"
			}, 4);
		};

		// If transit time was already specified (from multi-trip picker), skip dialog
		if (presetTransitMin != null) {
			doChain(presetTransitMin, 0);
			return;
		}

		// Otherwise show transit time dialog with buffer field
		const lastItem = existingItems
			.sort((a, b) => new Date(a.end) - new Date(b.end))
			.slice(-1)[0];
		const lastCard = shipmentCards.value.find((c) => c.id === lastItem.cardId);
		const lastSiteName = lastCard ? lastCard.site_location : "previous stop";
		const seatInfo = vehicle ? ` (${vehicle.seats} seats, ${peakLoadDuringCardWindows(newCard, vehicleId) + newCard.headcount} needed)` : "";

		const d = new frappe.ui.Dialog({
			title: `Transit to ${newCard.site_location}`,
			fields: [
				{
					fieldtype: "HTML",
					options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
						How long from <strong>${lastSiteName}</strong>
						to <strong>${newCard.site_location}</strong>?${seatInfo}</p>`
				},
				{
					fieldtype: "Int", fieldname: "transit_min",
					label: "Transit Time (minutes)",
					default: 30, reqd: 1,
					description: "Driving time between stops"
				},
				{ fieldtype: "Column Break" },
				{
					fieldtype: "Int", fieldname: "dwell_min",
					label: "Dwell/Buffer Time (minutes)",
					default: 10,
					description: "Loading/unloading time at previous stop before departing"
				}
			],
			primary_action_label: "Add Stop",
			primary_action(vals) {
				d.hide();
				doChain(vals.transit_min, vals.dwell_min || 0);
			}
		});
		d.show();
	}

	// ── Conflict & overcapacity detection ──

	function checkConflicts() {
		swimItems.value.forEach((i) => { i.conflict = false; i.overcapacity = false; });
		vehicles.value.forEach((v) => {
			const vi = swimItems.value.filter((i) => i.vehicleId === v.id);

			// Time overlap detection
			for (let a = 0; a < vi.length; a++) {
				for (let b = a + 1; b < vi.length; b++) {
					const ia = vi[a], ib = vi[b];
					if (ia.tripId && ia.tripId === ib.tripId) continue;
					const aS = new Date(ia.start).getTime(), aE = new Date(ia.end).getTime();
					const bS = new Date(ib.start).getTime(), bE = new Date(ib.end).getTime();
					if (aS < bE && aE > bS) { ia.conflict = true; ib.conflict = true; }
				}
			}

			// Overcapacity detection: check headcount at each item's time window
			if (v.seats && vi.length > 0) {
				vi.forEach((item) => {
					const iS = new Date(item.start).getTime();
					const iE = new Date(item.end).getTime();
					// Sum all headcounts overlapping this item's time window
					const load = vi
						.filter((o) => {
							const oS = new Date(o.start).getTime();
							const oE = new Date(o.end).getTime();
							return oS < iE && oE > iS;
						})
						.reduce((sum, o) => sum + (o.headcount || 0), 0);
					if (load > v.seats) {
						item.overcapacity = true;
					}
				});
			}
		});
	}

	// ── Removal ──

	function removeSelectedFromLane() {
		if (!selectedItem.value) return;
		const itemId = selectedItem.value.id;
		const cid = selectedItem.value.cardId;
		const dir = selectedItem.value.direction;

		swimItems.value = swimItems.value.filter((i) => i.id !== itemId);
		const remaining = swimItems.value.filter((i) => i.cardId === cid);
		if (remaining.length === 0) assignedCards.value.delete(cid);

		selectedItem.value = null;
		checkConflicts();
		canSave.value = assignedCards.value.size > 0 || swimItems.value.length > 0;
		persistAssignments();

		frappe.show_alert({
			message: `${dir === "OUTBOUND" ? "Outbound (→)" : "Return (←)"} removed`,
			indicator: "orange"
		}, 3);
	}

	// ── Merged items (trip chains render as single block) ──

	const mergedItemsByVehicle = computed(() => {
		const merged = {};
		vehicles.value.forEach((v) => {
			const items = swimItems.value.filter((i) => i.vehicleId === v.id);
			const entries = [];
			const tripGroups = {};

			items.forEach((item) => {
				if (item.tripId) {
					if (!tripGroups[item.tripId]) tripGroups[item.tripId] = [];
					tripGroups[item.tripId].push(item);
				} else {
					entries.push({
						type: "single", item,
						_layoutStart: new Date(item.start).getTime(),
						_layoutEnd: new Date(item.end).getTime(),
					});
				}
			});

			Object.keys(tripGroups).forEach((tripId) => {
				const stops = tripGroups[tripId].sort(
					(a, b) => new Date(a.start) - new Date(b.start)
				);
				const firstItem = stops[0];
				const lastItem = stops[stops.length - 1];
				const totalHC = stops.reduce((sum, s) => sum + (s.headcount || 0), 0);
				const stopLabels = stops.map((s) => {
					const card = shipmentCards.value.find((c) => c.id === s.cardId);
					return card ? card.site_location : s.cardId;
				});

				entries.push({
					type: "merged", tripId,
					direction: firstItem.direction,
					start: firstItem.start, end: lastItem.end,
					headcount: totalHC, stopLabels, stops,
					conflict: stops.some((s) => s.conflict),
					primaryItem: firstItem,
					_layoutStart: new Date(firstItem.start).getTime(),
					_layoutEnd: new Date(lastItem.end).getTime(),
				});
			});

			// Recalculate overlap columns
			if (entries.length <= 1) {
				entries.forEach((e) => { e._col = 0; e._totalCols = 1; });
			} else {
				entries.sort((a, b) => {
					const d = a._layoutStart - b._layoutStart;
					return d !== 0 ? d : b._layoutEnd - a._layoutEnd;
				});
				const columns = [];
				entries.forEach((entry) => {
					let placed = false;
					for (let c = 0; c < columns.length; c++) {
						const last = columns[c][columns[c].length - 1];
						if (last._layoutEnd <= entry._layoutStart) {
							columns[c].push(entry);
							entry._col = c;
							placed = true;
							break;
						}
					}
					if (!placed) {
						entry._col = columns.length;
						columns.push([entry]);
					}
				});
				const groups = [];
				let group = [entries[0]];
				let groupEnd = entries[0]._layoutEnd;
				for (let i = 1; i < entries.length; i++) {
					if (entries[i]._layoutStart < groupEnd) {
						group.push(entries[i]);
						groupEnd = Math.max(groupEnd, entries[i]._layoutEnd);
					} else {
						groups.push(group);
						group = [entries[i]];
						groupEnd = entries[i]._layoutEnd;
					}
				}
				groups.push(group);
				groups.forEach((g) => {
					const maxCol = Math.max(...g.map((e) => e._col)) + 1;
					g.forEach((e) => { e._totalCols = maxCol; });
				});
			}

			merged[v.id] = entries;
		});
		return merged;
	});

	// ── Selected card computed ──

	const selectedCard = computed(() => {
		if (!selectedItem.value) return null;
		return shipmentCards.value.find((c) => c.id === selectedItem.value.cardId) || null;
	});

	const selectedTripStops = computed(() => {
		if (!selectedItem.value || !selectedItem.value.tripId) return [];
		const tripId = selectedItem.value.tripId;
		return swimItems.value
			.filter((i) => i.tripId === tripId)
			.sort((a, b) => new Date(a.start) - new Date(b.start))
			.map((item, idx) => ({
				item,
				card: shipmentCards.value.find((c) => c.id === item.cardId) || {},
				stopNum: idx + 1
			}));
	});

	// ── Persistence ──

	let _persistTimer = null;
	function persistAssignments() {
		if (!currentPlan.value) return;
		clearTimeout(_persistTimer);
		_persistTimer = setTimeout(() => {
			const items = swimItems.value.map((i) => {
				const card = shipmentCards.value.find((c) => c.id === i.cardId);
				return {
					id: i.id, cardId: i.cardId, vehicleId: i.vehicleId,
					direction: i.direction,
					start: new Date(i.start).toISOString(),
					end: new Date(i.end).toISOString(),
					headcount: i.headcount, conflict: i.conflict,
					tripId: i.tripId || null,
					stopIndex: i.stopIndex || 0,
					totalStops: i.totalStops || 0,
					_accommodation: card ? card.accommodation : "",
					_stopLocation: card ? card.stop_location : "",
				};
			});
			const cards = [...assignedCards.value];
			frappe.call({
				method: "one_fm.one_fm.page.route_planner.route_planner.save_assignments",
				args: {
					plan_name: currentPlan.value.name,
					swim_items: JSON.stringify(items),
					assigned_cards: JSON.stringify(cards)
				},
				async: true,
				callback: () => { },
			});
		}, 500);
	}

	// ── Load plan ──

	function loadSavedAssignments() {
		console.log("[RP] loadSavedAssignments called, vehicles:", vehicles.value.length);
		planLoading.value = true;
		frappe.call({
			method: "one_fm.one_fm.page.route_planner.route_planner.get_route_plans",
			async: true,
			callback: (r) => {
				planList.value = r.message || [];
				frappe.call({
					method: "one_fm.one_fm.page.route_planner.route_planner.load_assignments",
					args: { plan_name: "" },
					async: true,
					callback: (r2) => {
						planLoading.value = false;
						if (r2.message && r2.message.status === "ok") {
							applyLoadedPlan(r2.message);
						} else if (planList.value.length > 0) {
							// No active plan found — auto-select first plan from list
							const firstPlan = planList.value[0];
							switchPlan(firstPlan.name);
						}
					}
				});
			}
		});
	}

	function applyLoadedPlan(msg) {
		const items = msg.swim_items || [];
		const cards = msg.assigned_cards || [];
		console.log("[RP] applyLoadedPlan:", msg.plan_name, "items:", items.length, "cards:", cards.length);

		currentPlan.value = {
			name: msg.plan_name,
			title: msg.plan_title,
			status: msg.plan_status,
			effective_from: msg.effective_from,
			effective_until: msg.effective_until
		};

		// Restore + rebase dates to today's timeline
		let parsedItems = items.map((i) => ({
			...i,
			start: new Date(i.start),
			end: new Date(i.end)
		}));

		if (parsedItems.length > 0) {
			const earliestSaved = Math.min(...parsedItems.map((i) => i.start.getTime()));
			const savedDay = new Date(earliestSaved);
			savedDay.setUTCHours(0, 0, 0, 0);
			const todayDay = new Date(globalStart.value || Date.now());
			todayDay.setUTCHours(0, 0, 0, 0);
			const dayOffsetMs = todayDay.getTime() - savedDay.getTime();

			if (Math.abs(dayOffsetMs) > 12 * 3600000) {
				parsedItems = parsedItems.map((i) => ({
					...i,
					start: new Date(i.start.getTime() + dayOffsetMs),
					end: new Date(i.end.getTime() + dayOffsetMs)
				}));
			}
		}

		swimItems.value = parsedItems;
		assignedCards.value = new Set(cards);
		checkConflicts();
		canSave.value = assignedCards.value.size > 0;
		console.log("[RP] swimItems set:", swimItems.value.length, "vehicles:", vehicles.value.length);
		if (parsedItems.length > 0) {
			console.log("[RP] first item:", JSON.stringify({id: parsedItems[0].id, vehicleId: parsedItems[0].vehicleId, start: parsedItems[0].start.toISOString(), end: parsedItems[0].end.toISOString()}));
		}

		if (items.length > 0) {
			frappe.show_alert({
				message: `Loaded plan "${msg.plan_title}" — ${items.length} assignments`,
				indicator: "blue"
			}, 4);
		}
	}



	function switchPlan(planName) {
		if (!planName) return;
		planLoading.value = true;
		frappe.call({
			method: "one_fm.one_fm.page.route_planner.route_planner.load_assignments",
			args: { plan_name: planName },
			async: true,
			callback: (r) => {
				planLoading.value = false;
				if (r.message && r.message.status === "ok") {
					console.log("[RP] switchPlan got ok, items:", r.message.swim_items?.length);
					applyLoadedPlan(r.message);
				} else {
					swimItems.value = [];
					assignedCards.value = new Set();
					canSave.value = false;
					const plan = planList.value.find((p) => p.name === planName);
					if (plan) {
						currentPlan.value = {
							name: plan.name,
							title: plan.title,
							status: plan.status,
							effective_from: plan.effective_from,
							effective_until: plan.effective_until
						};
					}
				}
			}
		});
	}

	function createNewPlan() {
		const d = new frappe.ui.Dialog({
			title: __("Create New Route Plan"),
			fields: [
				{
					fieldname: "title", label: "Plan Title", fieldtype: "Data", reqd: 1,
					description: "e.g. May 2026 Plan"
				},
				{
					fieldname: "effective_from", label: "Effective From", fieldtype: "Date", reqd: 1,
					default: frappe.datetime.get_today()
				},
				{
					fieldname: "effective_until", label: "Effective Until", fieldtype: "Date",
					description: "Leave blank for indefinite"
				},
			],
			primary_action_label: __("Create"),
			primary_action(values) {
				frappe.call({
					method: "one_fm.one_fm.page.route_planner.route_planner.create_route_plan",
					args: values,
					callback: (r) => {
						if (r.message && r.message.status === "ok") {
							d.hide();
							frappe.show_alert({
								message: `Plan "${r.message.plan_title}" created`,
								indicator: "green"
							}, 4);
							refreshPlanList(() => switchPlan(r.message.plan_name));
						}
					}
				});
			}
		});
		d.show();
	}

	function togglePlanStatus(newStatus) {
		if (!currentPlan.value) return;
		const planName = currentPlan.value.name;
		const doUpdate = () => {
			frappe.call({
				method: "one_fm.one_fm.page.route_planner.route_planner.update_route_plan_status",
				args: { plan_name: planName, new_status: newStatus },
				callback: (r) => {
					if (r.message && r.message.status === "ok") {
						currentPlan.value.status = newStatus;
						refreshPlanList();
						frappe.show_alert({
							message: `Plan status updated to ${newStatus}`,
							indicator: "green"
						}, 3);
					}
				}
			});
		};

		if (newStatus === "Active" || newStatus === "Expired") {
			frappe.confirm(
				`Set plan "${currentPlan.value.title}" to <strong>${newStatus}</strong>?`,
				doUpdate
			);
		} else {
			doUpdate();
		}
	}

	function refreshPlanList(cb) {
		frappe.call({
			method: "one_fm.one_fm.page.route_planner.route_planner.get_route_plans",
			async: true,
			callback: (r) => {
				planList.value = r.message || [];
				if (cb) cb();
			}
		});
	}

	function savePlan() {
		if (!currentPlan.value) {
			frappe.show_alert({ message: "Create or select a plan first", indicator: "orange" });
			return;
		}

		// ── Pre-save overcapacity audit ──
		checkConflicts(); // ensure overcapacity flags are fresh
		const overcapVehicles = [];
		vehicles.value.forEach((v) => {
			const vi = swimItems.value.filter((i) => i.vehicleId === v.id);
			if (vi.some((i) => i.overcapacity)) {
				const peakLoad = Math.max(...vi.map((item) => {
					const iS = new Date(item.start).getTime();
					const iE = new Date(item.end).getTime();
					return vi
						.filter((o) => {
							const oS = new Date(o.start).getTime();
							const oE = new Date(o.end).getTime();
							return oS < iE && oE > iS;
						})
						.reduce((sum, o) => sum + (o.headcount || 0), 0);
				}));
				overcapVehicles.push({ label: v.label, seats: v.seats, peak: peakLoad });
			}
		});

		const doSave = () => {
			const items = swimItems.value.map((i) => {
				const card = shipmentCards.value.find((c) => c.id === i.cardId);
				return {
					id: i.id, cardId: i.cardId, vehicleId: i.vehicleId,
					direction: i.direction,
					start: new Date(i.start).toISOString(),
					end: new Date(i.end).toISOString(),
					headcount: i.headcount, conflict: i.conflict,
					tripId: i.tripId || null,
					stopIndex: i.stopIndex || 0,
					totalStops: i.totalStops || 0,
					_accommodation: card ? card.accommodation : "",
					_stopLocation: card ? card.stop_location : "",
				};
			});
			const cards = [...assignedCards.value];
			frappe.call({
				method: "one_fm.one_fm.page.route_planner.route_planner.save_assignments",
				args: {
					plan_name: currentPlan.value.name,
					swim_items: JSON.stringify(items),
					assigned_cards: JSON.stringify(cards)
				},
				callback: () => {
					frappe.show_alert({ message: "Plan saved", indicator: "green" }, 3);
				}
			});
		};

		// Show warning if overcapacity detected, but allow saving anyway
		if (overcapVehicles.length > 0) {
			const list = overcapVehicles.map((v) =>
				`<li><strong>${v.label}</strong>: ${v.peak} passengers / ${v.seats} seats</li>`
			).join("");
			frappe.confirm(
				`<div style="color:#c62828;font-weight:600;margin-bottom:8px">⚠ Overcapacity Warning</div>` +
				`<p style="font-size:13px;color:#555">The following vehicles exceed seat capacity:</p>` +
				`<ul style="font-size:13px;margin:8px 0 12px 16px">${list}</ul>` +
				`<p style="font-size:13px;color:#555">Save anyway?</p>`,
				() => doSave(),
				() => frappe.show_alert({ message: "Save cancelled — fix overcapacity first", indicator: "orange" }, 4)
			);
		} else {
			doSave();
		}
	}

	// ── Manifest ──

	function openManifest() {
		if (swimItems.value.length === 0) {
			frappe.show_alert({ message: "No assignments on the timeline yet.", indicator: "orange" });
			return;
		}

		const routeData = buildManifestData();
		if (!routeData.response.routes.length) {
			frappe.show_alert({ message: "No assigned shipments to generate a manifest from.", indicator: "orange" });
			return;
		}

		const bv = (frappe.boot && frappe.boot.build_version) || Date.now();
		fetch(`/assets/one_fm/html/route_manifest_template.html?v=${bv}`)
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
			})
			.catch(err => {
				frappe.show_alert({ message: `Template load failed: ${err.message}`, indicator: "red" }, 8);
			});
	}

	function buildManifestData() {
		const slug = s => (s || "").replace(/[\s_]+/g, "-").replace(/[^a-zA-Z0-9\-]/g, "");
		const shipments = [], vehiclesList = [], routes = [];
		const shipEmp = {}, shipReturnEmp = {}, shipSite = {}, shipShift = {}, vMeta = {}, cMap = {};
		let si = 0;

		swimItems.value.forEach(item => {
			const card = shipmentCards.value.find(c => c.id === item.cardId);
			if (!card) return;
			const dirKey = `${item.cardId}_${item.direction}`;
			if (cMap[dirKey]) return;
			const lbl = `${slug(card.accommodation)}_${si}_${slug(card.site_location)}_${item.direction}`;
			const idx = si++;
			shipments.push({ label: lbl, pickups: [{}], deliveries: [{}] });
			shipEmp[lbl] = item.direction === "RETURN"
				? (card.return_employees && card.return_employees.length > 0 ? card.return_employees : [])
				: (card.employees || []);
			shipReturnEmp[lbl] = card.return_employees || [];
			shipSite[lbl] = card.site_location;
			shipShift[lbl] = card.shift_name || "";
			cMap[dirKey] = { idx, label: lbl };
		});

		vehicles.value.forEach((v, vi) => {
			vehiclesList.push({
				label: v.label,
				startLocation: { latitude: 0, longitude: 0 },
				endLocation: { latitude: 0, longitude: 0 },
				loadLimits: { seats: { maxLoad: String(v.seats || 0) } },
			});
			vMeta[v.label] = { driver: v.driver, accommodation: v.accommodation, seats: v.seats };

			const vItems = swimItems.value
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
					tripId: item.tripId || null, stopIndex: item.stopIndex || 0
				});
				trans.push({ travelDuration: `${dSec}s`, waitDuration: "0s", travelDistanceMeters: Math.round(dSec * 10) });
				visits.push({
					shipmentIndex: sIdx, isPickup: false, startTime: iE,
					loadDemands: { seats: { amount: String(-hc) } },
					tripId: item.tripId || null, stopIndex: item.stopIndex || 0
				});
				const nxt = vItems[idx + 1];
				const gap = nxt ? Math.max(0, new Date(nxt.start) - new Date(item.end)) : 0;
				trans.push({ travelDuration: `${Math.round(gap / 1000)}s`, waitDuration: "0s", travelDistanceMeters: Math.round(gap / 1000 * 8) });
			});

			const rS = new Date(vItems[0].start).toISOString();
			const rE = new Date(vItems[vItems.length - 1].end).toISOString();
			const totMs = new Date(rE) - new Date(rS);
			routes.push({
				vehicleIndex: vi, vehicleLabel: v.label,
				vehicleStartTime: rS, vehicleEndTime: rE,
				visits, transitions: trans,
				metrics: { travelDistanceMeters: 0, totalDuration: `${Math.round(totMs / 1000)}s`, travelDuration: `${Math.round(totMs / 1000)}s` }
			});
		});

		return {
			request: { model: { shipments, vehicles: vehiclesList, globalStartTime: globalStart.value, globalEndTime: globalEnd.value } },
			response: { routes, skippedShipments: [], metrics: { totalCost: 0 } },
			shipmentEmployees: shipEmp, shipmentReturnEmployees: shipReturnEmp,
			shipmentSiteLocations: shipSite, shipmentShiftNames: shipShift, vehicleMeta: vMeta
		};
	}

	return {
		// State
		vehicles, shipmentCards, globalStart, globalEnd,
		swimItems, assignedCards,
		currentPlan, planList, planLoading,
		selectedItem, searchQuery, showManifest, dataLoading,
		draggingCard, isDraggingBlock, selectedPoolCard,
		collapsedGroups, canSave,

		// Computed
		filteredPoolCards, poolGroups,
		mergedItemsByVehicle, selectedCard, selectedTripStops,

		// Methods
		fetchData, placedDirections, isFullyAssigned, cardAssignmentLabel,
		vehicleLabelForItem, findCard,
		peakLoadDuringCardWindows, doPlace, chainToTrip,
		checkConflicts, removeSelectedFromLane,
		loadSavedAssignments, applyLoadedPlan, switchPlan,
		createNewPlan, togglePlanStatus, savePlan,
		persistAssignments, refreshPlanList,
		openManifest,
	};
});
