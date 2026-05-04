frappe.pages['route-planner'].on_page_load = function (wrapper) {
    injectRPLoadingStyles();
    $(wrapper).html(`
        <div id="rp-loading">
            <div id="rp-loading-spinner"></div>
            <div id="rp-loading-text">Loading Route Planner...</div>
            <div id="rp-loading-sub">Fetching vehicles, shifts and employee data</div>
        </div>
    `);

    if (!document.querySelector('#vue3-cdn')) {
        const s = document.createElement('script');
        s.id = 'vue3-cdn';
        s.src = 'https://unpkg.com/vue@3/dist/vue.global.prod.js';
        s.onload = () => fetchRPData(wrapper);
        document.head.appendChild(s);
    } else {
        fetchRPData(wrapper);
    }
};

function fetchRPData(wrapper) {
    frappe.call({
        method: 'one_fm.one_fm.page.route_planner.route_planner.get_route_planner_data',
        callback: function (r) {
            if (!r.message || r.message.status === 'error') {
                frappe.msgprint(r.message ? r.message.message : 'Failed to load data');
                return;
            }
            mountRoutePlannerApp(wrapper, r.message);
        }
    });
}

// ── Vue App ───────────────────────────────────────────────────────────────────

function mountRoutePlannerApp(wrapper, data) {
    injectRPVueTemplate();
    injectRPStyles();
    $(wrapper).html('<div id="rp-app"></div>');

    Vue.createApp({
        template: '#rp-vue-template',

        // ── State ──────────────────────────────────────────────────────────
        data() {
            const planStart = new Date(data.global_start);
            const planEnd = new Date(data.global_end);

            // Smart initial zoom: show a ~10h working-hours window
            // centred on the shift activity (05:00 – 15:00 local time)
            const kw = s => {
                const d = new Date(s);
                return new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Kuwait' }));
            };
            const kwNow = kw(planStart);
            // Build 05:00 and 15:00 today in Kuwait, then convert back to UTC
            const base = new Date(planStart);
            // offset from plan start to 05:00 Kuwait
            const h05utc = new Date(planStart.getTime() + (5 * 3600000) + (6 * 3600000)); // planStart is midnight-6h local → +11h = 05:00 local
            const h15utc = new Date(h05utc.getTime() + (10 * 3600000)); // +10h = 15:00 local
            const initStart = new Date(Math.max(planStart.getTime(), h05utc.getTime() - 3600000));
            const initEnd = new Date(Math.min(planEnd.getTime(), h15utc.getTime() + 3600000));

            return {
                planData: data,
                // swimItems: { id, cardId, vehicleId, direction, start, end, headcount, conflict }
                swimItems: [],
                assignedCards: new Set(),   // reactive Set<cardId>
                windowStart: initStart,
                windowEnd: initEnd,
                planStart,
                planEnd,
                svgWidth: 800,         // updated by ResizeObserver
                rowHeight: 100,
                selectedItem: null,        // highlighted swim block
                draggingCard: null,        // card being dragged from pool
                isDraggingBlock: false,       // block being moved on lane
                searchQuery: '',
                collapsedGroups: {},          // { [accommodation]: boolean }
                canSave: false,

                // ── Plan management ──
                currentPlan: null,        // { name, title, status, effective_from, effective_until }
                planList: [],           // all available plans
                planLoading: false,
            };
        },

        // ── Computed ───────────────────────────────────────────────────────
        computed: {
            windowDurationMs() {
                return this.windowEnd - this.windowStart;
            },

            filteredPoolCards() {
                const q = this.searchQuery.toLowerCase().trim();
                return this.planData.shipment_cards.filter(c => {
                    // Fully assigned = both outbound AND return placed
                    if (this.isFullyAssigned(c.id)) return false;
                    if (!q) return true;
                    return (
                        c.shift_name.toLowerCase().includes(q) ||
                        c.site_location.toLowerCase().includes(q) ||
                        c.accommodation.toLowerCase().includes(q) ||
                        c.stop_location.toLowerCase().includes(q)
                    );
                });
            },

            poolGroups() {
                const map = {};
                this.filteredPoolCards.forEach(c => {
                    if (!map[c.accommodation]) map[c.accommodation] = [];
                    map[c.accommodation].push(c);
                });
                return Object.entries(map).map(([acc, cards]) => ({ acc, cards }));
            },

            axisTicks() {
                // Adaptive tick step based on zoom level
                const durationH = this.windowDurationMs / 3600000;
                let stepMs, labelEvery;
                if (durationH <= 4) {
                    stepMs = 15 * 60 * 1000;   // 15 min ticks
                    labelEvery = 1;             // label every tick
                } else if (durationH <= 10) {
                    stepMs = 30 * 60 * 1000;   // 30 min ticks
                    labelEvery = 1;             // label every tick
                } else if (durationH <= 18) {
                    stepMs = 30 * 60 * 1000;   // 30 min ticks
                    labelEvery = 2;             // label every hour
                } else {
                    stepMs = 60 * 60 * 1000;   // 1 h ticks
                    labelEvery = 1;             // label every tick
                }

                const origin = new Date(Math.ceil(this.windowStart.getTime() / stepMs) * stepMs);
                const ticks = [];
                let t = new Date(origin);
                let idx = 0;
                while (t <= this.windowEnd) {
                    const x = this.timeToX(t);
                    if (x >= -1 && x <= this.svgWidth + 1) {
                        const isMajor = t.getMinutes() === 0;
                        const showLabel = (idx % labelEvery === 0);
                        ticks.push({
                            key: t.getTime(),
                            x,
                            isMajor,
                            label: showLabel ? this.fmtTime(t) : null
                        });
                    }
                    t = new Date(t.getTime() + stepMs);
                    idx++;
                }
                return ticks;
            },

            itemsByVehicle() {
                const map = {};
                this.planData.vehicles.forEach(v => { map[v.id] = []; });
                this.swimItems.forEach(item => {
                    if (map[item.vehicleId] !== undefined) map[item.vehicleId].push(item);
                });

                // ── Google Calendar-style overlap layout ──
                // For each vehicle, compute column positions so overlapping
                // blocks display side-by-side instead of on top of each other.
                Object.keys(map).forEach(vid => {
                    const items = map[vid];
                    if (items.length <= 1) {
                        items.forEach(i => { i._col = 0; i._totalCols = 1; });
                        return;
                    }

                    // Sort by start time, then by end time descending
                    items.sort((a, b) => {
                        const d = new Date(a.start) - new Date(b.start);
                        return d !== 0 ? d : new Date(b.end) - new Date(a.end);
                    });

                    // Assign columns using a greedy interval packing algorithm
                    const columns = []; // each column is an array of items
                    items.forEach(item => {
                        const iS = new Date(item.start).getTime();
                        // Find first column where item doesn't overlap
                        let placed = false;
                        for (let c = 0; c < columns.length; c++) {
                            const lastInCol = columns[c][columns[c].length - 1];
                            if (new Date(lastInCol.end).getTime() <= iS) {
                                columns[c].push(item);
                                item._col = c;
                                placed = true;
                                break;
                            }
                        }
                        if (!placed) {
                            item._col = columns.length;
                            columns.push([item]);
                        }
                    });

                    // For each overlap cluster, set _totalCols to the max columns
                    // needed within that cluster (not the global max)
                    // Use a sweep to find connected overlap groups
                    const groups = [];
                    let group = [items[0]];
                    let groupEnd = new Date(items[0].end).getTime();

                    for (let i = 1; i < items.length; i++) {
                        const iS = new Date(items[i].start).getTime();
                        if (iS < groupEnd) {
                            // Overlaps with current group
                            group.push(items[i]);
                            groupEnd = Math.max(groupEnd, new Date(items[i].end).getTime());
                        } else {
                            groups.push(group);
                            group = [items[i]];
                            groupEnd = new Date(items[i].end).getTime();
                        }
                    }
                    groups.push(group);

                    // Set _totalCols per group
                    groups.forEach(g => {
                        const maxCol = Math.max(...g.map(i => i._col)) + 1;
                        g.forEach(i => { i._totalCols = maxCol; });
                    });
                });

                return map;
            },

            selectedCard() {
                if (!this.selectedItem) return null;
                return this.planData.shipment_cards.find(c => c.id === this.selectedItem.cardId) || null;
            },
        },

        // ── Methods ────────────────────────────────────────────────────────
        methods: {

            // ─ Time helpers ────────────────────────────────────────────────

            timeToX(t) {
                return Math.round((new Date(t) - this.windowStart) / this.windowDurationMs * this.svgWidth);
            },

            xToTime(x) {
                return new Date(this.windowStart.getTime() + (x / this.svgWidth) * this.windowDurationMs);
            },

            fmtTime(t) {
                return new Date(t).toLocaleTimeString('en-GB', {
                    hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kuwait'
                });
            },

            fmtISO(iso) {
                if (!iso) return '—';
                return this.fmtTime(new Date(iso));
            },

            fmtDate(d) {
                return frappe.datetime.str_to_user(d);
            },

            durMin(item) {
                return Math.round((new Date(item.end) - new Date(item.start)) / 60000);
            },

            // ─ Zoom / Pan ──────────────────────────────────────────────────

            zoomIn() {
                const c = (this.windowStart.getTime() + this.windowEnd.getTime()) / 2;
                const h = this.windowDurationMs * 0.25;
                this.windowStart = new Date(c - h);
                this.windowEnd = new Date(c + h);
            },

            zoomOut() {
                const c = (this.windowStart.getTime() + this.windowEnd.getTime()) / 2;
                const maxH = (this.planEnd - this.planStart) / 2;
                const h = Math.min(maxH, this.windowDurationMs * 0.75);
                this.windowStart = new Date(Math.max(this.planStart.getTime(), c - h));
                this.windowEnd = new Date(Math.min(this.planEnd.getTime(), c + h));
            },

            fitAll() {
                this.windowStart = new Date(this.planStart);
                this.windowEnd = new Date(this.planEnd);
            },

            onSvgWheel(e) {
                e.preventDefault();
                if (e.ctrlKey || e.metaKey) {
                    // ── Zoom to cursor position ──
                    const rect = e.currentTarget.getBoundingClientRect();
                    const x = Math.max(0, Math.min(this.svgWidth, e.clientX - rect.left));
                    const pivot = this.xToTime(x);
                    const factor = e.deltaY > 0 ? 1.4 : 0.714;
                    const minDur = 30 * 60 * 1000;
                    const maxDur = this.planEnd - this.planStart;
                    const newDur = Math.min(maxDur, Math.max(minDur, this.windowDurationMs * factor));
                    const ratio = x / this.svgWidth;
                    const newS = pivot.getTime() - ratio * newDur;
                    this.windowStart = new Date(Math.max(this.planStart.getTime(), newS));
                    this.windowEnd = new Date(Math.min(this.planEnd.getTime(), this.windowStart.getTime() + newDur));
                } else {
                    // ── Pan ──
                    const delta = (e.deltaX || e.deltaY) / this.svgWidth * this.windowDurationMs;
                    const newS = this.windowStart.getTime() + delta;
                    const newE = this.windowEnd.getTime() + delta;
                    if (newS >= this.planStart.getTime() && newE <= this.planEnd.getTime()) {
                        this.windowStart = new Date(newS);
                        this.windowEnd = new Date(newE);
                    }
                }
            },

            // ─ Pool ────────────────────────────────────────────────────────

            toggleGroup(acc) {
                this.collapsedGroups[acc] = !this.collapsedGroups[acc];
            },

            // ─ Card drag (pool → lane) ──────────────────────────────────────

            onCardDragStart(e, card) {
                this.draggingCard = card;
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', card.id);
            },

            onCardDragEnd() {
                setTimeout(() => { this.draggingCard = null; }, 150);
            },

            // ─ Lane drop ───────────────────────────────────────────────────

            onLaneDragOver(e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
            },

            onLaneDrop(e, vehicle) {
                e.preventDefault();
                const card = this.draggingCard;
                this.draggingCard = null;
                if (!card) return;
                const rect = e.currentTarget.getBoundingClientRect();
                const x = Math.max(0, e.clientX - rect.left);
                const dropTime = this.xToTime(x);
                this.handleDrop(card, vehicle, dropTime);
            },

            handleDrop(card, vehicle, dropTime) {
                // ── Seat capacity check (time-aware) ──
                const peakLoad = this.peakLoadDuringCardWindows(card, vehicle.id);

                if (peakLoad + card.headcount > vehicle.seats) {
                    frappe.show_alert({
                        message: `Not enough seats — ${vehicle.seats - peakLoad} available on ${vehicle.label} during peak`,
                        indicator: 'red'
                    });
                    return;
                }

                // ── Trip chaining: detect nearby outbound blocks from same accommodation ──
                // Only consider blocks within ±2 hours of this card's outbound window
                const cardOutStart = new Date(card.outbound_window_start).getTime();
                const cardOutEnd   = new Date(card.outbound_window_end).getTime();
                const PROXIMITY_MS = 2 * 60 * 60 * 1000; // 2 hours

                const nearbyOutbound = this.swimItems.filter(i => {
                    if (i.vehicleId !== vehicle.id || i.direction !== 'OUTBOUND') return false;
                    const existingCard = this.planData.shipment_cards.find(c => c.id === i.cardId);
                    if (!existingCard || existingCard.accommodation !== card.accommodation) return false;
                    // Time proximity check — block must be within 2h of this card's window
                    const blockEnd = new Date(i.end).getTime();
                    const blockStart = new Date(i.start).getTime();
                    return blockEnd > (cardOutStart - PROXIMITY_MS) && blockStart < (cardOutEnd + PROXIMITY_MS);
                });

                if (nearbyOutbound.length > 0) {
                    const existingSites = nearbyOutbound.map(i => {
                        const c = this.planData.shipment_cards.find(sc => sc.id === i.cardId);
                        return c ? c.site_location : i.cardId;
                    });

                    frappe.confirm(
                        `<strong>${vehicle.label}</strong> already picks up from <strong>${card.accommodation}</strong> and drops at:<br><br>` +
                        existingSites.map((s, i) => `&nbsp;&nbsp;${i + 1}. ${s}`).join('<br>') +
                        `<br><br>Add <strong>${card.site_location}</strong> as the next stop on this trip?`,
                        () => this._chainToTrip(card, nearbyOutbound, vehicle.id),
                        // "No" → place as a fresh independent card (full direction picker)
                        () => this._doPlaceWithDialog(card, vehicle.id)
                    );
                    return;
                }

                this.placeCard(card, vehicle.id, dropTime);
            },

            // Fresh placement dialog — bypasses "already placed" direction check
            _doPlaceWithDialog(card, vehicleId) {
                const self = this;
                const d = new frappe.ui.Dialog({
                    title: `New Trip — ${card.site_location}`,
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
                                <strong>${card.shift_name}</strong><br>
                                ${card.headcount} employee(s) · Shift ${self.fmtISO(card.shift_start)} – ${self.fmtISO(card.shift_end)}</p>`
                        },
                        {
                            fieldtype: 'Select', fieldname: 'direction',
                            label: 'Trip Direction', reqd: 1,
                            options: 'Both (Outbound + Return)\nOutbound Only (→ To Site)\nReturn Only (← From Site)',
                            default: 'Outbound Only (→ To Site)'
                        },
                        {
                            fieldtype: 'Column Break'
                        },
                        {
                            fieldtype: 'Int', fieldname: 'duration_min',
                            label: 'Trip Duration (minutes)', default: 60, reqd: 1
                        }
                    ],
                    primary_action_label: 'Place on Timeline',
                    primary_action(vals) {
                        d.hide();
                        const durMs = (vals.duration_min || 60) * 60000;
                        const choice = vals.direction;
                        const placeOut = choice.startsWith('Both') || choice.startsWith('Outbound');
                        const placeRet = choice.startsWith('Both') || choice.startsWith('Return');
                        self._doPlace(card, vehicleId, durMs, placeOut, placeRet);
                    }
                });
                d.show();
            },

            // ── Chain a card as the next stop on an existing trip ──
            _chainToTrip(newCard, existingItems, vehicleId) {
                const self = this;

                // Find or create trip ID
                let tripId = existingItems.find(i => i.tripId)?.tripId;
                if (!tripId) {
                    tripId = `TRIP_${vehicleId}_${Math.random().toString(36).slice(2, 8)}`;
                    existingItems
                        .sort((a, b) => new Date(a.start) - new Date(b.start))
                        .forEach((item, idx) => {
                            item.tripId = tripId;
                            item.stopIndex = idx + 1;
                        });
                }

                // Find the last stop name for context
                const lastItem = existingItems
                    .sort((a, b) => new Date(a.end) - new Date(b.end))
                    .slice(-1)[0];
                const lastCard = this.planData.shipment_cards.find(c => c.id === lastItem.cardId);
                const lastSiteName = lastCard ? lastCard.site_location : 'previous stop';

                const d = new frappe.ui.Dialog({
                    title: `Transit to ${newCard.site_location}`,
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
                                How long from <strong>${lastSiteName}</strong>
                                to <strong>${newCard.site_location}</strong>?</p>`
                        },
                        {
                            fieldtype: 'Int', fieldname: 'transit_min',
                            label: 'Transit + Drop-off Time (minutes)',
                            default: 30, reqd: 1
                        }
                    ],
                    primary_action_label: 'Add Stop',
                    primary_action(vals) {
                        d.hide();
                        const transitMs = (vals.transit_min || 30) * 60000;

                        const lastEnd = new Date(Math.max(
                            ...existingItems.map(i => new Date(i.end).getTime())
                        ));
                        const totalStops = self.swimItems.filter(i => i.tripId === tripId).length;

                        const segStart = new Date(lastEnd.getTime());
                        const segEnd = new Date(segStart.getTime() + transitMs);
                        const uid = Math.random().toString(36).slice(2, 10);

                        self.swimItems.push({
                            id: `${newCard.id}_OUT_${uid}`, cardId: newCard.id, vehicleId,
                            direction: 'OUTBOUND', start: segStart, end: segEnd,
                            headcount: newCard.headcount, conflict: false,
                            tripId, stopIndex: totalStops + 1
                        });

                        // Update totalStops on all trip items
                        const allTrip = self.swimItems.filter(i => i.tripId === tripId);
                        allTrip.forEach(i => { i.totalStops = allTrip.length; });

                        self.assignedCards.add(newCard.id);
                        self.checkConflicts();
                        self.canSave = self.assignedCards.size > 0;
                        self.persistAssignments();

                        frappe.show_alert({
                            message: `Stop ${totalStops + 1}: ${newCard.site_location} (${vals.transit_min}min transit)`,
                            indicator: 'green'
                        }, 4);
                    }
                });
                d.show();
            },

            // ── Time-aware peak load helper ─────────────────────────────────
            // Returns the maximum simultaneous headcount on a vehicle during
            // the new card's outbound or return windows.
            peakLoadDuringCardWindows(card, vehicleId) {
                const DEF = 3600000;
                const outEnd = new Date(card.outbound_window_end).getTime();
                const outStart = outEnd - DEF;
                const retStart = new Date(card.return_window_start).getTime();
                const retEnd = retStart + DEF;

                const vItems = this.swimItems.filter(i => i.vehicleId === vehicleId);

                const loadDuring = (wS, wE) => {
                    return vItems
                        .filter(i => {
                            const iS = new Date(i.start).getTime();
                            const iE = new Date(i.end).getTime();
                            return iS < wE && iE > wS;  // overlaps
                        })
                        .reduce((sum, i) => sum + (i.headcount || 0), 0);
                };

                return Math.max(loadDuring(outStart, outEnd), loadDuring(retStart, retEnd));
            },

            // ─ Place card + direction picker ─────────────────────────────

            // Check which directions are already on the timeline for a card
            placedDirections(cardId) {
                const dirs = new Set();
                this.swimItems.forEach(i => {
                    if (i.cardId === cardId) dirs.add(i.direction);
                });
                return dirs;
            },

            isFullyAssigned(cardId) {
                const dirs = this.placedDirections(cardId);
                return dirs.has('OUTBOUND') && dirs.has('RETURN');
            },

            cardAssignmentLabel(cardId) {
                const dirs = this.placedDirections(cardId);
                if (dirs.has('OUTBOUND') && !dirs.has('RETURN')) return '→ Outbound placed';
                if (dirs.has('RETURN') && !dirs.has('OUTBOUND')) return '← Return placed';
                return null;
            },

            placeCard(card, vehicleId, dropTime) {
                const self = this;
                const placed = this.placedDirections(card.id);
                const hasOut = placed.has('OUTBOUND');
                const hasRet = placed.has('RETURN');

                // If card already has one direction, auto-place the missing one
                if (hasOut && !hasRet) {
                    // Only return is needed — skip dialog
                    const d = new frappe.ui.Dialog({
                        title: `Assign Return — ${card.site_location}`,
                        fields: [
                            {
                                fieldtype: 'HTML',
                                options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
                                    Outbound (→) already placed. Assign <strong>Return (←)</strong> to
                                    <strong>${self.vehicleLabelForItem({ vehicleId })}</strong>.</p>`
                            },
                            { fieldtype: 'Int', fieldname: 'duration_min', label: 'Return Duration (minutes)', default: 60, reqd: 1 }
                        ],
                        primary_action_label: 'Place Return',
                        primary_action(vals) {
                            d.hide();
                            self._doPlace(card, vehicleId, (vals.duration_min || 60) * 60000, false, true);
                        }
                    });
                    d.show();
                    return;
                }
                if (hasRet && !hasOut) {
                    const d = new frappe.ui.Dialog({
                        title: `Assign Outbound — ${card.site_location}`,
                        fields: [
                            {
                                fieldtype: 'HTML',
                                options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
                                    Return (←) already placed. Assign <strong>Outbound (→)</strong> to
                                    <strong>${self.vehicleLabelForItem({ vehicleId })}</strong>.</p>`
                            },
                            { fieldtype: 'Int', fieldname: 'duration_min', label: 'Outbound Duration (minutes)', default: 60, reqd: 1 }
                        ],
                        primary_action_label: 'Place Outbound',
                        primary_action(vals) {
                            d.hide();
                            self._doPlace(card, vehicleId, (vals.duration_min || 60) * 60000, true, false);
                        }
                    });
                    d.show();
                    return;
                }

                // ── Fresh card — full direction picker ──
                const d = new frappe.ui.Dialog({
                    title: `Assign — ${card.site_location}`,
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
                                <strong>${card.shift_name}</strong><br>
                                ${card.headcount} employee(s) · Shift ${self.fmtISO(card.shift_start)} – ${self.fmtISO(card.shift_end)}</p>`
                        },
                        {
                            fieldtype: 'Select', fieldname: 'direction',
                            label: 'Trip Direction', reqd: 1,
                            options: 'Both (Outbound + Return)\nOutbound Only (→ To Site)\nReturn Only (← From Site)',
                            default: 'Both (Outbound + Return)'
                        },
                        {
                            fieldtype: 'Column Break'
                        },
                        {
                            fieldtype: 'Int', fieldname: 'duration_min',
                            label: 'Trip Duration (minutes)', default: 60, reqd: 1
                        }
                    ],
                    primary_action_label: 'Place on Timeline',
                    primary_action(vals) {
                        d.hide();
                        const durMs = (vals.duration_min || 60) * 60000;
                        const choice = vals.direction;
                        const placeOut = choice.startsWith('Both') || choice.startsWith('Outbound');
                        const placeRet = choice.startsWith('Both') || choice.startsWith('Return');
                        self._doPlace(card, vehicleId, durMs, placeOut, placeRet);
                    }
                });
                d.show();
            },

            _doPlace(card, vehicleId, durMs, placeOutbound, placeReturn) {
                const outEnd = new Date(card.outbound_window_end);
                const outStart = new Date(outEnd.getTime() - durMs);
                const retStart = new Date(card.return_window_start);
                const retEnd = new Date(retStart.getTime() + durMs);
                const uid = Math.random().toString(36).slice(2, 10);

                if (placeOutbound) {
                    this.swimItems.push({
                        id: `${card.id}_OUT_${uid}`, cardId: card.id, vehicleId,
                        direction: 'OUTBOUND', start: outStart, end: outEnd,
                        headcount: card.headcount, conflict: false
                    });
                }
                if (placeReturn) {
                    this.swimItems.push({
                        id: `${card.id}_RET_${uid}`, cardId: card.id, vehicleId,
                        direction: 'RETURN', start: retStart, end: retEnd,
                        headcount: card.headcount, conflict: false
                    });
                }

                this.assignedCards.add(card.id);
                this.checkConflicts();
                this.canSave = this.assignedCards.size > 0;
                this.persistAssignments();

                const dirLabel = (placeOutbound && placeReturn) ? 'Both trips'
                    : placeOutbound ? 'Outbound (→)' : 'Return (←)';
                frappe.show_alert({
                    message: `${dirLabel} placed on ${this.vehicleLabelForItem({ vehicleId })}`,
                    indicator: 'green'
                }, 4);
            },



            checkConflicts() {
                this.swimItems.forEach(i => { i.conflict = false; });
                this.planData.vehicles.forEach(v => {
                    const vi = this.swimItems.filter(i => i.vehicleId === v.id);
                    for (let a = 0; a < vi.length; a++) {
                        for (let b = a + 1; b < vi.length; b++) {
                            const ia = vi[a], ib = vi[b];
                            // Blocks in the same trip chain don't conflict
                            if (ia.tripId && ia.tripId === ib.tripId) continue;
                            const aS = new Date(ia.start).getTime(), aE = new Date(ia.end).getTime();
                            const bS = new Date(ib.start).getTime(), bE = new Date(ib.end).getTime();
                            if (aS < bE && aE > bS) { ia.conflict = true; ib.conflict = true; }
                        }
                    }
                });
            },

            // ─ Block interaction ────────────────────────────────────────────

            onBlockClick(item, e) {
                if (this.isDraggingBlock) return;  // was a drag, ignore
                e.stopPropagation();
                this.selectedItem = (this.selectedItem && this.selectedItem.id === item.id) ? null : item;
            },
            // Drag a block to reposition — horizontal (time) + vertical (cross-lane)
            onBlockMouseDown(e, item) {
                e.stopPropagation();
                const startX = e.clientX;
                const startY = e.clientY;
                const origStart = new Date(item.start).getTime();
                const origEnd = new Date(item.end).getTime();
                const origVehicleId = item.vehicleId;
                let moved = false;
                let targetVehicleId = origVehicleId;

                // Remove any existing lane highlight
                const clearHighlight = () => {
                    document.querySelectorAll('.rp-lane-drop-target').forEach(
                        el => el.classList.remove('rp-lane-drop-target')
                    );
                };

                const onMove = me => {
                    const dx = me.clientX - startX;
                    const dy = me.clientY - startY;
                    if (!moved && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) moved = true;
                    if (!moved) return;
                    this.isDraggingBlock = true;

                    // Horizontal: shift time
                    const deltaMs = (dx / this.svgWidth) * this.windowDurationMs;
                    item.start = new Date(origStart + deltaMs);
                    item.end = new Date(origEnd + deltaMs);

                    // Vertical: detect target lane
                    const el = document.elementFromPoint(me.clientX, me.clientY);
                    if (el) {
                        const laneWrap = el.closest('.rp-lane-svg-wrap');
                        if (laneWrap) {
                            const laneRow = laneWrap.closest('.rp-lane-row');
                            if (laneRow && laneRow.dataset.vehicleId) {
                                targetVehicleId = laneRow.dataset.vehicleId;
                                clearHighlight();
                                if (targetVehicleId !== origVehicleId) {
                                    laneWrap.classList.add('rp-lane-drop-target');
                                }
                            }
                        }
                    }

                    this.checkConflicts();
                };

                const onUp = () => {
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup', onUp);
                    clearHighlight();
                    setTimeout(() => { this.isDraggingBlock = false; }, 60);
                    if (moved) {
                        // If dropped on a different lane, reassign vehicle
                        if (targetVehicleId !== origVehicleId) {
                            const targetVehicle = this.planData.vehicles.find(v => v.id === targetVehicleId);
                            if (targetVehicle) {
                                item.vehicleId = targetVehicleId;
                                frappe.show_alert({
                                    message: `Moved to ${targetVehicle.label}`,
                                    indicator: 'blue'
                                }, 3);
                            }
                        }
                        this.canSave = this.assignedCards.size > 0;
                        this.persistAssignments();
                    }
                };

                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
            },

            closeDetail() { this.selectedItem = null; },

            removeSelectedFromLane() {
                if (!this.selectedItem) return;
                const itemId = this.selectedItem.id;
                const cid = this.selectedItem.cardId;
                const dir = this.selectedItem.direction;

                // Remove only the selected block, not both directions
                this.swimItems = this.swimItems.filter(i => i.id !== itemId);

                // Only fully un-assign the card if no blocks remain for it
                const remaining = this.swimItems.filter(i => i.cardId === cid);
                if (remaining.length === 0) {
                    this.assignedCards.delete(cid);
                }

                this.selectedItem = null;
                this.checkConflicts();
                this.canSave = this.assignedCards.size > 0 || this.swimItems.length > 0;
                this.persistAssignments();

                frappe.show_alert({
                    message: `${dir === 'OUTBOUND' ? 'Outbound (→)' : 'Return (←)'} removed`,
                    indicator: 'orange'
                }, 3);
            },

            reassignSelectedBlock() {
                if (!this.selectedItem) return;
                const item = this.selectedItem;
                const card = this.selectedCard;
                const currentVehicle = this.planData.vehicles.find(v => v.id === item.vehicleId);
                const dirLabel = item.direction === 'OUTBOUND' ? 'Outbound' : 'Return';

                // Build options for the vehicle selector (exclude current vehicle)
                const vehicleOpts = this.planData.vehicles
                    .filter(v => v.id !== item.vehicleId)
                    .map(v => `${v.label} (${v.seats} seats)`);

                if (vehicleOpts.length === 0) {
                    frappe.show_alert({ message: 'No other vehicles available', indicator: 'orange' });
                    return;
                }

                const self = this;
                const d = new frappe.ui.Dialog({
                    title: `Reassign ${dirLabel} — ${card.site_location}`,
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `<p style="margin:0 0 8px;color:#666">
                                Currently on <strong>${currentVehicle ? currentVehicle.label : item.vehicleId}</strong>.
                                Select a new vehicle for the <strong>${dirLabel.toLowerCase()}</strong> trip.</p>`
                        },
                        {
                            fieldtype: 'Select', fieldname: 'target_vehicle',
                            label: 'Move to Vehicle', reqd: 1,
                            options: vehicleOpts.join('\n')
                        }
                    ],
                    primary_action_label: 'Reassign',
                    primary_action(vals) {
                        // Parse vehicle label from selection
                        const label = vals.target_vehicle.split(' (')[0];
                        const targetVehicle = self.planData.vehicles.find(v => v.label === label);
                        if (!targetVehicle) return;

                        // Seat capacity check on target vehicle during this block's time
                        const blockStart = new Date(item.start).getTime();
                        const blockEnd = new Date(item.end).getTime();
                        const existingLoad = self.swimItems
                            .filter(i => i.vehicleId === targetVehicle.id)
                            .filter(i => {
                                const iS = new Date(i.start).getTime();
                                const iE = new Date(i.end).getTime();
                                return iS < blockEnd && iE > blockStart;
                            })
                            .reduce((sum, i) => sum + (i.headcount || 0), 0);

                        if (existingLoad + item.headcount > targetVehicle.seats) {
                            frappe.show_alert({
                                message: `Not enough seats — only ${targetVehicle.seats - existingLoad} available on ${targetVehicle.label} at that time`,
                                indicator: 'red'
                            });
                            return;
                        }

                        // Move the block
                        item.vehicleId = targetVehicle.id;
                        self.checkConflicts();
                        self.canSave = self.assignedCards.size > 0;
                        self.persistAssignments();
                        self.selectedItem = null;
                        d.hide();
                        frappe.show_alert({
                            message: `${dirLabel} moved to ${targetVehicle.label}`,
                            indicator: 'green'
                        });
                    }
                });
                d.show();
            },

            vehicleLabelForItem(item) {
                const v = this.planData.vehicles.find(v => v.id === item.vehicleId);
                return v ? v.label : item.vehicleId;
            },

            // ─ Persistence (save/load to Route Plan DocType) ──────────────

            loadSavedAssignments() {
                this.planLoading = true;
                // First fetch available plans, then load active
                frappe.call({
                    method: 'one_fm.one_fm.page.route_planner.route_planner.get_route_plans',
                    async: true,
                    callback: (r) => {
                        this.planList = r.message || [];
                        // Now load the active plan
                        frappe.call({
                            method: 'one_fm.one_fm.page.route_planner.route_planner.load_assignments',
                            args: { plan_name: '' }, // empty = load active
                            async: true,
                            callback: (r2) => {
                                this.planLoading = false;
                                if (r2.message && r2.message.status === 'ok') {
                                    this._applyLoadedPlan(r2.message);
                                }
                            }
                        });
                    }
                });
            },

            _applyLoadedPlan(msg) {
                const items = msg.swim_items || [];
                const cards = msg.assigned_cards || [];

                this.currentPlan = {
                    name: msg.plan_name,
                    title: msg.plan_title,
                    status: msg.plan_status,
                    effective_from: msg.effective_from,
                    effective_until: msg.effective_until
                };

                // Restore swim items — convert ISO strings to Date
                this.swimItems = items.map(i => ({
                    ...i,
                    start: new Date(i.start),
                    end: new Date(i.end)
                }));

                this.assignedCards = new Set(cards);
                this.checkConflicts();
                this.canSave = this.assignedCards.size > 0;

                if (items.length > 0) {
                    frappe.show_alert({
                        message: `Loaded plan "${msg.plan_title}" — ${items.length} assignments`,
                        indicator: 'blue'
                    }, 4);
                }
            },

            switchPlan(planName) {
                if (!planName) return;
                this.planLoading = true;
                frappe.call({
                    method: 'one_fm.one_fm.page.route_planner.route_planner.load_assignments',
                    args: { plan_name: planName },
                    async: true,
                    callback: (r) => {
                        this.planLoading = false;
                        if (r.message && r.message.status === 'ok') {
                            this._applyLoadedPlan(r.message);
                        } else {
                            // Plan exists but has no assignments yet
                            this.swimItems = [];
                            this.assignedCards = new Set();
                            this.canSave = false;
                            const plan = this.planList.find(p => p.name === planName);
                            if (plan) {
                                this.currentPlan = {
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
            },

            createNewPlan() {
                const self = this;
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
                            method: 'one_fm.one_fm.page.route_planner.route_planner.create_route_plan',
                            args: values,
                            callback: (r) => {
                                if (r.message && r.message.status === 'ok') {
                                    d.hide();
                                    frappe.show_alert({
                                        message: `Plan "${r.message.plan_title}" created`,
                                        indicator: 'green'
                                    }, 4);
                                    self.refreshPlanList(() => {
                                        self.switchPlan(r.message.plan_name);
                                    });
                                }
                            }
                        });
                    }
                });
                d.show();
            },

            refreshPlanList(callback) {
                frappe.call({
                    method: 'one_fm.one_fm.page.route_planner.route_planner.get_route_plans',
                    async: true,
                    callback: (r) => {
                        this.planList = r.message || [];
                        if (callback) callback();
                    }
                });
            },

            savePlan() {
                if (!this.currentPlan) {
                    frappe.show_alert({ message: 'Select or create a plan first', indicator: 'orange' }, 3);
                    return;
                }
                if (this.swimItems.length === 0) {
                    frappe.show_alert({ message: 'No assignments to save', indicator: 'orange' }, 3);
                    return;
                }
                // Immediate save (no debounce) for explicit user action
                const items = this.swimItems.map(i => {
                    const card = this.planData.shipment_cards.find(c => c.id === i.cardId);
                    return {
                        ...i,
                        start: new Date(i.start).toISOString(),
                        end:   new Date(i.end).toISOString(),
                        _site: card ? card.site : '',
                        _shift: card ? card.shift_name : '',
                        _accommodation: card ? card.accommodation : '',
                        _stopLocation: card ? card.stop_location : '',
                    };
                });
                const cards = [...this.assignedCards];
                frappe.call({
                    method: 'one_fm.one_fm.page.route_planner.route_planner.save_assignments',
                    args: {
                        plan_name: this.currentPlan.name,
                        swim_items: JSON.stringify(items),
                        assigned_cards: JSON.stringify(cards)
                    },
                    callback: (r) => {
                        if (r.message && r.message.status === 'ok') {
                            frappe.show_alert({
                                message: `Plan "${this.currentPlan.title}" saved — ${r.message.assignment_count} assignments`,
                                indicator: 'green'
                            }, 4);
                        }
                    }
                });
            },

            persistAssignments() {
                if (!this.currentPlan) return; // no plan selected — skip
                // Debounce: clear any pending save and schedule a new one
                if (this._saveTimer) clearTimeout(this._saveTimer);
                this._saveTimer = setTimeout(() => {
                    // Enrich swim items with card metadata for persistence
                    const items = this.swimItems.map(i => {
                        const card = this.planData.shipment_cards.find(c => c.id === i.cardId);
                        return {
                            ...i,
                            start: new Date(i.start).toISOString(),
                            end: new Date(i.end).toISOString(),
                            _site: card ? card.site : '',
                            _shift: card ? card.shift_name : '',
                            _accommodation: card ? card.accommodation : '',
                            _stopLocation: card ? card.stop_location : '',
                        };
                    });
                    const cards = [...this.assignedCards];

                    frappe.call({
                        method: 'one_fm.one_fm.page.route_planner.route_planner.save_assignments',
                        args: {
                            plan_name: this.currentPlan.name,
                            swim_items: JSON.stringify(items),
                            assigned_cards: JSON.stringify(cards)
                        },
                        async: true,
                        callback: () => { } // silent save
                    });
                }, 500); // 500ms debounce
            },


            bx(item) { return this.timeToX(item.start); },
            bw(item) { return Math.max(8, this.timeToX(item.end) - this.timeToX(item.start)); },

            // Google Calendar-style: y position and height based on overlap columns
            by(item) {
                const pad = 4;
                const cols = item._totalCols || 1;
                const col = item._col || 0;
                const usable = this.rowHeight - pad * 2;
                return pad + col * (usable / cols);
            },
            bh(item) {
                const pad = 4;
                const cols = item._totalCols || 1;
                const usable = this.rowHeight - pad * 2;
                return (usable / cols) - 2; // 2px gap between columns
            },
            // Vertical center of a block (for text positioning)
            bcy(item) {
                return this.by(item) + this.bh(item) / 2;
            },

            bfill(item) {
                if (item.conflict) return '#c62828';
                return item.direction === 'OUTBOUND' ? '#1565c0' : '#e65100';
            },

            bcard(item) {
                return this.planData.shipment_cards.find(c => c.id === item.cardId) || {};
            },

            bsel(item) {
                return !!(this.selectedItem && this.selectedItem.id === item.id);
            },

            // Build connector lines between consecutive trip stops for a vehicle
            tripConnectors(vehicleId) {
                const items = this.swimItems.filter(i => i.vehicleId === vehicleId && i.tripId);
                if (!items.length) return [];

                // Group by tripId
                const trips = {};
                items.forEach(i => {
                    if (!trips[i.tripId]) trips[i.tripId] = [];
                    trips[i.tripId].push(i);
                });

                const connectors = [];
                Object.entries(trips).forEach(([tripId, stops]) => {
                    stops.sort((a, b) => (a.stopIndex || 0) - (b.stopIndex || 0));
                    for (let i = 0; i < stops.length - 1; i++) {
                        const a = stops[i], b = stops[i + 1];
                        const aEnd = this.bx(a) + this.bw(a);
                        const bStart = this.bx(b);
                        const midY = this.by(a) + this.bh(a) / 2;
                        connectors.push({
                            key: `${tripId}_${i}`,
                            x1: aEnd,
                            x2: bStart,
                            y: midY
                        });
                    }
                });
                return connectors;
            },

            // ─ SVG width (ResizeObserver) ───────────────────────────────────

            updateSvgWidth() {
                const el = this.$refs.axisWrap;
                if (el && el.clientWidth > 0) this.svgWidth = el.clientWidth;
            },

            // ─ Manifest generation (ported verbatim from vis version) ───────

            async openManifest() {
                const routeData = this.buildManifestData();

                if (!routeData.response.routes.length) {
                    frappe.show_alert({
                        message: 'No assigned shipments to generate a manifest from.',
                        indicator: 'orange'
                    });
                    return;
                }

                const btn = document.getElementById('rp-save-btn');
                const orig = btn.textContent;
                btn.disabled = true;
                btn.textContent = 'Generating...';

                let tpl;
                try {
                    const res = await fetch('/assets/one_fm/html/route_manifest_template.html');
                    if (!res.ok) throw new Error(`HTTP ${res.status}`);
                    tpl = await res.text();
                } catch (err) {
                    frappe.show_alert({ message: `Template load failed: ${err.message}`, indicator: 'red' }, 8);
                    btn.disabled = false;
                    btn.textContent = orig;
                    return;
                }

                const safeJson = JSON.stringify(routeData).replace(/<\//g, '<\\/');
                // Inject ROUTE_DATA inside the template's existing <body><script>
                const dataLine = 'const ROUTE_DATA = ' + safeJson + ';\n';
                // Use regex to insert after first <script> in <body>
                const finalHtml = tpl.replace(/(<body>[\s\S]*?<script>)/, '$1\n' + dataLine);
                const blob = new Blob([finalHtml], { type: 'text/html' });
                const url = URL.createObjectURL(blob);
                window.open(url, '_blank');
                setTimeout(() => URL.revokeObjectURL(url), 60000);

                btn.disabled = false;
                btn.textContent = orig;
                frappe.show_alert({
                    message: `Manifest opened — ${routeData.response.routes.length} vehicles`,
                    indicator: 'green'
                }, 4);
            },

            buildManifestData() {
                const slug = s => (s || '').replace(/[\s_]+/g, '-').replace(/[^a-zA-Z0-9\-]/g, '');

                const shipments = [], vehiclesList = [], routes = [];
                const shipEmp = {}, shipSite = {}, shipShift = {}, vMeta = {}, cMap = {};
                let si = 0;

                [...this.assignedCards].forEach(cid => {
                    const card = this.planData.shipment_cards.find(c => c.id === cid);
                    if (!card) return;

                    const uid = si;
                    const outLbl = `${slug(card.accommodation)}_${uid}_${slug(card.site_location)}_OUTBOUND`;
                    const retLbl = `${slug(card.accommodation)}_${uid}_${slug(card.site_location)}_RETURN`;
                    const outIdx = si++, retIdx = si++;

                    shipments.push({ label: outLbl, pickups: [{}], deliveries: [{}] });
                    shipments.push({ label: retLbl, pickups: [{}], deliveries: [{}] });

                    shipEmp[outLbl] = shipEmp[retLbl] = card.employees;
                    shipSite[outLbl] = shipSite[retLbl] = card.site_location;
                    shipShift[outLbl] = shipShift[retLbl] = card.shift_name;
                    cMap[cid] = { outLbl, retLbl, outIdx, retIdx };
                });

                this.planData.vehicles.forEach((v, vi) => {
                    vehiclesList.push({ label: v.label, startLocation: null });
                    vMeta[v.label] = {
                        accommodation: v.accommodation, driver: v.driver,
                        seats: v.seats, location: v.accommodation
                    };

                    const vItems = this.swimItems
                        .filter(i => i.vehicleId === v.id)
                        .sort((a, b) => new Date(a.start) - new Date(b.start));
                    if (!vItems.length) return;

                    const visits = [], trans = [];
                    trans.push({ travelDuration: '0s', waitDuration: '0s', travelDistanceMeters: 0 });

                    vItems.forEach((item, idx) => {
                        const info = cMap[item.cardId]; if (!info) return;
                        const sIdx = item.direction === 'OUTBOUND' ? info.outIdx : info.retIdx;
                        const hc = item.headcount || 0;
                        const iS = new Date(item.start).toISOString();
                        const iE = new Date(item.end).toISOString();
                        const dSec = Math.round((new Date(item.end) - new Date(item.start)) / 1000);

                        visits.push({
                            shipmentIndex: sIdx, isPickup: true, startTime: iS,
                            loadDemands: { seats: { amount: String(hc) } }
                        });
                        trans.push({
                            travelDuration: `${dSec}s`, waitDuration: '0s',
                            travelDistanceMeters: Math.round(dSec * 10)
                        });
                        visits.push({
                            shipmentIndex: sIdx, isPickup: false, startTime: iE,
                            loadDemands: { seats: { amount: String(-hc) } }
                        });

                        const nxt = vItems[idx + 1];
                        const gap = nxt ? Math.max(0, new Date(nxt.start) - new Date(item.end)) : 0;
                        trans.push({
                            travelDuration: `${Math.round(gap / 1000)}s`, waitDuration: '0s',
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
                            globalStartTime: this.planData.global_start,
                            globalEndTime: this.planData.global_end
                        }
                    },
                    response: { routes, skippedShipments: [], metrics: { totalCost: 0 } },
                    shipmentEmployees: shipEmp,
                    shipmentSiteLocations: shipSite,
                    shipmentShiftNames: shipShift,
                    vehicleMeta: vMeta
                };
            }
        },

        // ── Lifecycle ──────────────────────────────────────────────────────
        mounted() {
            this.$nextTick(() => {
                this.updateSvgWidth();
                const ro = new ResizeObserver(() => this.updateSvgWidth());
                if (this.$refs.axisWrap) ro.observe(this.$refs.axisWrap);
                this._ro = ro;

                // Load saved assignments from backend
                this.loadSavedAssignments();
            });
        },

        beforeUnmount() {
            if (this._ro) this._ro.disconnect();
        }

    }).mount('#rp-app');
}

// ── Vue Template ──────────────────────────────────────────────────────────────

function injectRPVueTemplate() {
    if (document.getElementById('rp-vue-template')) return;
    const s = document.createElement('script');
    s.type = 'text/x-template';
    s.id = 'rp-vue-template';
    s.textContent = `
<div id="rp-shell">

  <!-- ══ Header ══ -->
  <div id="rp-header">
    <div id="rp-header-left">
      <div id="rp-title">Route Planner</div>
      <div id="rp-plan-selector" style="display:flex;align-items:center;gap:8px;margin-top:4px">
        <select :value="currentPlan ? currentPlan.name : ''"
                @change="switchPlan($event.target.value)"
                style="padding:4px 8px;border:1px solid #d1d5db;border-radius:6px;font-size:13px;background:#fff;min-width:160px">
          <option value="" disabled>Select a plan…</option>
          <option v-for="p in planList" :key="p.name" :value="p.name">
            {{ p.title }} ({{ p.status }})
          </option>
        </select>
        <button class="rp-btn" style="font-size:12px;padding:4px 10px;background:#e8f5e9;color:#2e7d32"
                @click="createNewPlan">+ New Plan</button>
        <span v-if="currentPlan" class="rp-dir-badge"
              :style="currentPlan.status === 'Active' ? 'background:#e8f5e9;color:#2e7d32' : currentPlan.status === 'Draft' ? 'background:#fff3e0;color:#e65100' : 'background:#fafafa;color:#999'">
          {{ currentPlan.status }}
        </span>
        <span v-if="currentPlan && currentPlan.effective_from" style="font-size:11px;color:#888">
          {{ currentPlan.effective_from }}{{ currentPlan.effective_until ? ' → ' + currentPlan.effective_until : ' → ∞' }}
        </span>
        <span v-if="planLoading" style="font-size:11px;color:#999">Loading…</span>
      </div>
    </div>
    <div id="rp-header-right">
      <button id="rp-save-btn" class="rp-btn rp-btn-primary"
              :disabled="!currentPlan"
              @click="savePlan"
              :title="!currentPlan ? 'Create or select a plan first' : ''">
        💾 Save Plan
      </button>
      <button class="rp-btn" style="margin-left:6px" :disabled="!canSave || !currentPlan" @click="openManifest">
        📋 Manifest
      </button>
    </div>
  </div>

  <!-- ══ Body ══ -->
  <div id="rp-body">

    <!-- ── Pool Panel ── -->
    <div id="rp-pool-panel">
      <div id="rp-pool-header">
        <div id="rp-pool-title">Unassigned Shipments</div>
        <div id="rp-pool-count">{{ filteredPoolCards.length }} cards</div>
      </div>
      <div id="rp-pool-search">
        <input v-model="searchQuery" type="text" id="rp-search-input"
               placeholder="Search shift, site, accommodation..." />
      </div>
      <div id="rp-pool-groups">

        <div v-for="group in poolGroups" :key="group.acc" class="rp-pool-group">
          <div class="rp-group-header" @click="toggleGroup(group.acc)">
            <span class="rp-group-label">{{ group.acc }}</span>
            <span class="rp-group-count">{{ group.cards.length }}</span>
            <span class="rp-group-chevron">{{ collapsedGroups[group.acc] ? '\u25b8' : '\u25be' }}</span>
          </div>

          <div v-show="!collapsedGroups[group.acc]" class="rp-group-cards">
            <div v-for="card in group.cards" :key="card.id"
                 class="rp-card"
                 draggable="true"
                 @dragstart="onCardDragStart($event, card)"
                 @dragend="onCardDragEnd">
              <div class="rp-card-header">
                <span class="rp-card-site">{{ card.site_location }}</span>
                <span :class="['rp-card-type', card.type === 'OLM' ? 'rp-tag-olm' : 'rp-tag-osm']">{{ card.type }}</span>
              </div>
              <div v-if="cardAssignmentLabel(card.id)" style="margin-bottom:4px">
                <span style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;background:#e8f5e9;color:#2e7d32">
                  {{ cardAssignmentLabel(card.id) }} — drag to assign other direction
                </span>
              </div>
              <div class="rp-card-shift">{{ card.shift_name }}</div>
              <div class="rp-card-meta">
                <span class="rp-card-meta-item">
                  <span class="rp-meta-icon">&#x1F465;</span>{{ card.headcount }} employees
                </span>
                <span class="rp-card-meta-item">
                  <span class="rp-meta-icon">&#x1F4CD;</span>{{ card.stop_location }}
                </span>
              </div>
              <div class="rp-card-windows">
                <div class="rp-window rp-window-out">
                  <span class="rp-window-label">SHIFT START TIME</span>
                  <span class="rp-window-time">{{ fmtISO(card.shift_start) }}</span>
                </div>
                <div class="rp-window rp-window-ret">
                  <span class="rp-window-label">SHIFT END TIME</span>
                  <span class="rp-window-time">{{ fmtISO(card.shift_end) }}</span>
                </div>
              </div>
              <div class="rp-card-employees">
                <span v-for="e in card.employees.slice(0,3)" :key="e" class="rp-emp-chip">{{ e }}</span>
                <span v-if="card.employees.length > 3" class="rp-emp-chip rp-emp-more">+{{ card.employees.length - 3 }} more</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="poolGroups.length === 0" class="rp-pool-empty">
          <div v-if="assignedCards.size > 0 && filteredPoolCards.length === 0">\u2713 All cards assigned</div>
          <div v-else>No cards match your search</div>
        </div>

      </div>
    </div>

    <!-- ── Timeline Panel ── -->
    <div id="rp-timeline-panel">

      <!-- Toolbar -->
      <div id="rp-timeline-toolbar">
        <div id="rp-timeline-zoom">
          <button class="rp-btn-icon" title="Zoom In"  @click="zoomIn">+</button>
          <button class="rp-btn-icon" title="Zoom Out" @click="zoomOut">&#x2212;</button>
          <button class="rp-btn-icon" title="Fit all"  @click="fitAll">&#x229d; Fit</button>
        </div>
        <div class="rp-tb-hint">
          Drag cards to lanes &nbsp;&middot;&nbsp; Drag blocks to reposition &nbsp;&middot;&nbsp;
          Scroll to pan &nbsp;&middot;&nbsp; Ctrl + Scroll to zoom
        </div>
        <div id="rp-timeline-legend">
          <span class="rp-legend-item rp-legend-out">Outbound</span>
          <span class="rp-legend-item rp-legend-ret">Return</span>
          <span class="rp-legend-item rp-legend-conflict">Conflict</span>
        </div>
      </div>

      <!-- Grid: axis row + scrollable lanes -->
      <div id="rp-grid-container">

        <!-- Sticky time axis -->
        <div id="rp-axis-row">
          <div class="rp-lane-label rp-label-stub"></div>
          <div id="rp-axis-wrap" ref="axisWrap">
            <svg :width="svgWidth" height="44" style="display:block;overflow:visible;">
              <!-- Tick lines -->
              <line v-for="tick in axisTicks" :key="'tl' + tick.key"
                    :x1="tick.x" :x2="tick.x"
                    :y1="tick.isMajor ? 20 : 32" y2="44"
                    :stroke="tick.isMajor ? '#aaa' : '#e0e0e0'" stroke-width="1"/>
              <!-- Hour / half-hour labels -->
              <text v-for="tick in axisTicks.filter(t => t.label)" :key="'lbl' + tick.key"
                    :x="tick.x" y="16"
                    text-anchor="middle"
                    :font-weight="tick.isMajor ? '600' : '400'"
                    :fill="tick.isMajor ? '#444' : '#aaa'"
                    font-size="11" font-family="'Google Sans', Roboto, sans-serif">
                {{ tick.label }}
              </text>
            </svg>
          </div>
        </div>

        <!-- Scrollable vehicle rows -->
        <div id="rp-lanes-area">
          <div v-for="(vehicle, vi) in planData.vehicles" :key="vehicle.id"
               :class="['rp-lane-row', vi % 2 === 1 ? 'rp-lane-alt' : '']"
               :data-vehicle-id="vehicle.id">

            <!-- Vehicle label column -->
            <div class="rp-lane-label">
              <div class="rp-gv-plate">{{ vehicle.label }}</div>
              <div class="rp-gv-meta">{{ vehicle.driver }} &middot; {{ vehicle.seats }} seats</div>
              <div class="rp-gv-acc">{{ vehicle.accommodation }}</div>
            </div>

            <!-- SVG swimlane canvas -->
            <div class="rp-lane-svg-wrap"
                 @dragover="onLaneDragOver"
                 @drop="onLaneDrop($event, vehicle)">
              <svg :width="svgWidth" :height="rowHeight"
                   class="rp-lane-svg"
                   @wheel.prevent="onSvgWheel"
                   @click.self="closeDetail">

                <!-- Vertical grid lines -->
                <line v-for="tick in axisTicks" :key="'g' + tick.key"
                      :x1="tick.x" :x2="tick.x" y1="0" :y2="rowHeight"
                      :stroke="tick.isMajor ? '#ebebeb' : '#f6f6f6'" stroke-width="1"/>

                <!-- Drop target highlight when dragging a card -->
                <rect v-if="draggingCard" x="0" y="0" :width="svgWidth" :height="rowHeight"
                      fill="rgba(249,115,22,0.04)"
                      stroke="#f97316" stroke-width="1.5" stroke-dasharray="6,4"/>

                <!-- ── Trip chain connectors ── -->
                <template v-for="conn in tripConnectors(vehicle.id)" :key="conn.key">
                  <line :x1="conn.x1" :y1="conn.y" :x2="conn.x2" :y2="conn.y"
                        stroke="#7c3aed" stroke-width="2" stroke-dasharray="4,3"
                        style="pointer-events:none"/>
                  <circle :cx="conn.x1" :cy="conn.y" r="3" fill="#7c3aed" style="pointer-events:none"/>
                  <circle :cx="conn.x2" :cy="conn.y" r="3" fill="#7c3aed" style="pointer-events:none"/>
                </template>

                <!-- ── Swim items ── -->
                <g v-for="item in itemsByVehicle[vehicle.id]" :key="item.id"
                   :class="isDraggingBlock && bsel(item) ? 'rp-block-grabbing' : 'rp-block-grab'"
                   @mousedown="onBlockMouseDown($event, item)"
                   @click.stop="onBlockClick(item, $event)">

                  <!-- Drop shadow -->
                  <rect :x="bx(item) + 1" :y="by(item) + 2"
                        :width="bw(item)" :height="bh(item)"
                        fill="rgba(0,0,0,0.10)" rx="5"/>

                  <!-- Block body -->
                  <rect :x="bx(item)" :y="by(item)"
                        :width="bw(item)" :height="bh(item)"
                        :fill="bfill(item)"
                        :stroke="bsel(item) ? '#f97316' : 'transparent'"
                        stroke-width="2.5" rx="5"/>

                  <!-- Line 1: Direction + Stop number (always visible) -->
                  <text v-if="bw(item) >= 18"
                        :x="bx(item) + 6" :y="by(item) + Math.min(15, bh(item) * 0.3)"
                        fill="rgba(255,255,255,0.9)" :font-size="Math.min(10, bh(item) * 0.28)"
                        font-weight="700" dominant-baseline="middle"
                        style="user-select:none;pointer-events:none">
                    {{ item.direction === 'OUTBOUND' ? '\u2192' : '\u2190' }}{{ item.stopIndex > 0 ? ' Stop ' + item.stopIndex : (item.direction === 'OUTBOUND' ? ' To' : ' From') }}
                  </text>

                  <!-- Line 2: Site name -->
                  <text v-if="bw(item) >= 40 && bh(item) >= 30"
                        :x="bx(item) + 6" :y="bcy(item)"
                        fill="white" :font-size="Math.min(11, bh(item) * 0.28)" font-weight="600"
                        dominant-baseline="middle"
                        :textLength="Math.max(0, bw(item) - 14)" lengthAdjust="spacing"
                        style="user-select:none;pointer-events:none;overflow:hidden">
                    {{ bcard(item).site_location }}
                  </text>

                  <!-- Line 3: Time range + Headcount -->
                  <text v-if="bw(item) >= 60 && bh(item) >= 40"
                        :x="bx(item) + 6" :y="by(item) + bh(item) - Math.min(8, bh(item) * 0.15)"
                        fill="rgba(255,255,255,0.7)" :font-size="Math.min(9, bh(item) * 0.22)"
                        dominant-baseline="middle"
                        style="user-select:none;pointer-events:none">
                    {{ fmtTime(item.start) }}-{{ fmtTime(item.end) }} · &#x1F465;{{ item.headcount }}
                  </text>

                  <!-- Resize handle (visual only) -->
                  <rect v-if="bw(item) >= 24"
                        :x="bx(item) + bw(item) - 5" :y="by(item) + 4"
                        width="3" :height="bh(item) - 8"
                        fill="rgba(255,255,255,0.22)" rx="1.5"
                        style="cursor:ew-resize;pointer-events:none"/>
                </g>

              </svg>
            </div>
          </div>

          <!-- Empty vehicles -->
          <div v-if="planData.vehicles.length === 0" class="rp-empty-state">
            No vehicles available for today
          </div>
        </div>

      </div>
    </div>

    <!-- ── Detail Panel (slides in when a block is selected) ── -->
    <div id="rp-detail-panel" :class="{ 'rp-detail-open': selectedItem && selectedCard }">
      <template v-if="selectedItem && selectedCard">
        <div id="rp-detail-header">
          <div id="rp-detail-title">Shipment Details</div>
          <button id="rp-detail-close" @click="closeDetail">&#x2715;</button>
        </div>

        <div id="rp-detail-body">

          <!-- Direction + Vehicle badges -->
          <div class="rp-detail-badges">
            <span :class="['rp-dir-badge', selectedItem.direction === 'OUTBOUND' ? 'rp-dir-out' : 'rp-dir-ret']">
              {{ selectedItem.direction === 'OUTBOUND' ? '\u2192 Outbound' : '\u2190 Return' }}
            </span>
            <span v-if="selectedItem.tripId" class="rp-dir-badge" style="background:#f3e8fd;color:#7c3aed">
              Stop {{ selectedItem.stopIndex || '?' }} of {{ selectedItem.totalStops }}
            </span>
            <span class="rp-dir-badge" style="background:#e3f2fd;color:#1565c0">
              {{ vehicleLabelForItem(selectedItem) }}
            </span>
          </div>

          <!-- Type badge -->
          <div v-if="selectedCard.type === 'OLM'" class="rp-detail-card" style="background:#f3e8fd;border-color:#e0cffc;padding:8px 12px">
            <div style="display:flex;align-items:center;gap:6px">
              <span style="font-size:14px">\ud83d\udccd</span>
              <div>
                <div class="rp-detail-row-label" style="color:#7c3aed;margin:0">Shared Bus Stop</div>
                <div class="rp-detail-row-value">{{ selectedCard.stop_location }}</div>
              </div>
            </div>
          </div>

          <!-- OLM: Per-site route breakdown -->
          <template v-if="selectedCard.type === 'OLM' && selectedCard.sites && selectedCard.sites.length">
            <div class="rp-detail-card" v-for="(s, si) in selectedCard.sites" :key="si"
                 style="border-left:3px solid #7c3aed">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                <span style="font-size:12px;font-weight:700;background:#f3e8fd;color:#7c3aed;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center">{{ si + 1 }}</span>
                <div class="rp-detail-row-value" style="font-weight:600">{{ s.site }}</div>
              </div>
              <div style="font-size:11px;color:#888;margin-left:30px" v-for="sh in s.shifts" :key="sh">
                \u23f0 {{ sh }}
              </div>
            </div>
          </template>

          <!-- OLM accommodation -->
          <div v-if="selectedCard.type === 'OLM'" class="rp-detail-card">
            <div class="rp-detail-row" style="border:none;padding:4px 0">
              <div class="rp-detail-row-icon">\ud83c\udfe0</div>
              <div class="rp-detail-row-content">
                <div class="rp-detail-row-label">Accommodation</div>
                <div class="rp-detail-row-value">{{ selectedCard.accommodation }}</div>
              </div>
            </div>
          </div>

          <!-- DIRECT / OSM: Simple info card -->
          <div v-if="selectedCard.type !== 'OLM'" class="rp-detail-card">
            <div class="rp-detail-row">
              <div class="rp-detail-row-icon">\ud83c\udfe2</div>
              <div class="rp-detail-row-content">
                <div class="rp-detail-row-label">Site</div>
                <div class="rp-detail-row-value">{{ selectedCard.site_location }}</div>
              </div>
            </div>
            <div class="rp-detail-row">
              <div class="rp-detail-row-icon">\u23f0</div>
              <div class="rp-detail-row-content">
                <div class="rp-detail-row-label">Shift</div>
                <div class="rp-detail-row-value">{{ selectedCard.shift_name }}</div>
              </div>
            </div>
            <div class="rp-detail-row">
              <div class="rp-detail-row-icon">\ud83d\udccd</div>
              <div class="rp-detail-row-content">
                <div class="rp-detail-row-label">Stop Location</div>
                <div class="rp-detail-row-value">{{ selectedCard.stop_location }}</div>
              </div>
            </div>
            <div class="rp-detail-row">
              <div class="rp-detail-row-icon">\ud83c\udfe0</div>
              <div class="rp-detail-row-content">
                <div class="rp-detail-row-label">Accommodation</div>
                <div class="rp-detail-row-value">{{ selectedCard.accommodation }}</div>
              </div>
            </div>
          </div>

          <!-- Time card -->
          <div class="rp-detail-card">
            <div class="rp-detail-row-label" style="padding:0 0 6px 0">Time on Lane</div>
            <div class="rp-detail-time-display">
              {{ fmtISO(new Date(selectedItem.start).toISOString()) }}
              <span class="rp-detail-time-arrow">\u2192</span>
              {{ fmtISO(new Date(selectedItem.end).toISOString()) }}
              <span class="rp-detail-time-dur">({{ durMin(selectedItem) }} min)</span>
            </div>

            <div class="rp-detail-shift-pills">
              <div class="rp-detail-pill rp-detail-pill-start">
                <div class="rp-detail-pill-label">Start</div>
                <div class="rp-detail-pill-value">{{ fmtISO(selectedCard.shift_start) }}</div>
              </div>
              <div class="rp-detail-pill rp-detail-pill-end">
                <div class="rp-detail-pill-label">End</div>
                <div class="rp-detail-pill-value">{{ fmtISO(selectedCard.shift_end) }}</div>
              </div>
            </div>
          </div>

          <!-- Employees -->
          <div class="rp-detail-card">
            <div class="rp-detail-row-label" style="padding:0 0 8px 0">\ud83d\udc65 Employees ({{ selectedCard.headcount }})</div>
            <div class="rp-detail-emp-list">
              <span v-for="e in selectedCard.employees" :key="e" class="rp-emp-chip">{{ e }}</span>
            </div>
          </div>

        </div>

        <div id="rp-detail-footer">
          <button class="rp-detail-btn rp-detail-btn-primary" @click="reassignSelectedBlock">
            \ud83d\ude8c Reassign Vehicle
          </button>
          <button class="rp-detail-btn rp-detail-btn-danger" @click="removeSelectedFromLane">
            \u2715 Remove from Lane
          </button>
        </div>
      </template>
    </div>

  </div><!-- /rp-body -->
</div><!-- /rp-shell -->
    `;
    document.body.appendChild(s);
}

// ── Styles ────────────────────────────────────────────────────────────────────

function injectRPLoadingStyles() {
    if (document.getElementById('rp-loading-styles')) return;
    const s = document.createElement('style');
    s.id = 'rp-loading-styles';
    s.textContent = `
        #rp-loading {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; height: 100vh;
            background: #f5f5f5; font-family: 'Google Sans', Roboto, sans-serif; gap: 16px;
        }
        #rp-loading-spinner {
            width: 40px; height: 40px;
            border: 3px solid #e0e0e0; border-top-color: #5e5c5b;
            border-radius: 50%; animation: rp-spin 0.8s linear infinite;
        }
        @keyframes rp-spin { to { transform: rotate(360deg); } }
        #rp-loading-text { font-size: 16px; font-weight: 500; color: #1a1a1a; }
        #rp-loading-sub  { font-size: 13px; color: #888; }
    `;
    document.head.appendChild(s);
}

function injectRPStyles() {
    if (document.getElementById('rp-styles')) return;
    const s = document.createElement('style');
    s.id = 'rp-styles';
    s.textContent = `
        /* ── Reset & Root ── */
        #rp-shell {
            display: flex; flex-direction: column; height: 100vh;
            background: #f4f4f5; font-family: 'Google Sans', Roboto, sans-serif;
            overflow: hidden;
        }

        /* ── Header ── */
        #rp-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 24px; background: #fff;
            border-bottom: 1px solid #e2e2e2;
            box-shadow: 0 1px 4px rgba(0,0,0,.05); flex-shrink: 0;
        }
        #rp-title { font-size: 20px; font-weight: 700; color: #111; }
        #rp-date  { font-size: 12px; color: #999; margin-top: 2px; }

        .rp-btn {
            padding: 8px 20px; border-radius: 20px; border: none;
            font-size: 13px; font-weight: 600; cursor: pointer;
            transition: background .18s, box-shadow .18s, transform .1s;
        }
        .rp-btn-primary { background: #f97316; color: #fff; }
        .rp-btn-primary:hover:not(:disabled) {
            background: #ea6c0a;
            box-shadow: 0 3px 10px rgba(249,115,22,.35);
            transform: translateY(-1px);
        }
        .rp-btn-primary:disabled { background: #d1d1d1; cursor: not-allowed; }
        .rp-btn-danger  { background: #ef4444; color: #fff; width: 100%; border-radius: 8px; }
        .rp-btn-danger:hover { background: #dc2626; }

        /* ── Body ── */
        #rp-body { display: flex; flex: 1; overflow: hidden; }

        /* ── Pool Panel ── */
        #rp-pool-panel {
            width: 300px; min-width: 300px; background: #fff;
            border-right: 1px solid #e2e2e2;
            display: flex; flex-direction: column; overflow: hidden;
        }
        #rp-pool-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 16px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
        }
        #rp-pool-title {
            font-size: 10px; font-weight: 800; text-transform: uppercase;
            letter-spacing: .10em; color: #999;
        }
        #rp-pool-count { font-size: 11px; color: #ccc; }
        #rp-pool-search { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }
        #rp-search-input {
            width: 100%; padding: 7px 12px;
            border: 1px solid #e2e2e2; border-radius: 8px;
            font-size: 13px; outline: none;
            transition: border-color .2s; box-sizing: border-box;
        }
        #rp-search-input:focus { border-color: #f97316; }
        #rp-pool-groups { flex: 1; overflow-y: auto; padding: 4px 0; }
        .rp-pool-empty  { padding: 36px 16px; text-align: center; font-size: 13px; color: #ccc; }

        /* Pool groups */
        .rp-pool-group  { }
        .rp-group-header {
            display: flex; align-items: center; padding: 8px 14px;
            cursor: pointer; user-select: none;
            background: #fafafa;
            border-top: 1px solid #f0f0f0; border-bottom: 1px solid #f0f0f0;
            transition: background .14s;
        }
        .rp-group-header:hover { background: #f3f3f3; }
        .rp-group-label   { flex: 1; font-size: 12px; font-weight: 700; color: #333; }
        .rp-group-count   { font-size: 10px; color: #ccc; margin-right: 6px; }
        .rp-group-chevron { font-size: 11px; color: #ccc; }
        .rp-group-cards   {
            display: flex; flex-direction: column; gap: 8px; padding: 8px 10px;
        }

        /* Cards */
        .rp-card {
            background: #fff; border: 1px solid #ebebeb; border-radius: 12px;
            padding: 11px 12px; cursor: grab;
            transition: box-shadow .18s, transform .14s, border-color .18s;
            box-shadow: 0 1px 3px rgba(0,0,0,.04);
        }
        .rp-card:hover  {
            box-shadow: 0 5px 16px rgba(0,0,0,.10);
            transform: translateY(-1px);
            border-color: #d8d8d8;
        }
        .rp-card:active { cursor: grabbing; }
        .rp-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
        .rp-card-site   { font-size: 13px; font-weight: 700; color: #111; }
        .rp-card-type   { font-size: 9px; font-weight: 700; letter-spacing: .06em; padding: 2px 7px; border-radius: 4px; }
        .rp-tag-osm     { background: #e8f4fd; color: #1a73e8; }
        .rp-tag-olm     { background: #f3e8fd; color: #7c3aed; }
        .rp-card-shift  { font-size: 11px; color: #aaa; margin-bottom: 7px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .rp-card-meta   { display: flex; flex-direction: column; gap: 2px; margin-bottom: 8px; }
        .rp-card-meta-item { font-size: 11px; color: #666; display: flex; align-items: center; gap: 5px; }
        .rp-meta-icon   { font-size: 11px; }
        .rp-card-windows{ display: flex; gap: 5px; margin-bottom: 8px; }
        .rp-window      { flex: 1; border-radius: 6px; padding: 4px 8px; }
        .rp-window-out  { background: #e8f5e9; }
        .rp-window-ret  { background: #fff3e0; }
        .rp-window-label{ display: block; font-size: 8px; font-weight: 800; letter-spacing: .08em; color: #888; }
        .rp-window-time { display: block; font-size: 10px; font-weight: 600; color: #333; }
        .rp-card-employees { display: flex; flex-wrap: wrap; gap: 3px; }
        .rp-emp-chip    { font-size: 10px; background: #f5f5f5; border: 1px solid #ebebeb; border-radius: 4px; padding: 2px 6px; color: #666; }
        .rp-emp-more    { background: #eee; color: #aaa; }

        /* ── Timeline Panel ── */
        #rp-timeline-panel {
            flex: 1; display: flex; flex-direction: column;
            overflow: hidden; min-width: 0;
        }
        #rp-timeline-toolbar {
            display: flex; align-items: center; justify-content: space-between;
            padding: 8px 14px; background: #fff;
            border-bottom: 1px solid #e2e2e2; flex-shrink: 0; gap: 12px;
        }
        #rp-timeline-zoom { display: flex; gap: 4px; }
        .rp-btn-icon {
            padding: 4px 12px; border: 1px solid #e2e2e2; border-radius: 6px;
            background: #fff; cursor: pointer; font-size: 14px; color: #555;
            transition: background .14s, border-color .14s;
        }
        .rp-btn-icon:hover { background: #f5f5f5; border-color: #ccc; }
        .rp-tb-hint { font-size: 11px; color: #ccc; flex: 1; text-align: center; }
        #rp-timeline-legend { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
        .rp-legend-item     { font-size: 11px; padding: 2px 9px; border-radius: 4px; font-weight: 600; }
        .rp-legend-out      { background: #dbeafe; color: #1565c0; }
        .rp-legend-ret      { background: #ffedd5; color: #c2410c; }
        .rp-legend-conflict { background: #fee2e2; color: #c62828; }

        /* ── Grid ── */
        #rp-grid-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

        /* Sticky axis */
        #rp-axis-row {
            display: flex; align-items: stretch; background: #fff;
            border-bottom: 2px solid #e2e2e2; flex-shrink: 0;
        }
        #rp-axis-wrap { flex: 1; overflow: hidden; min-width: 0; }

        /* Lane label column */
        .rp-lane-label {
            width: 200px; min-width: 200px; flex-shrink: 0;
            padding: 6px 14px; border-right: 1px solid #ebebeb;
            display: flex; flex-direction: column; justify-content: center;
        }
        .rp-label-stub { background: #fafafa; min-height: 44px; }

        /* Scrollable lanes */
        #rp-lanes-area { flex: 1; overflow-y: auto; overflow-x: hidden; }
        .rp-lane-row   {
            display: flex; align-items: stretch;
            border-bottom: 1px solid #f0f0f0;
            transition: background .14s;
        }
        .rp-lane-alt   { background: #fafafa; }
        .rp-lane-row:hover { background: rgba(249,115,22,.015); }
        .rp-lane-drop-target { background: rgba(33,150,243,0.10) !important; outline: 2px dashed #2196f3; outline-offset: -2px; }
        .rp-lane-svg-wrap  { flex: 1; overflow: hidden; min-width: 0; }
        .rp-lane-svg       { display: block; }

        .rp-gv-plate { font-size: 13px; font-weight: 700; color: #111; }
        .rp-gv-meta  { font-size: 11px; color: #888; margin-top: 1px; }
        .rp-gv-acc   { font-size: 10px; color: #ccc; margin-top: 1px; }

        .rp-block-grab     { cursor: grab; }
        .rp-block-grabbing { cursor: grabbing; }
        .rp-empty-state    { padding: 48px; text-align: center; font-size: 14px; color: #ccc; }

        /* ── Detail Panel ── */
        #rp-detail-panel {
            width: 0; min-width: 0; background: #fafafa;
            border-left: 1px solid #e8e8e8;
            display: flex; flex-direction: column;
            transition: width .22s ease, min-width .22s ease;
            overflow: hidden; flex-shrink: 0;
        }
        #rp-detail-panel.rp-detail-open { width: 320px; min-width: 320px; }

        #rp-detail-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px 16px; background: #fff; border-bottom: 1px solid #eee; flex-shrink: 0;
        }
        #rp-detail-title {
            font-size: 12px; font-weight: 700; text-transform: uppercase;
            letter-spacing: .08em; color: #555;
        }
        #rp-detail-close {
            background: none; border: none; cursor: pointer;
            font-size: 15px; color: #bbb; padding: 4px 8px; border-radius: 6px;
            transition: all .14s;
        }
        #rp-detail-close:hover { background: #f0f0f0; color: #333; }
        #rp-detail-body   { flex: 1; overflow-y: auto; padding: 12px; }
        #rp-detail-footer { padding: 12px 16px; background: #fff; border-top: 1px solid #eee; flex-shrink: 0; }

        .rp-detail-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }

        .rp-detail-card {
            background: #fff; border-radius: 10px; padding: 12px 14px;
            margin-bottom: 10px; border: 1px solid #eee;
        }
        .rp-detail-row {
            display: flex; align-items: flex-start; gap: 10px;
            padding: 7px 0; border-bottom: 1px solid #f5f5f5;
        }
        .rp-detail-row:last-child { border-bottom: none; }
        .rp-detail-row-icon { font-size: 16px; width: 24px; text-align: center; flex-shrink: 0; margin-top: 1px; }
        .rp-detail-row-content { flex: 1; min-width: 0; }
        .rp-detail-row-label {
            font-size: 9px; font-weight: 700; text-transform: uppercase;
            letter-spacing: .08em; color: #aaa; margin-bottom: 2px;
        }
        .rp-detail-row-value { font-size: 13px; color: #222; font-weight: 500; word-break: break-word; }

        .rp-detail-time-display { font-size: 14px; font-weight: 600; color: #222; margin-bottom: 10px; }
        .rp-detail-time-arrow { color: #ccc; margin: 0 4px; }
        .rp-detail-time-dur { color: #aaa; font-size: 12px; font-weight: 400; }

        .rp-detail-shift-pills { display: flex; gap: 8px; }
        .rp-detail-pill {
            flex: 1; border-radius: 8px; padding: 8px 10px; text-align: center;
        }
        .rp-detail-pill-start { background: #e8f5e9; }
        .rp-detail-pill-end   { background: #fff3e0; }
        .rp-detail-pill-label { font-size: 9px; font-weight: 700; letter-spacing: .06em; color: #888; text-transform: uppercase; }
        .rp-detail-pill-value { font-size: 13px; font-weight: 600; color: #333; margin-top: 2px; }

        .rp-detail-emp-list { display: flex; flex-wrap: wrap; gap: 5px; }

        .rp-detail-btn-row { display: flex; gap: 6px; margin-bottom: 8px; }
        .rp-detail-btn {
            display: block; width: 100%; padding: 9px 0; border: none; border-radius: 8px;
            font-size: 12px; font-weight: 600; cursor: pointer; transition: all .14s;
            text-align: center; margin-bottom: 6px;
        }
        .rp-detail-btn:last-child { margin-bottom: 0; }
        .rp-detail-btn-row .rp-detail-btn { flex: 1; margin-bottom: 0; }
        .rp-detail-btn-neutral  { background: #f0f0f0; color: #444; }
        .rp-detail-btn-neutral:hover { background: #e4e4e4; }
        .rp-detail-btn-neutral:disabled { opacity: .4; cursor: default; }
        .rp-detail-btn-primary  { background: #1565c0; color: #fff; }
        .rp-detail-btn-primary:hover { background: #0d47a1; }
        .rp-detail-btn-danger   { background: #fff5f5; color: #dc2626; border: 1px solid #fecaca; }
        .rp-detail-btn-danger:hover { background: #fef2f2; }

        .rp-detail-section { margin-bottom: 16px; }
        .rp-detail-label {
            font-size: 9px; font-weight: 800; text-transform: uppercase;
            letter-spacing: .10em; color: #ccc; margin-bottom: 3px;
        }
        .rp-detail-value { font-size: 13px; color: #111; line-height: 1.5; }

        .rp-dir-badge { font-size: 10px; font-weight: 700; padding: 3px 9px; border-radius: 4px; display: inline-block; }
        .rp-dir-out   { background: #dbeafe; color: #1565c0; }
        .rp-dir-ret   { background: #ffedd5; color: #c2410c; }
        .rp-dir-trip  { background: #f3e8fd; color: #7c3aed; }
    `;
    document.head.appendChild(s);
}