frappe.pages['transportation-schedule'].on_page_load = function (wrapper) {
    injectRPLoadingStyles();
    $(wrapper).html(`
        <div id="rp-loading">
            <div id="rp-loading-spinner"></div>
            <div id="rp-loading-text">Loading Transportation Schedule...</div>
            <div id="rp-loading-sub">Fetching vehicles, shifts and employee data</div>
        </div>
    `);

    if (!document.querySelector('#vue3-cdn')) {
        // Load Material Symbols font
        if (!document.querySelector('#material-symbols-css')) {
            const link = document.createElement('link');
            link.id = 'material-symbols-css';
            link.rel = 'stylesheet';
            link.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200';
            document.head.appendChild(link);
        }
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
        method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.get_route_planner_data',
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

            // Smart initial zoom: show working-hours window
            // planStart is midnight-3h local, so +6h = 03:00 local, +20h = 17:00 local
            const h03utc = new Date(planStart.getTime() + (6 * 3600000));
            const h17utc = new Date(h03utc.getTime() + (14 * 3600000));
            const initStart = new Date(Math.max(planStart.getTime(), h03utc.getTime() - 3600000));
            const initEnd = new Date(Math.min(planEnd.getTime(), h17utc.getTime() + 3600000));

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
                rowHeight: 120,
                selectedItem: null,        // highlighted swim block
                draggingCard: null,        // card being dragged from pool
                isDraggingBlock: false,       // block being moved on lane
                selectedPoolCard: null,    // mobile: tap-to-select card for assignment
                searchQuery: '',
                collapsedGroups: {},          // { [accommodation]: boolean }
                canSave: false,
                isGenerating: false,          // shipment generation in progress
                stopDragSourceIndex: null,  // drag-reorder: source stop index
                stopDragOverIndex: null,    // drag-reorder: hovered stop index

                // ── Drag tooltip (5-min snap) ──
                dragTooltip: null,          // { x, y, timeLabel } — floating HH:MM tooltip during block drag

                // ── Multi-stop hover popup ──
                hoverPopup: null,           // { x, y, groups:[{seq, accommodation, pax}] } — stop-sequence pax summary

                // ── Plan management ──
                currentPlan: null,        // { name, title, status, effective_from, effective_until }
                planList: [],           // all available plans
                planLoading: false,

                // ── Theme ──
                isDark: localStorage.getItem('transportation-schedule-theme') === 'dark',
            };
        },

        // ── Computed ───────────────────────────────────────────────────────
        computed: {
            windowDurationMs() {
                return this.windowEnd - this.windowStart;
            },

            // Vehicle ids whose lane is held by an active multi-day lock today —
            // used to grey the lane and warn the dispatcher (TR-8). Only spans of
            // more than one day (lockTo > lockFrom) count as a block-out.
            lockedLaneIds() {
                const todayStr = frappe.datetime.get_today();
                const ids = new Set();
                this.swimItems.forEach(i => {
                    if (!(i.lockFrom && i.lockTo && i.lockTo > i.lockFrom)) return;
                    if (i.lockFrom <= todayStr && todayStr <= i.lockTo) ids.add(i.vehicleId);
                });
                return ids;
            },

            // Vehicle id -> earliest UPCOMING multi-day lock start date. A future
            // reservation is saved but not yet active today, so the lane shows a
            // "reserved from <date>" badge even though the block itself is still
            // hidden (TR-8). Locks active today (lockedLaneIds) take precedence.
            upcomingLockByVehicle() {
                const todayStr = frappe.datetime.get_today();
                const map = {};
                this.swimItems.forEach(i => {
                    if (!(i.lockFrom && i.lockTo && i.lockTo > i.lockFrom)) return;
                    const from = String(i.lockFrom).slice(0, 10);
                    const to = String(i.lockTo).slice(0, 10);
                    if (to < todayStr) return;      // expired
                    if (from <= todayStr) return;   // active today, not "upcoming"
                    if (!map[i.vehicleId] || from < map[i.vehicleId]) map[i.vehicleId] = from;
                });
                return map;
            },

            filteredPoolCards() {
                const q = this.searchQuery.toLowerCase().trim();
                return this.planData.shipment_cards.filter(c => {
                    // Card is assigned when its specific ID is in assignedCards
                    if (this.assignedCards.has(c.id)) return false;
                    if (!q) return true;
                    return (
                        c.shift_name.toLowerCase().includes(q) ||
                        c.site_location.toLowerCase().includes(q) ||
                        c.accommodation.toLowerCase().includes(q) ||
                        c.stop_location.toLowerCase().includes(q) ||
                        (c.direction || '').toLowerCase().includes(q)
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
                // Only render items live today — future-dated placements wait for
                // their start date, lapsed ones drop off (TR-8).
                this.swimItems.forEach(item => {
                    if (!this._liveToday(item)) return;
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

            // Merged view: trip-chained items render as a single visual block
            mergedItemsByVehicle() {
                const raw = this.itemsByVehicle;
                const merged = {};

                Object.keys(raw).forEach(vid => {
                    const items = raw[vid];
                    const entries = [];
                    const tripGroups = {};

                    items.forEach(item => {
                        if (item.tripId) {
                            if (!tripGroups[item.tripId]) tripGroups[item.tripId] = [];
                            tripGroups[item.tripId].push(item);
                        } else {
                            entries.push({
                                type: 'single', item,
                                // Time span for layout calculation
                                _layoutStart: new Date(item.start).getTime(),
                                _layoutEnd: new Date(item.end).getTime(),
                            });
                        }
                    });

                    // Build merged blocks for each trip group
                    Object.keys(tripGroups).forEach(tripId => {
                        const stops = tripGroups[tripId].sort(
                            (a, b) => (a.stopIndex || 0) - (b.stopIndex || 0)
                        );
                        const firstItem = stops[0];
                        const lastItem = stops[stops.length - 1];
                        const totalHC = stops.reduce((sum, s) => sum + (s.headcount || 0), 0);

                        const stopLabels = stops.map(s => {
                            const card = this.planData.shipment_cards.find(c => c.id === s.cardId);
                            return card ? card.site_location : (s._stopLocation || s._site || s.cardId);
                        });

                        entries.push({
                            type: 'merged',
                            tripId,
                            tripName: stops.find(s => s.tripName)?.tripName || null,
                            direction: firstItem.direction,
                            start: firstItem.start,
                            end: lastItem.end,
                            headcount: totalHC,
                            stopLabels,
                            stops,
                            conflict: stops.some(s => s.conflict),
                            overcapacity: stops.some(s => s.overcapacity),
                            primaryItem: firstItem,
                            // Time span for layout calculation
                            _layoutStart: new Date(firstItem.start).getTime(),
                            _layoutEnd: new Date(lastItem.end).getTime(),
                        });
                    });

                    // ── Recalculate overlap columns on merged entries ──
                    if (entries.length <= 1) {
                        entries.forEach(e => { e._col = 0; e._totalCols = 1; });
                    } else {
                        // Sort by start time, then by end time descending
                        entries.sort((a, b) => {
                            const d = a._layoutStart - b._layoutStart;
                            return d !== 0 ? d : b._layoutEnd - a._layoutEnd;
                        });

                        // Greedy column packing
                        const columns = [];
                        entries.forEach(entry => {
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

                        // Sweep to find connected overlap groups
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

                        // Set _totalCols per overlap group
                        groups.forEach(g => {
                            const maxCol = Math.max(...g.map(e => e._col)) + 1;
                            g.forEach(e => { e._totalCols = maxCol; });
                        });
                    }

                    merged[vid] = entries;
                });

                return merged;
            },

            selectedCard() {
                if (!this.selectedItem) return null;
                const found = this.planData.shipment_cards.find(c => c.id === this.selectedItem.cardId);
                if (found) return found;
                // Fallback: build a synthetic card from saved metadata on the swim item
                // This allows the detail panel to open for loaded plans even when
                // the underlying employee/shift data has changed since the plan was saved.
                const item = this.selectedItem;
                if (item._site || item._shift || item._accommodation || item._stopLocation) {
                    // Fuzzy-match: find a current card with same accommodation + stop + direction + shift
                    const fuzzy = this.planData.shipment_cards.find(c =>
                        c.accommodation === item._accommodation &&
                        c.stop_location === item._stopLocation &&
                        c.direction === (item.direction || 'OUTBOUND') &&
                        (!item._shift || c.shift_name === item._shift)
                    );
                    return {
                        id: item.cardId,
                        site: item._site || '',
                        site_location: item._stopLocation || item._site || 'Unknown Site',
                        shift_name: fuzzy ? fuzzy.shift_name : (item._shift || '\u2014'),
                        accommodation: item._accommodation || '\u2014',
                        stop_location: item._stopLocation || '\u2014',
                        headcount: fuzzy ? fuzzy.headcount : (item.headcount || 0),
                        employees: fuzzy ? fuzzy.employees : [],
                        return_employees: fuzzy ? (fuzzy.return_employees || []) : [],
                        direction: item.direction || 'OUTBOUND',
                        shift_start: fuzzy ? fuzzy.shift_start : null,
                        shift_end: fuzzy ? fuzzy.shift_end : null,
                        type: fuzzy ? fuzzy.type : 'LOADED',
                    };
                }
                return null;
            },

            // All stops in the selected trip chain (empty if not a trip)
            selectedTripStops() {
                if (!this.selectedItem || !this.selectedItem.tripId) return [];
                const tripId = this.selectedItem.tripId;
                const self = this;
                return this.swimItems
                    .filter(i => i.tripId === tripId)
                    .sort((a, b) => (a.stopIndex || 0) - (b.stopIndex || 0))
                    .map((item, idx) => {
                        let card = self.planData.shipment_cards.find(c => c.id === item.cardId);
                        if (!card && (item._site || item._shift || item._accommodation || item._stopLocation)) {
                            // Fuzzy-match for trip stops too
                            const fuzzy = self.planData.shipment_cards.find(c =>
                                c.accommodation === item._accommodation &&
                                c.stop_location === item._stopLocation &&
                                c.direction === (item.direction || 'OUTBOUND') &&
                                (!item._shift || c.shift_name === item._shift)
                            );
                            card = {
                                id: item.cardId,
                                site_location: item._stopLocation || item._site || 'Unknown Site',
                                shift_name: fuzzy ? fuzzy.shift_name : (item._shift || '\u2014'),
                                accommodation: item._accommodation || '\u2014',
                                stop_location: item._stopLocation || '\u2014',
                                headcount: fuzzy ? fuzzy.headcount : (item.headcount || 0),
                                employees: fuzzy ? fuzzy.employees : [],
                            };
                        }
                        return { item, card: card || {}, stopNum: idx + 1 };
                    });
            },
            selectedTripStopsByCamp() {
                // Group the trip's stops by their pickup accommodation camp, in the
                // order each camp first appears. The detail panel renders one camp
                // banner followed by only the stops that belong to it, so a chained
                // trip spanning several camps reads camp-by-camp. stopNum is carried
                // through unchanged so drag-reorder still keys off the global index.
                const groups = [];
                const index = {};
                for (const stop of this.selectedTripStops) {
                    const acc = (stop.card && stop.card.accommodation)
                        ? stop.card.accommodation : '—';
                    if (!(acc in index)) {
                        index[acc] = groups.length;
                        groups.push({ accommodation: acc, stops: [] });
                    }
                    groups[index[acc]].stops.push(stop);
                }
                return groups;
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

            /** Round a Date to the nearest 5-minute boundary. */
            snapTo5Min(d) {
                const ms = new Date(d).getTime();
                const FIVE_MIN = 5 * 60 * 1000;
                return new Date(Math.round(ms / FIVE_MIN) * FIVE_MIN);
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

            /** Safe accessor: extract display name from employee (object or legacy string). */
            empName(e) {
                return (typeof e === 'object' && e !== null) ? (e.name || '—') : (e || '—');
            },

            /** Safe accessor: extract mobile from employee object. */
            empMobile(e) {
                return (typeof e === 'object' && e !== null) ? (e.mobile || '') : '';
            },

            /** True when the employee is a Rambo reliever filling in for the shift. */
            empIsReliever(e) {
                return (typeof e === 'object' && e !== null) ? !!e.is_reliever : false;
            },

            /** Count of relievers in an employee list (regulars = length − this). */
            relieverCount(emps) {
                if (!Array.isArray(emps)) return 0;
                return emps.filter(e => this.empIsReliever(e)).length;
            },

            /** Handle click on employee phone icon — tel: on mobile, clipboard on desktop. */
            handleEmployeeCall(e) {
                const name = this.empName(e);
                const mobile = this.empMobile(e);
                if (!mobile) {
                    frappe.show_alert({ message: __('No mobile number on file for ' + name), indicator: 'orange' }, 3);
                    return;
                }
                const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry/i.test(navigator.userAgent);
                if (isMobile) {
                    window.location.href = 'tel:' + mobile;
                } else {
                    navigator.clipboard.writeText(mobile).then(() => {
                        frappe.show_alert({ message: __('Number Copied: ') + mobile, indicator: 'green' }, 3);
                    }).catch(() => {
                        frappe.show_alert({ message: mobile, indicator: 'blue' }, 5);
                    });
                }
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

            show24h() {
                // Show full 24h day: midnight to midnight (Kuwait time = UTC+3)
                const today = new Date(this.planStart);
                // Set to midnight UTC of the plan day, then offset for Kuwait TZ
                const dayStart = new Date(today);
                dayStart.setUTCHours(0, 0, 0, 0);
                // Subtract 3h to get 00:00 Kuwait = 21:00 UTC previous day
                const kwMidnightStart = new Date(dayStart.getTime() - (3 * 3600000));
                const kwMidnightEnd = new Date(kwMidnightStart.getTime() + (24 * 3600000));
                this.windowStart = kwMidnightStart;
                this.windowEnd = kwMidnightEnd;
            },

            showWorkHours() {
                // Snap to 05:00–19:00 Kuwait time (working hours window)
                const today = new Date(this.planStart);
                const dayStart = new Date(today);
                dayStart.setUTCHours(0, 0, 0, 0);
                // 05:00 Kuwait = 02:00 UTC, 19:00 Kuwait = 16:00 UTC
                const workStart = new Date(dayStart.getTime() - (3 * 3600000) + (5 * 3600000));
                const workEnd = new Date(dayStart.getTime() - (3 * 3600000) + (19 * 3600000));
                this.windowStart = workStart;
                this.windowEnd = workEnd;
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

            // ─ Touch/Mobile detection ────────────────────────────────────
            isMobile() {
                return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
            },

            // ─ Card drag (pool → lane) — desktop ─────────────────────────

            onCardDragStart(e, card) {
                this.draggingCard = card;
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', card.id);
            },

            onCardDragEnd() {
                setTimeout(() => { this.draggingCard = null; }, 150);
            },

            // ─ Card tap (pool → lane) — mobile ───────────────────────────

            onCardTap(card) {
                if (!this.isMobile()) return;
                if (this.selectedPoolCard && this.selectedPoolCard.id === card.id) {
                    this.selectedPoolCard = null; // deselect
                } else {
                    this.selectedPoolCard = card;
                    frappe.show_alert({
                        message: `Selected: ${card.site_location} — tap a vehicle lane to assign`,
                        indicator: 'orange'
                    }, 3);
                }
            },

            onLaneTap(e, vehicle) {
                if (!this.selectedPoolCard) return;
                const card = this.selectedPoolCard;
                // Don't clear selection yet — handleDrop may abort (seat check, etc.)
                // Selection is cleared inside handleDrop on successful placement
                this.handleDrop(card, vehicle);
            },

            // ─ Lane drop — desktop ───────────────────────────────────────

            onLaneDragOver(e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
            },

            onLaneDrop(e, vehicle) {
                e.preventDefault();
                const card = this.draggingCard;
                this.draggingCard = null;
                if (!card) return;
                this.handleDrop(card, vehicle);
            },

            // Return the swim item whose multi-day lock holds this vehicle today,
            // ignoring blocks that belong to `excludeCardId`. Only a lock spanning
            // more than one day (lockTo > lockFrom) blocks out the vehicle; a
            // single-day run does not (TR-8).
            vehicleLockToday(vehicleId, excludeCardId) {
                const todayStr = frappe.datetime.get_today();
                return this.swimItems.find(i => {
                    if (i.vehicleId !== vehicleId) return false;
                    if (excludeCardId && i.cardId === excludeCardId) return false;
                    if (!(i.lockFrom && i.lockTo && i.lockTo > i.lockFrom)) return false;
                    return i.lockFrom <= todayStr && todayStr <= i.lockTo;
                }) || null;
            },

            // The [from, to] calendar span a swim item reserves. Items without an
            // explicit lock window are ordinary single-day runs (today..today).
            _lockDateRange(item) {
                const today = frappe.datetime.get_today();
                const from = item.lockFrom ? String(item.lockFrom).slice(0, 10) : today;
                const to = item.lockTo ? String(item.lockTo).slice(0, 10) : from;
                return [from, to];
            },

            // Mirror of the backend block-out check (route_plan.py): a candidate
            // placement spanning [newFrom, newTo] on a vehicle conflicts when it
            // overlaps an existing run's date range and at least one side is a
            // multi-day lock. Expired locks and the card's own rows are ignored.
            // Returns the conflicting swim item, or null. Lets the modal warn
            // before a future-dated overlap would otherwise only fail at save.
            _overlappingLock(vehicleId, newFrom, newTo, excludeCardId) {
                const today = frappe.datetime.get_today();
                const newMulti = newTo > newFrom;
                return this.swimItems.find(i => {
                    if (i.vehicleId !== vehicleId) return false;
                    if (excludeCardId && i.cardId === excludeCardId) return false;
                    const [ef, et] = this._lockDateRange(i);
                    if (et < today) return false;                 // existing lock expired
                    if (!newMulti && !(et > ef)) return false;    // both single-day: normal multi-trip
                    return newFrom <= et && ef <= newTo;          // inclusive date-range overlap
                }) || null;
            },

            handleDrop(card, vehicle) {
                // ── Multi-day vehicle lock (TR-8): reject a drop onto a lane whose
                // vehicle is already held by another shipment's multi-day lock. ──
                const lock = this.vehicleLockToday(vehicle.id, card.id);
                if (lock) {
                    frappe.throw(`Vehicle Locked: ${vehicle.label} is reserved for a multi-day run until ${lock.lockTo}. It cannot take another overlapping shipment.`);
                    return;
                }

                // ── Seat capacity check (time-aware) ──
                const peakLoad = this.peakLoadDuringCardWindows(card, vehicle.id);

                if (peakLoad + card.headcount > vehicle.seats) {
                    const shell = document.getElementById('rp-shell');
                    if (shell) {
                        shell.style.transition = 'background-color 0.2s';
                        shell.style.backgroundColor = '#ffebee';
                        setTimeout(() => { shell.style.backgroundColor = ''; }, 400);
                    }
                    frappe.throw(`Capacity Exceeded: Cannot assign ${card.headcount} employees to a ${vehicle.seats}-seater vehicle.`);
                    return;
                }

                // ── Trip chaining: detect nearby blocks from same accommodation (any direction) ──
                // Mixed-direction trips are valid: OUT drops + RET pickups on the same trip
                const isOutbound = card.direction === 'OUTBOUND';
                const cardWindowStart = new Date(isOutbound ? card.outbound_window_start : card.return_window_start).getTime();
                const cardWindowEnd   = new Date(isOutbound ? card.outbound_window_end   : card.return_window_end).getTime();
                const PROXIMITY_MS = 2 * 60 * 60 * 1000; // 2 hours

                // ── Driver handover overlap (WI-001577) ──
                // Dropping a run onto hours already covered by a submitted Vehicle
                // Handover Log is legitimate — the operational driver simply takes it on
                // — so the dispatcher is warned and the drop proceeds. Deliberately not a
                // frappe.throw: the AC requires a warning that does not block.
                const handover = this.overlapsHandover(vehicle.id, cardWindowStart, cardWindowEnd);
                if (handover) {
                    frappe.show_alert({
                        message: __('{0} is under a handover to {1} ({2}–{3}) during this window. The run was still placed.', [
                            vehicle.label,
                            handover.driver_name,
                            this.fmtTime(handover.start),
                            this.fmtTime(handover.end)
                        ]),
                        indicator: 'orange'
                    }, 8);
                }

                // Multi-camp trips are valid: a single vehicle may pick up from
                // several accommodations on one run (e.g. Mahboula then Mangaf),
                // so proximity — not a shared accommodation — decides chaining.
                const nearbyBlocks = this.swimItems.filter(i => {
                    if (i.vehicleId !== vehicle.id) return false;
                    const existingCard = this.planData.shipment_cards.find(c => c.id === i.cardId);
                    if (!existingCard) return false;
                    const blockEnd = new Date(i.end).getTime();
                    const blockStart = new Date(i.start).getTime();
                    return blockEnd > (cardWindowStart - PROXIMITY_MS) && blockStart < (cardWindowEnd + PROXIMITY_MS);
                });

                if (nearbyBlocks.length > 0) {
                    // Group by tripId (items without tripId are each their own "trip")
                    const tripMap = {};
                    let soloIdx = 0;
                    nearbyBlocks.forEach(item => {
                        const key = item.tripId || `_solo_${soloIdx++}`;
                        if (!tripMap[key]) tripMap[key] = [];
                        tripMap[key].push(item);
                    });
                    const tripKeys = Object.keys(tripMap);

                    if (tripKeys.length === 1) {
                        // ── Single trip: simple confirm ──
                        const existingStops = nearbyBlocks.map(i => {
                            const c = this.planData.shipment_cards.find(sc => sc.id === i.cardId);
                            const siteName = c ? c.site_location : i.cardId;
                            const campName = (c && c.accommodation) ? c.accommodation : '';
                            const dirBadge = i.direction === 'RETURN' ? '← RET' : '→ OUT';
                            return `${campName ? '<strong>' + campName + '</strong> — ' : ''}${siteName} <span style="font-size:11px;color:#888">(${dirBadge})</span>`;
                        });
                        const newDirBadge = card.direction === 'RETURN' ? '← RET' : '→ OUT';
                        const newCamp = card.accommodation ? `<strong>${card.accommodation}</strong> — ` : '';
                        frappe.confirm(
                            `<strong>${vehicle.label}</strong> already has an active trip:<br><br>` +
                            existingStops.map((s, i) => `&nbsp;&nbsp;${i + 1}. ${s}`).join('<br>') +
                            `<br><br>Add ${newCamp}<strong>${card.site_location}</strong> <span style="font-size:11px;color:#888">(${newDirBadge})</span> as the next stop on this trip?`,
                            () => this._chainToTrip(card, tripMap[tripKeys[0]], vehicle.id),
                            () => this._doPlaceWithDialog(card, vehicle.id)
                        );
                    } else {
                        // ── Multiple trips: let user pick which trip to join ──
                        const self = this;
                        const tripOptions = tripKeys.map((key, idx) => {
                            const items = tripMap[key];
                            const sites = items.map(i => {
                                const c = self.planData.shipment_cards.find(sc => sc.id === i.cardId);
                                const siteName = c ? c.site_location : i.cardId;
                                const campName = (c && c.accommodation) ? c.accommodation + ' — ' : '';
                                const dir = i.direction === 'RETURN' ? '←' : '→';
                                return `${dir} ${campName}${siteName}`;
                            });
                            const timeRange = self.fmtTime(items[0].start) + '–' + self.fmtTime(items[items.length - 1].end);
                            const tName = items.find(i => i.tripName)?.tripName;
                            const tripLabel = tName || `Trip ${idx + 1}`;
                            return {
                                key,
                                label: `${tripLabel}: ${sites.join(' → ')} (${timeRange})`,
                                items
                            };
                        });

                        const d = new frappe.ui.Dialog({
                            title: `Add ${card.site_location} to which trip?`,
                            fields: [
                                {
                                    fieldtype: 'HTML',
                                    options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
                                        <strong>${vehicle.label}</strong> has <strong>${tripKeys.length} active trips</strong>.
                                        Choose which trip to add <strong>${card.accommodation ? card.accommodation + ' — ' : ''}${card.site_location}</strong> to:</p>`
                                },
                                {
                                    fieldtype: 'Select', fieldname: 'trip_choice',
                                    label: 'Select Trip', reqd: 1,
                                    options: tripOptions.map(t => t.label).join('\n') + '\nCreate New Independent Trip',
                                    default: tripOptions[0].label
                                },
                                { fieldtype: 'Column Break' },
                                {
                                    fieldtype: 'Int', fieldname: 'transit_min',
                                    label: 'Transit Time (minutes)', default: 30, reqd: 1,
                                    description: 'Only used when adding to an existing trip'
                                }
                            ],
                            primary_action_label: 'Add Stop',
                            primary_action(vals) {
                                d.hide();
                                const choice = vals.trip_choice;

                                if (choice === 'Create New Independent Trip') {
                                    self._doPlaceWithDialog(card, vehicle.id);
                                    return;
                                }

                                // Find selected trip
                                const selected = tripOptions.find(t => t.label === choice);
                                if (selected) {
                                    self._chainToTrip(card, selected.items, vehicle.id, vals.transit_min);
                                }
                            }
                        });
                        d.show();
                    }
                    return;
                }

                this.placeCard(card, vehicle.id);
            },

            // Fresh placement dialog — bypasses "already placed" direction check
            _doPlaceWithDialog(card, vehicleId) {
                const self = this;

                // Build context about existing trips on this vehicle
                const existingOnVehicle = this.swimItems.filter(i => i.vehicleId === vehicleId && i.direction === 'OUTBOUND');
                let existingHtml = '';
                if (existingOnVehicle.length > 0) {
                    // Group by tripId
                    const trips = {};
                    let soloIdx = 0;
                    existingOnVehicle.forEach(item => {
                        const key = item.tripId || `_solo_${soloIdx++}`;
                        if (!trips[key]) trips[key] = [];
                        trips[key].push(item);
                    });

                    const tripSummaries = Object.values(trips).map(stops => {
                        const sites = stops.map(s => {
                            const c = self.planData.shipment_cards.find(sc => sc.id === s.cardId);
                            return c ? c.site_location : s.cardId;
                        });
                        const time = self.fmtTime(stops[0].start) + '–' + self.fmtTime(stops[stops.length - 1].end);
                        return `<span style="display:block;padding:2px 0;font-size:12px;color:#666">• ${sites.join(' → ')} (${time})</span>`;
                    });

                    existingHtml = `<div style="background:#f5f5f5;border-radius:6px;padding:8px 10px;margin:0 0 12px">
                        <div style="font-size:11px;font-weight:600;color:#999;text-transform:uppercase;margin-bottom:4px">
                            Existing trips on this vehicle
                        </div>
                        ${tripSummaries.join('')}
                    </div>`;
                }

                const vehicleLabel = this.planData.vehicles.find(v => v.id === vehicleId)?.label || vehicleId;
                const isOutbound = card.direction === 'OUTBOUND';
                const dirLabel = isOutbound ? 'Outbound (→ To Site)' : 'Return (← From Site)';

                const d = new frappe.ui.Dialog({
                    title: `New Independent Trip — ${card.site_location}`,
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `<p style="margin:0 0 8px;color:#555;font-size:13px">
                                Create a <strong>new separate trip</strong> on <strong>${vehicleLabel}</strong>
                                for <strong>${card.site_location}</strong>.</p>
                                <p style="margin:0 0 12px;color:#555;font-size:12px">
                                <strong>${card.shift_name}</strong><br>
                                ${card.headcount} employee(s) · Shift ${self.fmtISO(card.shift_start)} – ${self.fmtISO(card.shift_end)}<br>
                                Accommodation: ${card.accommodation || '—'}<br>
                                Direction: <strong>${dirLabel}</strong></p>
                                ${existingHtml}`
                        },
                        {
                            fieldtype: 'Data', fieldname: 'trip_name',
                            label: 'Trip Name', reqd: 1,
                            description: 'Auto-generated sequential trip name.',
                            default: self.generateTripName(vehicleId),
                            read_only: 1
                        },
                        { fieldtype: 'Section Break' },
                        {
                            fieldtype: 'Int', fieldname: 'duration_min',
                            label: 'Trip Duration (minutes)', default: 60, reqd: 1
                        },
                        { fieldtype: 'Section Break', label: 'Multi-Day Vehicle Lock' },
                        {
                            fieldtype: 'Datetime', fieldname: 'start_datetime',
                            label: 'Start Date Time',
                            description: 'First day this run holds the vehicle. Defaults to the card\'s From Date (or today).',
                            default: self._defaultLockStart(card)
                        },
                        { fieldtype: 'Column Break' },
                        {
                            fieldtype: 'Datetime', fieldname: 'end_datetime',
                            label: 'End Date Time',
                            description: 'Last day this run holds the vehicle. Leave blank for a continuous (open-ended) run.',
                            default: self._defaultLockEnd(card)
                        }
                    ],
                    primary_action_label: 'Create Trip',
                    primary_action(vals) {
                        const startDt = vals.start_datetime || '';
                        const endDt = vals.end_datetime || '';
                        if (startDt && startDt.slice(0, 10) < frappe.datetime.get_today()) {
                            frappe.throw('Start Date Time cannot be in the past.');
                            return;
                        }
                        if (startDt && endDt && startDt > endDt) {
                            frappe.throw('Start Date Time must be on or before End Date Time.');
                            return;
                        }
                        const newFrom = startDt ? startDt.slice(0, 10) : frappe.datetime.get_today();
                        const newTo = endDt ? endDt.slice(0, 10) : newFrom;
                        const clash = self._overlappingLock(vehicleId, newFrom, newTo, card.id);
                        if (clash) {
                            const [cf, ct] = self._lockDateRange(clash);
                            frappe.throw(`Vehicle Reserved: ${self.vehicleLabelForItem({ vehicleId })} is already locked from ${cf} to ${ct} for an overlapping run. Choose different dates or another vehicle.`);
                            return;
                        }
                        d.hide();
                        const durMs = (vals.duration_min || 60) * 60000;
                        self._doPlace(card, vehicleId, durMs, isOutbound, !isOutbound, 0,
                            vals.trip_name || '', startDt, endDt);
                    }
                });
                d.show();
            },

            // ── Chain a card as the next stop on an existing trip ──
            _chainToTrip(newCard, existingItems, vehicleId, presetTransitMin) {
                const self = this;

                // ── Capacity check before chaining ──
                const vehicle = this.planData.vehicles.find(v => v.id === vehicleId);
                if (vehicle) {
                    const currentLoad = this.peakLoadDuringCardWindows(newCard, vehicleId);
                    if (currentLoad + newCard.headcount > vehicle.seats) {
                        const shell = document.getElementById('rp-shell');
                        if (shell) {
                            shell.style.transition = 'background-color 0.2s';
                            shell.style.backgroundColor = '#ffebee';
                            setTimeout(() => { shell.style.backgroundColor = ''; }, 400);
                        }
                        frappe.throw(`Capacity Exceeded: Cannot assign ${newCard.headcount} employees to a ${vehicle.seats}-seater vehicle.`);
                        return;
                    }
                }

                // Find or create trip ID
                let tripId = existingItems.find(i => i.tripId)?.tripId;
                const existingTripName = existingItems.find(i => i.tripName)?.tripName || null;
                if (!tripId) {
                    tripId = `TRIP_${vehicleId}_${Math.random().toString(36).slice(2, 8)}`;
                    existingItems
                        .sort((a, b) => new Date(a.start) - new Date(b.start))
                        .forEach((item, idx) => {
                            item.tripId = tripId;
                            item.stopIndex = idx + 1;
                        });
                }

                // Shared placement logic (transitMin = travel, dwellMin = buffer at prev stop)
                const doChain = (transitMin, dwellMin) => {
                    const dwellMs = (dwellMin != null ? dwellMin : 0) * 60000;
                    const transitMs = Math.max((transitMin != null ? transitMin : 30), 5) * 60000; // min 5min block for visibility
                    const lastEnd = new Date(Math.max(
                        ...existingItems.map(i => new Date(i.end).getTime())
                    ));
                    const totalStops = self.swimItems.filter(i => i.tripId === tripId).length;

                    // Buffer gap after last stop before transit begins
                    const segStart = new Date(lastEnd.getTime() + dwellMs);
                    const segEnd = new Date(segStart.getTime() + transitMs);
                    const uid = Math.random().toString(36).slice(2, 10);

                    self.swimItems.push({
                        id: `${newCard.id}_${newCard.direction === 'RETURN' ? 'RET' : 'OUT'}_${uid}`, cardId: newCard.id, vehicleId,
                        direction: newCard.direction || 'OUTBOUND', start: segStart, end: segEnd,
                        headcount: newCard.headcount, conflict: false,
                        tripId, tripName: existingTripName, stopIndex: totalStops + 1
                    });

                    const allTrip = self.swimItems.filter(i => i.tripId === tripId);
                    allTrip.forEach(i => { i.totalStops = allTrip.length; });

                    self.assignedCards.add(newCard.id);
                    self.selectedPoolCard = null;
                    self.checkConflicts();
                    self.canSave = self.assignedCards.size > 0;
                    self.persistAssignments();

                    const bufferNote = dwellMin > 0 ? ` +${dwellMin}min buffer` : '';
                    frappe.show_alert({
                        message: `Stop ${totalStops + 1}: ${newCard.site_location} (${transitMin}min transit${bufferNote})`,
                        indicator: 'green'
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
                const lastCard = this.planData.shipment_cards.find(c => c.id === lastItem.cardId);
                const lastSiteName = lastCard ? lastCard.site_location : 'previous stop';
                const seatInfo = vehicle ? ` (${vehicle.seats} seats, ${this.peakLoadDuringCardWindows(newCard, vehicleId) + newCard.headcount} needed)` : '';

                const d = new frappe.ui.Dialog({
                    title: `Transit to ${newCard.site_location}`,
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
                                How long from <strong>${lastSiteName}</strong>
                                to <strong>${newCard.site_location}</strong>?${seatInfo}</p>`
                        },
                        {
                            fieldtype: 'Int', fieldname: 'transit_min',
                            label: 'Transit Time (minutes)',
                            default: 30, reqd: 1,
                            description: 'Driving time between stops'
                        },
                        { fieldtype: 'Column Break' },
                        {
                            fieldtype: 'Int', fieldname: 'dwell_min',
                            label: 'Dwell/Buffer Time (minutes)',
                            default: 10,
                            description: 'Loading/unloading time at previous stop before departing'
                        }
                    ],
                    primary_action_label: 'Add Stop',
                    primary_action(vals) {
                        d.hide();
                        doChain(vals.transit_min, vals.dwell_min || 0);
                    }
                });
                d.show();
            },

            // ── Time-aware peak load helper ─────────────────────────────────
            _getLogicalTrips(vehicleId) {
                const vi = this.swimItems.filter(i => i.vehicleId === vehicleId && this._liveToday(i));
                const tripsMap = {};
                let soloIdx = 0;
                
                vi.forEach(item => {
                    const key = item.tripId || `_solo_${soloIdx++}`;
                    if (!tripsMap[key]) {
                        tripsMap[key] = {
                            start: new Date(item.start).getTime(),
                            end: new Date(item.end).getTime(),
                            headcount: item.headcount || 0
                        };
                    } else {
                        tripsMap[key].start = Math.min(tripsMap[key].start, new Date(item.start).getTime());
                        tripsMap[key].end = Math.max(tripsMap[key].end, new Date(item.end).getTime());
                        tripsMap[key].headcount += (item.headcount || 0);
                    }
                });
                return Object.values(tripsMap);
            },

            // Returns the maximum simultaneous headcount on a vehicle during
            // the new card's outbound or return windows.
            peakLoadDuringCardWindows(card, vehicleId) {
                const DEF = 3600000;
                const outEnd = new Date(card.outbound_window_end).getTime();
                const outStart = outEnd - DEF;
                const retStart = new Date(card.return_window_start).getTime();
                const retEnd = retStart + DEF;

                const logicalTrips = this._getLogicalTrips(vehicleId);

                const loadDuring = (wS, wE) => {
                    return logicalTrips
                        .filter(t => {
                            return t.start < wE && t.end > wS;  // overlaps
                        })
                        .reduce((sum, t) => sum + t.headcount, 0);
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

            // Each card is now direction-specific (_OUT or _RET)
            // A card is fully assigned when it has a swim item placed
            isFullyAssigned(cardId) {
                return this.assignedCards.has(cardId);
            },

            // No longer needed — cards are direction-specific, badge is in the template
            cardAssignmentLabel(cardId) {
                return null;
            },

            placeCard(card, vehicleId) {
                const self = this;
                const isOutbound = card.direction === 'OUTBOUND';
                const dirLabel = isOutbound ? 'Outbound (→ To Site)' : 'Return (← From Site)';

                // ── Duration dialog with buffer + transit ──
                const d = new frappe.ui.Dialog({
                    title: `Assign ${dirLabel} — ${card.site_location}`,
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `<p style="margin:0 0 12px;color:#555;font-size:13px">
                                <strong>${card.shift_name}</strong><br>
                                ${card.headcount} employee(s) · Shift ${self.fmtISO(card.shift_start)} – ${self.fmtISO(card.shift_end)}<br>
                                Direction: <strong>${dirLabel}</strong></p>`
                        },
                        {
                            fieldtype: 'Data', fieldname: 'trip_name',
                            label: 'Trip Name', reqd: 1,
                            description: 'Auto-generated sequential trip name.',
                            default: self.generateTripName(vehicleId),
                            read_only: 1
                        },
                        { fieldtype: 'Section Break' },
                        {
                            fieldtype: 'Int', fieldname: 'buffer_min',
                            label: 'Buffer Time (minutes)',
                            description: isOutbound
                                ? 'Time for loading employees at accommodation'
                                : 'Time for loading employees at site',
                            default: 15, reqd: 1
                        },
                        {
                            fieldtype: 'Column Break'
                        },
                        {
                            fieldtype: 'Int', fieldname: 'duration_min',
                            label: 'Transit Time (minutes)',
                            description: isOutbound
                                ? 'Driving time from accommodation to site'
                                : 'Driving time from site to accommodation',
                            default: 60, reqd: 1
                        },
                        { fieldtype: 'Section Break', label: 'Multi-Day Vehicle Lock' },
                        {
                            fieldtype: 'Datetime', fieldname: 'start_datetime',
                            label: 'Start Date Time',
                            description: 'First day this run holds the vehicle. Defaults to the card\'s From Date (or today).',
                            default: self._defaultLockStart(card)
                        },
                        { fieldtype: 'Column Break' },
                        {
                            fieldtype: 'Datetime', fieldname: 'end_datetime',
                            label: 'End Date Time',
                            description: 'Last day this run holds the vehicle. Leave blank for a continuous (open-ended) run.',
                            default: self._defaultLockEnd(card)
                        }
                    ],
                    primary_action_label: 'Place on Timeline',
                    primary_action(vals) {
                        // ── Validate the multi-day lock window before placing ──
                        const startDt = vals.start_datetime || '';
                        const endDt = vals.end_datetime || '';
                        if (startDt) {
                            const today = frappe.datetime.get_today();
                            if (startDt.slice(0, 10) < today) {
                                frappe.throw('Start Date Time cannot be in the past.');
                                return;
                            }
                        }
                        if (startDt && endDt && startDt > endDt) {
                            frappe.throw('Start Date Time must be on or before End Date Time.');
                            return;
                        }
                        // Block a date range that overlaps an existing multi-day
                        // lock on this vehicle — including future reservations —
                        // before the drop is committed (mirrors the backend).
                        const newFrom = startDt ? startDt.slice(0, 10) : frappe.datetime.get_today();
                        const newTo = endDt ? endDt.slice(0, 10) : newFrom;
                        const clash = self._overlappingLock(vehicleId, newFrom, newTo, card.id);
                        if (clash) {
                            const [cf, ct] = self._lockDateRange(clash);
                            frappe.throw(`Vehicle Reserved: ${self.vehicleLabelForItem({ vehicleId })} is already locked from ${cf} to ${ct} for an overlapping run. Choose different dates or another vehicle.`);
                            return;
                        }
                        d.hide();
                        const bufferMs = (vals.buffer_min || 15) * 60000;
                        const transitMs = (vals.duration_min || 60) * 60000;
                        self._doPlace(card, vehicleId, transitMs, isOutbound, !isOutbound,
                            bufferMs, vals.trip_name || '', startDt, endDt);
                    }
                });
                d.show();
            },

            // A placement is "bounded" (its lock can lapse) when it spans more than
            // one day, or when its linked shipment carries a to_date. A single-day
            // run with no to_date is an open-ended / continuous run that never
            // lapses (AC2). Mirrors the backend _expired_assigned_shipments rule so
            // the canvas and the expiry job agree on what "expired" means.
            _isBoundedItem(item) {
                const from = item.lockFrom ? String(item.lockFrom).slice(0, 10) : null;
                const to = item.lockTo ? String(item.lockTo).slice(0, 10) : null;
                if (from && to && to > from) return true;   // multi-day span
                const card = this.planData.shipment_cards.find(c => c.id === item.cardId);
                return !!(card && card.to_date);
            },

            // True when a swim item is active on the current system date. A future
            // placement (lockFrom later than today) stays hidden until its start
            // date; a bounded lapsed one (lockTo before today) drops off; a
            // continuous run is always live. This is what makes a future-dated card
            // wait for its start date and an expired one disappear (TR-8).
            _liveToday(item) {
                const t = frappe.datetime.get_today();
                if (item.lockFrom && String(item.lockFrom).slice(0, 10) > t) return false;
                if (this._isBoundedItem(item) && item.lockTo && String(item.lockTo).slice(0, 10) < t) return false;
                return true;
            },

            // Serialize a render-position Date to an ISO stamp, replacing its
            // calendar date with the lock lifespan date when one is set. The time
            // of day (the daily trip window) is preserved either way.
            _stampLifespan(renderDate, lockDate) {
                const iso = new Date(renderDate).toISOString();
                if (!lockDate) return iso;
                return lockDate + iso.slice(10);
            },

            // Default the lock window's Start Date Time to the card's From Date,
            // clamped to today: use From Date when it is today or later, otherwise
            // fall back to today so the default never lands in the past (the "cannot
            // be in the past" rule). Undated cards default to today. The time part
            // is cosmetic — the block always runs at the card's own trip time.
            _defaultLockStart(card) {
                const today = frappe.datetime.get_today();
                let day = today;
                if (card && card.from_date) {
                    const fd = String(card.from_date).slice(0, 10);
                    day = fd > today ? fd : today;
                }
                return day + ' 00:00:00';
            },

            // Default the End Date Time to the card's To Date at end of day. Undated
            // (continuous / standing) cards get a blank end — an open-ended lock.
            _defaultLockEnd(card) {
                if (card && card.to_date) return card.to_date + ' 23:59:59';
                return '';
            },

            _doPlace(card, vehicleId, durMs, placeOutbound, placeReturn, bufferMs, tripName, startDatetime, endDatetime) {
                bufferMs = bufferMs || 0;
                tripName = tripName || '';
                // The lock lifespan lives in the DATE part of the persisted
                // start_time/end_time. We carry it separately on the swim item so
                // the block still renders at today's daily trip time; persistence
                // stamps the date onto the timestamps (see persistAssignments).
                const lockFrom = startDatetime ? String(startDatetime).slice(0, 10) : null;
                const lockTo = endDatetime ? String(endDatetime).slice(0, 10) : null;
                const totalMs = bufferMs + durMs;
                const outEnd = new Date(card.outbound_window_end);
                const outStart = new Date(outEnd.getTime() - totalMs);
                const retStart = new Date(card.return_window_start);
                const retEnd = new Date(retStart.getTime() + totalMs);
                const uid = Math.random().toString(36).slice(2, 10);

                // Auto-generate a tripId if a trip name was given
                const autoTripId = tripName ? `TRIP_${vehicleId}_${uid}` : null;

                if (placeOutbound) {
                    this.swimItems.push({
                        id: `${card.id}_OUT_${uid}`, cardId: card.id, vehicleId,
                        direction: 'OUTBOUND', start: outStart, end: outEnd,
                        headcount: card.headcount, conflict: false,
                        bufferMin: Math.round(bufferMs / 60000),
                        transitMin: Math.round(durMs / 60000),
                        tripId: autoTripId, tripName: tripName || null,
                        stopIndex: 1,
                        lockFrom, lockTo
                    });
                }
                if (placeReturn) {
                    this.swimItems.push({
                        id: `${card.id}_RET_${uid}`, cardId: card.id, vehicleId,
                        direction: 'RETURN', start: retStart, end: retEnd,
                        headcount: card.headcount, conflict: false,
                        bufferMin: Math.round(bufferMs / 60000),
                        transitMin: Math.round(durMs / 60000),
                        tripId: autoTripId, tripName: tripName || null,
                        stopIndex: 1,
                        lockFrom, lockTo
                    });
                }

                this.assignedCards.add(card.id);
                this.selectedPoolCard = null; // clear mobile selection on success
                this.checkConflicts();
                this.canSave = this.assignedCards.size > 0;
                this.persistAssignments();

                const bufferNote = bufferMs > 0 ? ` + ${Math.round(bufferMs/60000)}min buffer` : '';
                const dirLabel = (placeOutbound && placeReturn) ? 'Both trips'
                    : placeOutbound ? 'Outbound (→)' : 'Return (←)';
                const tripNote = tripName ? ` · Trip: ${tripName}` : '';

                // A future-dated placement is saved now but only appears on the
                // lane from its start date — tell the dispatcher so the "vanished"
                // block isn't mistaken for a failed drop (TR-8).
                if (lockFrom && String(lockFrom).slice(0, 10) > frappe.datetime.get_today()) {
                    frappe.show_alert({
                        message: `${dirLabel} scheduled on ${this.vehicleLabelForItem({ vehicleId })} — will appear on the lane from ${lockFrom}.`,
                        indicator: 'blue'
                    }, 6);
                } else {
                    frappe.show_alert({
                        message: `${dirLabel} placed on ${this.vehicleLabelForItem({ vehicleId })} (${Math.round(durMs/60000)}min transit${bufferNote})${tripNote}`,
                        indicator: 'green'
                    }, 4);
                }
            },



            checkConflicts() {
                this.swimItems.forEach(i => { i.conflict = false; i.overcapacity = false; });
                this.planData.vehicles.forEach(v => {
                    // Only reconcile items live today; a future-dated placement
                    // must not conflict with today's runs (TR-8).
                    const vi = this.swimItems.filter(i => i.vehicleId === v.id && this._liveToday(i));

                    // Time overlap detection
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

                    // Overcapacity detection: check headcount at each item's time window
                    if (v.seats && vi.length > 0) {
                        const logicalTrips = this._getLogicalTrips(v.id);
                        vi.forEach(item => {
                            const iS = new Date(item.start).getTime();
                            const iE = new Date(item.end).getTime();
                            const load = logicalTrips
                                .filter(t => {
                                    return t.start < iE && t.end > iS;
                                })
                                .reduce((sum, t) => sum + t.headcount, 0);
                            if (load > v.seats) {
                                item.overcapacity = true;
                            }
                        });
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

                    // Horizontal: shift time (snapped to 5-min intervals)
                    const deltaMs = (dx / this.svgWidth) * this.windowDurationMs;
                    const rawStart = new Date(origStart + deltaMs);
                    const snappedStart = this.snapTo5Min(rawStart);
                    const snapDelta = snappedStart.getTime() - origStart;
                    item.start = snappedStart;
                    item.end = new Date(origEnd + snapDelta);

                    // Update floating tooltip
                    this.dragTooltip = {
                        x: me.clientX,
                        y: me.clientY,
                        timeLabel: this.fmtTime(snappedStart)
                    };

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
                    this.dragTooltip = null;
                    setTimeout(() => { this.isDraggingBlock = false; }, 60);
                    if (moved) {
                        // If dropped on a different lane, validate seat capacity first
                        if (targetVehicleId !== origVehicleId) {
                            const targetVehicle = this.planData.vehicles.find(v => v.id === targetVehicleId);
                            if (targetVehicle) {
                                // Temporarily set vehicleId to check peak load on target
                                const origVid = item.vehicleId;
                                item.vehicleId = targetVehicleId;
                                const peakLoad = this.peakLoadDuringCardWindows(
                                    this.planData.shipment_cards.find(c => c.id === item.cardId) || { outbound_window_start: item.start, outbound_window_end: item.end, return_window_start: item.start, return_window_end: item.end },
                                    targetVehicleId
                                );
                                if (peakLoad > targetVehicle.seats) {
                                    // Revert — capacity exceeded
                                    item.vehicleId = origVid;
                                    item.start = new Date(origStart);
                                    item.end = new Date(origEnd);
                                    const shell = document.getElementById('rp-shell');
                                    if (shell) {
                                        shell.style.transition = 'background-color 0.2s';
                                        shell.style.backgroundColor = '#ffebee';
                                        setTimeout(() => { shell.style.backgroundColor = ''; }, 400);
                                    }
                                    // Use msgprint (not throw) so checkConflicts() below still runs to clear stale flags
                                    frappe.msgprint({
                                        title: __('Capacity Exceeded'),
                                        indicator: 'red',
                                        message: __(`Capacity Exceeded: Cannot assign ${item.headcount} employees to a ${targetVehicle.seats}-seater vehicle.`)
                                    });
                                } else {
                                    frappe.show_alert({
                                        message: `Moved to ${targetVehicle.label}`,
                                        indicator: 'blue'
                                    }, 3);
                                }
                            }
                        }
                        this.checkConflicts();
                        this.canSave = this.assignedCards.size > 0;
                        this.persistAssignments();
                    }
                };

                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
            },

            // Touch version of block drag (horizontal time repositioning only)
            onBlockTouchStart(e, item) {
                e.stopPropagation();
                const touch = e.touches[0];
                const startX = touch.clientX;
                const origStart = new Date(item.start).getTime();
                const origEnd = new Date(item.end).getTime();
                let moved = false;

                const onTouchMove = te => {
                    te.preventDefault();
                    const t = te.touches[0];
                    const dx = t.clientX - startX;
                    if (!moved && Math.abs(dx) > 5) moved = true;
                    if (!moved) return;
                    this.isDraggingBlock = true;
                    const deltaMs = (dx / this.svgWidth) * this.windowDurationMs;
                    const rawStart = new Date(origStart + deltaMs);
                    const snappedStart = this.snapTo5Min(rawStart);
                    const snapDelta = snappedStart.getTime() - origStart;
                    item.start = snappedStart;
                    item.end = new Date(origEnd + snapDelta);

                    // Update floating tooltip
                    this.dragTooltip = {
                        x: t.clientX,
                        y: t.clientY,
                        timeLabel: this.fmtTime(snappedStart)
                    };
                };

                const onTouchEnd = () => {
                    document.removeEventListener('touchmove', onTouchMove);
                    document.removeEventListener('touchend', onTouchEnd);
                    document.removeEventListener('touchcancel', onTouchCancel);
                    this.dragTooltip = null;
                    setTimeout(() => { this.isDraggingBlock = false; }, 60);
                    if (moved) {
                        this.checkConflicts();
                        this.canSave = this.assignedCards.size > 0;
                        this.persistAssignments();
                    }
                };

                const onTouchCancel = () => {
                    document.removeEventListener('touchmove', onTouchMove);
                    document.removeEventListener('touchend', onTouchEnd);
                    document.removeEventListener('touchcancel', onTouchCancel);
                    // Revert position on cancel
                    item.start = new Date(origStart);
                    item.end = new Date(origEnd);
                    this.dragTooltip = null;
                    setTimeout(() => { this.isDraggingBlock = false; }, 60);
                };

                document.addEventListener('touchmove', onTouchMove, { passive: false });
                document.addEventListener('touchend', onTouchEnd);
                document.addEventListener('touchcancel', onTouchCancel);
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

                        // The whole journey leg moves together (MA4-13 AC2): every stop
                        // sharing this block's trip id AND direction. Outbound and return
                        // legs stay independently assignable, so direction is part of the
                        // match; a standalone block (no tripId) moves on its own.
                        const journeyItems = item.tripId
                            ? self.swimItems.filter(i =>
                                i.tripId === item.tripId && i.direction === item.direction)
                            : [item];
                        const movingHeadcount = journeyItems.reduce((sum, i) => sum + (i.headcount || 0), 0);

                        // Seat capacity check on the target vehicle across the journey's
                        // combined time window. The selector excludes the current vehicle,
                        // so none of the moving stops are already on the target.
                        const blockStart = Math.min(...journeyItems.map(i => new Date(i.start).getTime()));
                        const blockEnd = Math.max(...journeyItems.map(i => new Date(i.end).getTime()));
                        const logicalTrips = self._getLogicalTrips(targetVehicle.id);
                        const existingLoad = logicalTrips
                            .filter(t => t.start < blockEnd && t.end > blockStart)
                            .reduce((sum, t) => sum + t.headcount, 0);

                        if (existingLoad + movingHeadcount > targetVehicle.seats) {
                            const shell = document.getElementById('rp-shell');
                            if (shell) {
                                shell.style.transition = 'background-color 0.2s';
                                shell.style.backgroundColor = '#ffebee';
                                setTimeout(() => { shell.style.backgroundColor = ''; }, 400);
                            }
                            frappe.throw(`Capacity Exceeded: Cannot assign ${movingHeadcount} employees to a ${targetVehicle.seats}-seater vehicle.`);
                            return;
                        }

                        // Move every stop of the journey leg to the new vehicle/driver.
                        journeyItems.forEach(i => { i.vehicleId = targetVehicle.id; });
                        self.checkConflicts();
                        self.canSave = self.assignedCards.size > 0;
                        self.persistAssignments();
                        self.selectedItem = null;
                        d.hide();
                        const stopNote = journeyItems.length > 1 ? ` (${journeyItems.length} stops)` : '';
                        frappe.show_alert({
                            message: `${dirLabel} moved to ${targetVehicle.label}${stopNote}`,
                            indicator: 'green'
                        });
                    }
                });
                d.show();
            },

            // ─ Stop drag-to-reorder handlers ──────────────────────────────
            onStopDragStart(event, sourceIndex) {
                this.stopDragSourceIndex = sourceIndex;
                event.dataTransfer.effectAllowed = 'move';
                event.dataTransfer.setData('text/plain', String(sourceIndex));
                // Slight delay to allow the drag image to render
                requestAnimationFrame(() => {
                    event.target.style.opacity = '0.4';
                });
            },

            onStopDragOver(event, targetIndex) {
                event.dataTransfer.dropEffect = 'move';
                this.stopDragOverIndex = targetIndex;
            },

            onStopDrop(event, targetIndex) {
                const sourceIndex = this.stopDragSourceIndex;
                if (sourceIndex === null || sourceIndex === targetIndex) {
                    this.stopDragSourceIndex = null;
                    this.stopDragOverIndex = null;
                    return;
                }

                const tripId = this.selectedItem.tripId;
                if (!tripId) return;

                // Get trip stops sorted by current stopIndex
                const tripStops = this.swimItems
                    .filter(i => i.tripId === tripId)
                    .sort((a, b) => (a.stopIndex || 0) - (b.stopIndex || 0));

                if (sourceIndex >= tripStops.length || targetIndex >= tripStops.length) return;

                // Capture durations and inter-stop gaps BEFORE reorder
                const durations = tripStops.map(s =>
                    new Date(s.end).getTime() - new Date(s.start).getTime()
                );
                const gaps = []; // gaps[i] = gap AFTER stop i (before stop i+1)
                for (let i = 0; i < tripStops.length - 1; i++) {
                    const gapMs = new Date(tripStops[i + 1].start).getTime()
                               - new Date(tripStops[i].end).getTime();
                    gaps.push(Math.max(0, gapMs));
                }

                // Fix #2: adjust target index for downward drags.
                // After splice(sourceIndex, 1), indices above sourceIndex shift down by 1.
                let insertAt = targetIndex;
                if (sourceIndex < targetIndex) {
                    insertAt = targetIndex - 1;
                }

                // Perform the reorder: remove source, insert at adjusted target
                const [moved] = tripStops.splice(sourceIndex, 1);
                const movedDuration = durations.splice(sourceIndex, 1)[0];
                // Remove the gap that was AFTER the source stop (or before it if at start)
                const removedGapIdx = Math.min(sourceIndex, gaps.length - 1);
                const removedGap = gaps.length > 0 ? gaps.splice(removedGapIdx, 1)[0] : 0;

                tripStops.splice(insertAt, 0, moved);
                durations.splice(insertAt, 0, movedDuration);
                // Re-insert the gap before the moved stop's new position
                if (gaps.length > 0 && insertAt < gaps.length) {
                    gaps.splice(insertAt, 0, removedGap);
                } else {
                    gaps.push(removedGap);
                }

                // Rebuild times: recalculate from the NEW first stop's shift window
                // The first stop's time window determines the trip start, not the old order
                const firstStop = tripStops[0];
                const firstCard = this.planData.shipment_cards.find(c => c.id === firstStop.cardId);
                let baseStartMs;
                if (firstCard) {
                    // Use the card's actual shift window as the anchor
                    const isOut = firstStop.direction === 'OUTBOUND' || (firstStop.direction !== 'RETURN');
                    const windowField = isOut ? 'outbound_window_start' : 'return_window_start';
                    const windowTime = new Date(firstCard[windowField]).getTime();
                    // Subtract the first stop's duration (transit time) to get departure time
                    baseStartMs = windowTime - durations[0];
                } else {
                    // Fallback: use the old minimum if card not found
                    baseStartMs = Math.min(
                        ...this.swimItems
                            .filter(i => i.tripId === tripId)
                            .map(s => new Date(s.start).getTime())
                    );
                }
                let cursor = baseStartMs;
                tripStops.forEach((stop, idx) => {
                    stop.stopIndex = idx + 1;
                    stop.start = new Date(cursor);
                    stop.end = new Date(cursor + durations[idx]);
                    cursor = cursor + durations[idx];
                    // Add inter-stop gap (dwell/buffer) if not the last stop
                    if (idx < gaps.length) {
                        cursor += gaps[idx];
                    }
                });

                // Update totalStops on all trip items
                tripStops.forEach(s => { s.totalStops = tripStops.length; });

                // Trigger Vue reactivity
                this.swimItems = [...this.swimItems];

                // Clear drag state
                this.stopDragSourceIndex = null;
                this.stopDragOverIndex = null;

                // Re-check conflicts and persist
                this.checkConflicts();
                this.persistAssignments();

                frappe.show_alert({
                    message: `Stop reordered — now ${tripStops.map((s, i) => `${i + 1}. ${(this.planData.shipment_cards.find(c => c.id === s.cardId) || {}).site_location || 'Unknown'}`).join(' → ')}`,
                    indicator: 'blue'
                }, 4);
            },

            onStopDragEnd(event) {
                event.target.style.opacity = '';
                this.stopDragSourceIndex = null;
                this.stopDragOverIndex = null;
            },

            mergeSelectedBlock() {
                if (!this.selectedItem || this.selectedItem.tripId) return;
                const item = this.selectedItem;
                const card = this.selectedCard;

                // Find all existing chained trips across all vehicles
                const tripOptions = [];
                const tripsMap = {};

                this.swimItems.forEach(i => {
                    if (i.id === item.id) return; // Exclude the block we are moving
                    const key = i.tripId || `solo_${i.id}`;
                    if (!tripsMap[key]) tripsMap[key] = { vehicleId: i.vehicleId, items: [], isSolo: !i.tripId };
                    tripsMap[key].items.push(i);
                });

                Object.keys(tripsMap).forEach(tid => {
                    const t = tripsMap[tid];
                    t.items.sort((a, b) => new Date(a.start) - new Date(b.start));
                    const lastItem = t.items[t.items.length - 1];
                    const lastCard = this.planData.shipment_cards.find(c => c.id === lastItem.cardId);
                    const vehicle = this.planData.vehicles.find(v => v.id === t.vehicleId);

                    if (vehicle && lastCard && lastItem.direction === item.direction) {
                        const tName = t.items.find(i => i.tripName)?.tripName;
                        const prefix = tName ? tName : (t.isSolo ? 'Single stop' : 'Trip');
                        tripOptions.push({
                            label: `[${vehicle.label}] ${prefix} ending at ${lastCard.site_location}`,
                            value: tid,
                            lastItem, lastCard, vehicle,
                            tripName: tName || null
                        });
                    }
                });

                if (tripOptions.length === 0) {
                    frappe.show_alert({ message: 'No existing trips available in the same direction', indicator: 'orange' });
                    return;
                }

                const self = this;
                const d = new frappe.ui.Dialog({
                    title: `Merge ${card.site_location}`,
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `<p style="margin:0 0 12px;color:#555;font-size:13px">Select an existing trip to merge this stop into. It will be appended to the end of the selected trip.</p>`
                        },
                        {
                            fieldtype: 'Select', fieldname: 'target_trip',
                            label: 'Select Target Trip', reqd: 1,
                            options: tripOptions.map(o => o.label).join('\n')
                        },
                        { fieldtype: 'Section Break' },
                        {
                            fieldtype: 'Int', fieldname: 'transit_min',
                            label: 'Transit Time (minutes)',
                            default: 30, reqd: 1,
                            description: 'Driving time from previous stop'
                        },
                        { fieldtype: 'Column Break' },
                        {
                            fieldtype: 'Int', fieldname: 'dwell_min',
                            label: 'Dwell/Buffer Time (minutes)',
                            default: 10,
                            description: 'Loading/unloading time at previous stop'
                        }
                    ],
                    primary_action_label: 'Merge',
                    primary_action(vals) {
                        const selectedOpt = tripOptions.find(o => o.label === vals.target_trip);
                        if (!selectedOpt) return;

                        let targetTripId = selectedOpt.value;
                        const targetTripItems = tripsMap[targetTripId].items;
                        const targetVehicleId = selectedOpt.vehicle.id;

                        // Check logical trip capacity directly instead of peakLoadDuringCardWindows 
                        // because we want to know the target trip's total capacity + new card
                        const tripLoad = targetTripItems.reduce((sum, i) => sum + (i.headcount || 0), 0);
                        if (tripLoad + card.headcount > selectedOpt.vehicle.seats) {
                            frappe.msgprint({
                                title: __('Capacity Exceeded'),
                                indicator: 'red',
                                message: __(`Capacity Exceeded: Cannot assign ${card.headcount} employees to a ${selectedOpt.vehicle.seats}-seater vehicle.`)
                            });
                            return;
                        }

                        d.hide();

                        // Remove original solo block
                        self.swimItems = self.swimItems.filter(i => i.id !== item.id);

                        // If merging into a solo block, convert it to a trip first
                        if (tripsMap[targetTripId].isSolo) {
                            targetTripId = `TRIP_${targetVehicleId}_${Math.random().toString(36).slice(2, 8)}`;
                            targetTripItems[0].tripId = targetTripId;
                            targetTripItems[0].stopIndex = 1;
                        }

                        // Append logic
                        const dwellMs = (vals.dwell_min || 0) * 60000;
                        const transitMs = (vals.transit_min || 30) * 60000;
                        const lastEnd = new Date(Math.max(...targetTripItems.map(i => new Date(i.end).getTime())));

                        const segStart = new Date(lastEnd.getTime() + dwellMs);
                        const segEnd = new Date(segStart.getTime() + transitMs);
                        const totalStops = targetTripItems.length;

                        const existingTripName = targetTripItems.find(i => i.tripName)?.tripName || selectedOpt.tripName || null;

                        self.swimItems.push({
                            id: item.id, // keep original ID
                            cardId: card.id, 
                            vehicleId: targetVehicleId,
                            direction: item.direction, 
                            start: segStart, 
                            end: segEnd,
                            headcount: item.headcount, 
                            conflict: false,
                            tripId: targetTripId, 
                            tripName: existingTripName,
                            stopIndex: totalStops + 1,
                            bufferMin: vals.dwell_min || 0,
                            transitMin: vals.transit_min || 30
                        });

                        const allTrip = self.swimItems.filter(i => i.tripId === targetTripId);
                        allTrip.forEach(i => { i.totalStops = allTrip.length; });

                        self.selectedItem = null;
                        self.checkConflicts();
                        self.canSave = self.assignedCards.size > 0;
                        self.persistAssignments();

                        frappe.show_alert({ message: `Merged into ${selectedOpt.vehicle.label} trip`, indicator: 'green' });
                    }
                });
                d.show();
            },

            vehicleLabelForItem(item) {
                const v = this.planData.vehicles.find(v => v.id === item.vehicleId);
                return v ? v.label : item.vehicleId;
            },

            /**
             * Auto-generate sequential trip name for a vehicle.
             * Format: {vehicleNumber}{2-digit-sequence}
             * Leased vehicles: S-{vehicleNumber}{2-digit-sequence}
             *
             * vehicleNumber is derived from VHL-#### name (e.g., VHL-0015 → 15)
             * sequence is 01-based count of existing trips on that vehicle + 1
             */
            generateTripName(vehicleId) {
                const vehicle = this.planData.vehicles.find(v => v.id === vehicleId);
                if (!vehicle) return '';

                // Extract integer from VHL-#### pattern; fallback to 1-based vehicle index
                const match = vehicleId.match(/VHL-(\d+)/i);
                let vehicleNumber = match ? parseInt(match[1], 10) : 0;
                if (!vehicleNumber) {
                    // Fallback: use 1-based position in vehicles list
                    const idx = this.planData.vehicles.findIndex(v => v.id === vehicleId);
                    vehicleNumber = idx >= 0 ? idx + 1 : 1;
                }

                // Count existing unique trips on this vehicle
                const existingTripIds = new Set();
                this.swimItems.forEach(item => {
                    if (item.vehicleId !== vehicleId) return;
                    if (item.tripId) {
                        existingTripIds.add(item.tripId);
                    } else {
                        existingTripIds.add(item.id);
                    }
                });
                const nextSeq = existingTripIds.size + 1;

                // Format: vehicleNumber + 2-digit sequence (e.g., 15 + 01 = "1501")
                const seqStr = String(nextSeq).padStart(2, '0');
                const tripName = `${vehicleNumber}${seqStr}`;

                // Leased vehicles get "S-" prefix
                const prefix = vehicle.is_leased ? 'S-' : '';
                return `${prefix}${tripName}`;
            },

            // ─ Persistence (save/load to Route Plan DocType) ──────────────

            loadSavedAssignments() {
                this.planLoading = true;
                // First fetch available plans, then load active
                frappe.call({
                    method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.get_route_plans',
                    async: true,
                    callback: (r) => {
                        this.planList = r.message || [];
                        // Now load the active plan
                        frappe.call({
                            method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.load_assignments',
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
                    effective_until: msg.effective_until,
                    is_default: Number(msg.is_default) || 0
                };

                // Restore swim items. start_time/end_time encode two things: the
                // TIME-of-day is the daily trip window (drives render position) and
                // the DATE is the multi-day lock lifespan. We split them here.
                const dayMs = 24 * 3600000;
                const todayStr = frappe.datetime.get_today();

                const DEFAULT_DUR_MS = 60 * 60000;
                let parsedItems = items.map(i => {
                    const startD = new Date(i.start);
                    const endD = new Date(i.end);
                    // Daily trip length = time-of-day span; the % dayMs strips the
                    // multi-day date component so the block is never days wide.
                    // Guard a missing/invalid end_time (e.g. edited away on the
                    // assignment) so the block falls back to a 1h daily bar instead
                    // of collapsing to a NaN/zero-width invisible one.
                    let dur;
                    if (!i.end || isNaN(endD.getTime())) {
                        dur = DEFAULT_DUR_MS;
                    } else {
                        dur = (((endD.getTime() - startD.getTime()) % dayMs) + dayMs) % dayMs;
                        if (!dur) dur = DEFAULT_DUR_MS;
                    }
                    return {
                        ...i,
                        start: startD,
                        end: (!i.end || isNaN(endD.getTime())) ? new Date(startD.getTime() + dur) : endD,
                        lockFrom: i.start ? String(i.start).slice(0, 10) : null,
                        lockTo: i.end ? String(i.end).slice(0, 10) : null,
                        _dailyDurMs: dur
                    };
                });

                // ── Multi-day lifespan gate (TR-8) ──
                // A placed block re-renders every day until the system date crosses
                // its lock end, then disappears. Continuous cards (linked shipment
                // has no to_date) are always shown; bounded cards stop once today
                // passes the lock end. This is AC1's "disappear after To Date".
                parsedItems = parsedItems.filter(i => {
                    if (!this._isBoundedItem(i)) return true;   // continuous — keep
                    const card = this.planData.shipment_cards.find(c => c.id === i.cardId);
                    const endDate = i.lockTo
                        ? String(i.lockTo).slice(0, 10)
                        : (card && card.to_date ? String(card.to_date).slice(0, 10) : todayStr);
                    return endDate >= todayStr;   // drop lapsed (release the lane)
                });

                // Rebase EACH block onto today's timeline independently, then
                // re-derive its end from the daily trip length. Every block now
                // carries its own lifespan start date (the DATE part of start_time),
                // so a single shared offset is wrong: one block whose start sits in
                // the past — an ongoing multi-day lock, or a row edited to a past
                // date — would otherwise drag every block off-screen and blank the
                // whole grid. Shifting per block by whole days (which preserves the
                // UTC time-of-day, and so the render position) keeps each one in the
                // current window on its own.
                parsedItems = parsedItems.map(i => {
                    let startMs = i.start.getTime();
                    if (startMs < this.planStart.getTime()) {
                        startMs += Math.ceil((this.planStart.getTime() - startMs) / dayMs) * dayMs;
                    } else if (startMs > this.planEnd.getTime()) {
                        startMs -= Math.ceil((startMs - this.planEnd.getTime()) / dayMs) * dayMs;
                    }
                    const start = new Date(startMs);
                    const end = new Date(startMs + i._dailyDurMs);
                    return { ...i, start, end };
                });

                this.swimItems = parsedItems;
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
                    method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.load_assignments',
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
                                    effective_until: plan.effective_until,
                                    is_default: Number(plan.is_default) || 0
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
                        {
                            fieldname: "is_default", label: "Is Default", fieldtype: "Check",
                            default: 0,
                            description: "Auto-load this plan when opening Transportation Schedule"
                        },
                    ],
                    primary_action_label: __("Create"),
                    primary_action(values) {
                        frappe.call({
                            method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.create_route_plan',
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

            togglePlanStatus(newStatus) {
                if (!this.currentPlan) return;
                const self = this;
                const planName = this.currentPlan.name;
                const planTitle = this.currentPlan.title;

                const doUpdate = () => {
                    frappe.call({
                        method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.update_route_plan_status',
                        args: { plan_name: planName, new_status: newStatus },
                        callback: (r) => {
                            if (r.message && r.message.status === 'ok') {
                                self.currentPlan.status = newStatus;
                                // Refresh plan list to reflect status changes (incl. deactivated plans)
                                self.refreshPlanList();
                                const indicators = { Active: 'green', Draft: 'orange', Expired: 'grey' };
                                frappe.show_alert({
                                    message: `"${planTitle}" is now ${newStatus}`,
                                    indicator: indicators[newStatus] || 'blue'
                                }, 4);
                            }
                        }
                    });
                };

                if (newStatus === 'Active') {
                    frappe.confirm(
                        `Activate <strong>"${planTitle}"</strong>?<br><br>` +
                        `<span style="color:#888;font-size:12px">Any other Active plan will be automatically set to Draft.</span>`,
                        doUpdate
                    );
                } else if (newStatus === 'Expired') {
                    frappe.confirm(
                        `Mark <strong>"${planTitle}"</strong> as Expired?<br><br>` +
                        `<span style="color:#888;font-size:12px">This plan will no longer be available for dispatch.</span>`,
                        doUpdate
                    );
                } else {
                    doUpdate();
                }
            },

            refreshPlanList(callback) {
                frappe.call({
                    method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.get_route_plans',
                    async: true,
                    callback: (r) => {
                        this.planList = r.message || [];
                        if (callback) callback();
                    }
                });
            },



            persistAssignments() {
                if (!this.currentPlan) {
                    // Surface the silent failure: without a loaded Route Plan there
                    // is nowhere to save, so the assignment would vanish on refresh.
                    frappe.show_alert({
                        message: 'No Route Plan is loaded — this assignment was NOT saved. Create or select a plan (and mark it Default) first.',
                        indicator: 'red'
                    }, 6);
                    return;
                }
                // Debounce: clear any pending save and schedule a new one
                if (this._saveTimer) clearTimeout(this._saveTimer);
                this._saveTimer = setTimeout(() => {
                    // Enrich swim items with card metadata for persistence
                    const items = this.swimItems.map(i => {
                        const card = this.planData.shipment_cards.find(c => c.id === i.cardId);
                        return {
                            ...i,
                            // Persist the daily trip time (from the render position) but
                            // stamp the multi-day lock lifespan onto the DATE part so
                            // start_time/end_time carry both (TR-8).
                            start: this._stampLifespan(i.start, i.lockFrom),
                            end: this._stampLifespan(i.end, i.lockTo || i.lockFrom),
                            _site: card ? card.site : '',
                            _shift: card ? card.shift_name : '',
                            _accommodation: card ? card.accommodation : '',
                            _stopLocation: card ? card.stop_location : '',
                        };
                    });
                    const cards = [...this.assignedCards];

                    frappe.call({
                        method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.save_assignments',
                        args: {
                            plan_name: this.currentPlan.name,
                            swim_items: JSON.stringify(items),
                            assigned_cards: JSON.stringify(cards)
                        },
                        async: true,
                        callback: () => { }, // silent save on success
                        error: () => {
                            // A server-side validation (e.g. the vehicle-retention
                            // STANDBY lock) rejected the drop. Frappe already shows
                            // the thrown message; reload the plan so the phantom
                            // block is removed and the canvas mirrors what persisted.
                            if (this.currentPlan && this.currentPlan.name) {
                                this.switchPlan(this.currentPlan.name);
                            }
                        }
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

            // ── Driver on the wheel for a given block (WI-001577) ──
            // A vehicle can change hands mid-day, so the driver is resolved per block
            // rather than per lane: whoever holds the vehicle when the run starts. With
            // no Vehicle Handover Log covering that moment the permanent custodian drives.
            handoverWindows(vehicleId) {
                return (this.planData && this.planData.handover_windows
                    ? this.planData.handover_windows[vehicleId]
                    : null) || [];
            },

            handoverAt(vehicleId, at) {
                const instant = new Date(at).getTime();
                if (isNaN(instant)) return null;

                return this.handoverWindows(vehicleId).find(w =>
                    instant >= new Date(w.start).getTime() && instant <= new Date(w.end).getTime()
                ) || null;
            },

            // True when [start, end) overlaps any handover window on this vehicle.
            overlapsHandover(vehicleId, start, end) {
                const from = new Date(start).getTime();
                const to = new Date(end).getTime();
                if (isNaN(from) || isNaN(to)) return null;

                return this.handoverWindows(vehicleId).find(w =>
                    from < new Date(w.end).getTime() && to > new Date(w.start).getTime()
                ) || null;
            },

            blockDriver(item, vehicle) {
                const handover = this.handoverAt(vehicle.id, item.start);
                return handover ? handover.driver_name : (vehicle.driver || '—');
            },

            bfill(item) {
                const shell = document.getElementById('rp-shell');
                const cs = shell ? getComputedStyle(shell) : null;
                if (item.conflict) return cs ? cs.getPropertyValue('--rp-color-conflict').trim() : '#c62828';
                if (item.overcapacity) return '#7b1fa2'; // purple for overcapacity
                return item.direction === 'OUTBOUND'
                    ? (cs ? cs.getPropertyValue('--rp-color-outbound').trim() : '#1565c0')
                    : (cs ? cs.getPropertyValue('--rp-color-return').trim() : '#e65100');
            },

            bcard(item) {
                const found = this.planData.shipment_cards.find(c => c.id === item.cardId);
                if (found) return found;
                // Fallback for loaded plan items
                if (item._site || item._stopLocation) {
                    return {
                        site_location: item._stopLocation || item._site || '—',
                        shift_name: item._shift || '—',
                        stop_location: item._stopLocation || '—',
                    };
                }
                return {};
            },

            bsel(item) {
                return !!(this.selectedItem && this.selectedItem.id === item.id);
            },

            // ── Multi-stop hover popup (AC: group by Pickup Accommodation) ──

            /**
             * Group a list of swim-item stops by their Pickup Accommodation,
             * summing pax (headcount) per accommodation. Stop sequence numbers
             * follow the order each accommodation first appears — matching the
             * backend Transportation Manifest rule.
             * @returns {Array<{seq:number, accommodation:string, pax:number, stops:number}>}
             */
            computeStopGroups(stops) {
                const order = [];
                const map = {};
                (stops || []).forEach(s => {
                    const card = this.bcard(s);
                    const acc = (card && card.accommodation)
                        ? card.accommodation
                        : (s._accommodation || '—');
                    if (!(acc in map)) {
                        map[acc] = { seq: order.length + 1, accommodation: acc, pax: 0, stops: 0 };
                        order.push(acc);
                    }
                    map[acc].pax += (s.headcount || 0);
                    map[acc].stops += 1;
                });
                return order.map(acc => map[acc]);
            },

            showStopHover(e, stops) {
                if (this.isDraggingBlock) return;   // don't compete with block drag
                const groups = this.computeStopGroups(stops);
                if (!groups.length) return;
                this.hoverPopup = { x: e.clientX, y: e.clientY, groups };
            },

            moveStopHover(e) {
                if (this.hoverPopup) {
                    this.hoverPopup.x = e.clientX;
                    this.hoverPopup.y = e.clientY;
                }
            },

            hideStopHover() {
                this.hoverPopup = null;
            },

            // ── Merged block position helpers ──
            mbx(entry) { return this.timeToX(entry.start); },
            mbw(entry) { return Math.max(8, this.timeToX(entry.end) - this.timeToX(entry.start)); },
            mby(entry) {
                const pad = 4;
                const cols = entry._totalCols || 1;
                const col = entry._col || 0;
                const usable = this.rowHeight - pad * 2;
                return pad + col * (usable / cols);
            },
            mbh(entry) {
                const pad = 4;
                const cols = entry._totalCols || 1;
                const usable = this.rowHeight - pad * 2;
                return (usable / cols) - 2;
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

            // ─ Theme toggle ─────────────────────────────────────────────────

            toggleTheme() {
                this.isDark = !this.isDark;
                localStorage.setItem('transportation-schedule-theme', this.isDark ? 'dark' : 'light');
                this.applyTheme();
            },

            applyTheme() {
                const shell = document.getElementById('rp-shell');
                if (shell) {
                    shell.classList.toggle('rp-dark', this.isDark);
                }
            },

            // ─ Manifest generation (ported verbatim from vis version) ───────

            generateShipments() {
                // Materialize/refresh Transportation Shipment records from Operations
                // Shift data, then reload the pool from the persisted records.
                if (this.isGenerating) return;
                this.isGenerating = true;
                const self = this;
                frappe.call({
                    method: 'one_fm.one_fm.doctype.transportation_shipment.shipment_generator.generate_transportation_shipments',
                    callback: function (r) {
                        const s = r.message || {};
                        frappe.show_alert({
                            message: `Shipments: ${s.created || 0} created, ${s.updated || 0} updated, ${s.deleted || 0} removed`,
                            indicator: 'green'
                        });
                        frappe.call({
                            method: 'one_fm.one_fm.page.transportation_schedule.transportation_schedule.get_route_planner_data',
                            callback: function (rd) {
                                if (rd.message && rd.message.status === 'ok') {
                                    self.planData.shipment_cards = rd.message.shipment_cards;
                                }
                            }
                        });
                    },
                    always: function () {
                        self.isGenerating = false;
                    }
                });
            },

            async openManifest() {
                if (!this.currentPlan || !this.currentPlan.name) {
                    frappe.show_alert({
                        message: 'No plan is loaded. Save a plan first before opening the manifest.',
                        indicator: 'orange'
                    });
                    return;
                }

                if (this.swimItems.length === 0) {
                    frappe.show_alert({
                        message: 'No assigned shipments to generate a manifest from.',
                        indicator: 'orange'
                    });
                    return;
                }

                // Navigate to the persistent manifest page
                const planName = this.currentPlan.name;
                const manifestUrl = `/app/transportation-manifest-page/${planName}`;
                window.open(manifestUrl, '_blank');

                frappe.show_alert({
                    message: `Manifest opened for plan "${this.currentPlan.title || planName}"`,
                    indicator: 'green'
                }, 4);
            },

            buildManifestData() {
                const slug = s => (s || '').replace(/[\s_]+/g, '-').replace(/[^a-zA-Z0-9\-]/g, '');

                const shipments = [], vehiclesList = [], routes = [];
                const shipEmp = {}, shipReturnEmp = {}, shipSite = {}, shipShift = {}, vMeta = {}, cMap = {};
                let si = 0;

                // Fix #6: Build shipments from swimItems (per direction actually placed)
                // instead of from assignedCards, to avoid phantom shipments
                this.swimItems.forEach(item => {
                    let card = this.planData.shipment_cards.find(c => c.id === item.cardId);
                    // Fuzzy-match for loaded plans where card IDs may have shifted
                    if (!card && (item._accommodation || item._stopLocation)) {
                        card = this.planData.shipment_cards.find(c =>
                            c.accommodation === item._accommodation &&
                            c.stop_location === item._stopLocation &&
                            c.direction === (item.direction || 'OUTBOUND') &&
                            (!item._shift || c.shift_name === item._shift)
                        );
                    }
                    if (!card) return;

                    const dirKey = `${item.cardId}_${item.direction}`;
                    if (cMap[dirKey]) return; // already created shipment for this card+direction

                    const lbl = `${slug(card.accommodation)}_${si}_${slug(card.site_location)}_${item.direction}`;
                    const idx = si++;

                    shipments.push({ label: lbl, pickups: [{}], deliveries: [{}] });
                    // OUTBOUND uses card.employees (employees being delivered to site)
                    // RETURN uses card.return_employees (previous shift employees being collected)
                    if (item.direction === 'RETURN') {
                        shipEmp[lbl] = (card.return_employees && card.return_employees.length > 0) ? card.return_employees : [];
                    } else {
                        shipEmp[lbl] = card.employees || [];
                    }
                    shipReturnEmp[lbl] = card.return_employees || [];
                    shipSite[lbl] = card.site_location;
                    shipShift[lbl] = card.shift_name;
                    cMap[dirKey] = { lbl, idx };
                });

                this.planData.vehicles.forEach((v, vi) => {
                    vehiclesList.push({ label: v.label, startLocation: null });
                    vMeta[v.label] = {
                        accommodation: v.accommodation, driver: v.driver,
                        seats: v.seats, location: v.location,
                        license_plate: v.license_plate
                    };

                    // Sort vehicle items: trip stops by stopIndex, solo items by start time
                    const vItems = this.swimItems
                        .filter(i => i.vehicleId === v.id)
                        .sort((a, b) => {
                            // If both are in the same trip, sort by stopIndex
                            if (a.tripId && b.tripId && a.tripId === b.tripId) {
                                return (a.stopIndex || 0) - (b.stopIndex || 0);
                            }
                            // Otherwise sort by start time
                            return new Date(a.start) - new Date(b.start);
                        });
                    if (!vItems.length) return;

                    const visits = [], trans = [];
                    trans.push({ travelDuration: '0s', waitDuration: '0s', travelDistanceMeters: 0 });

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
                            tripName: item.tripName || null,
                            stopIndex: item.stopIndex || 0
                        });
                        trans.push({
                            travelDuration: `${dSec}s`, waitDuration: '0s',
                            travelDistanceMeters: Math.round(dSec * 10)
                        });
                        visits.push({
                            shipmentIndex: sIdx, isPickup: false, startTime: iE,
                            loadDemands: { seats: { amount: String(-hc) } },
                            tripId: item.tripId || null,
                            tripName: item.tripName || null,
                            stopIndex: item.stopIndex || 0
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

                    // Trip Time = sum of only actual trip item durations (excludes idle gaps between trips)
                    const tripTimeMs = vItems.reduce((sum, item) => {
                        return sum + (new Date(item.end) - new Date(item.start));
                    }, 0);

                    // Cap both at 24 hours (86400s) for a single daily manifest
                    const MAX_DAY_SEC = 86400;
                    const totalSec = Math.min(Math.round(totMs / 1000), MAX_DAY_SEC);
                    const tripSec = Math.min(Math.round(tripTimeMs / 1000), MAX_DAY_SEC);

                    routes.push({
                        vehicleIndex: vi, vehicleLabel: v.label,
                        vehicleStartTime: rS, vehicleEndTime: rE,
                        visits, transitions: trans,
                        metrics: {
                            travelDistanceMeters: 0,
                            totalDuration: `${totalSec}s`,
                            travelDuration: `${tripSec}s`
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
                    shipmentReturnEmployees: shipReturnEmp,
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

                // Apply saved theme
                this.applyTheme();

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

  <!-- ── Drag time tooltip (5-min snap) ── -->
  <div v-if="dragTooltip"
       class="rp-drag-tooltip"
       :style="{
           left: dragTooltip.x + 'px',
           top: (dragTooltip.y - 44) + 'px'
       }">
    {{ dragTooltip.timeLabel }}
  </div>

  <!-- ── Multi-stop hover popup (rows-per-stop pax summary) ── -->
  <div v-if="hoverPopup && !isDraggingBlock"
       class="rp-stop-hover"
       :style="{
           left: hoverPopup.x + 'px',
           top: (hoverPopup.y + 18) + 'px'
       }">
    <div class="rp-stop-hover-title">
      {{ hoverPopup.groups.length > 1 ? 'Multi-Stop Route' : 'Route Stop' }}
    </div>
    <div class="rp-stop-hover-flow">
      <template v-for="(g, gi) in hoverPopup.groups" :key="'sh' + gi">
        <span class="rp-stop-hover-chip">
          <span class="rp-stop-hover-seq">Stop {{ g.seq }}</span>
          <span class="rp-stop-hover-acc">{{ g.accommodation }}</span>
          <span class="rp-stop-hover-pax">[{{ g.pax }} Pax]</span>
        </span>
        <span v-if="gi < hoverPopup.groups.length - 1" class="rp-stop-hover-arrow">&#10142;</span>
      </template>
    </div>
  </div>

  <!-- ══ Header ══ -->
  <div id="rp-header">
    <div id="rp-header-left">
      <div id="rp-title">Transportation Schedule</div>
    <div id="rp-plan-selector" style="display:flex;align-items:center;gap:8px;margin-top:4px;flex-wrap:wrap">
        <select :value="currentPlan ? currentPlan.name : ''"
                @change="switchPlan($event.target.value)"
                class="form-control input-sm"
                style="width:auto;min-width:160px">
          <option value="" disabled>Select a plan…</option>
          <option v-for="p in planList" :key="p.name" :value="p.name">
            {{ Number(p.is_default) ? '\u2605 ' : '' }}{{ p.title }} ({{ p.status }})
          </option>
        </select>
        <button class="rp-btn rp-btn-default"
                @click="createNewPlan">+ New Plan</button>
        <span v-if="currentPlan" class="indicator-pill"
              :class="currentPlan.status === 'Active' ? 'green' : currentPlan.status === 'Draft' ? 'orange' : 'gray'">
          {{ currentPlan.status }}
        </span>
        <span v-if="currentPlan && Number(currentPlan.is_default)" class="indicator-pill blue">
          \u2605 Default
        </span>
        <button v-if="currentPlan && currentPlan.status === 'Draft'"
                class="rp-btn rp-btn-success"
                @click="togglePlanStatus('Active')"
                title="Activate this route plan">
          ✓ Activate
        </button>
        <button v-if="currentPlan && currentPlan.status === 'Active'"
                class="rp-btn rp-btn-warning"
                @click="togglePlanStatus('Draft')"
                title="Set back to Draft">
          ↩ Deactivate
        </button>
        <button v-if="currentPlan && (currentPlan.status === 'Draft' || currentPlan.status === 'Active')"
                class="rp-btn rp-btn-default"
                @click="togglePlanStatus('Expired')"
                title="Mark this plan as expired">
          ✕ Expire
        </button>
        <span v-if="currentPlan && currentPlan.effective_from" class="text-muted" style="font-size:11px">
          {{ currentPlan.effective_from }}{{ currentPlan.effective_until ? ' → ' + currentPlan.effective_until : ' → ∞' }}
        </span>
        <span v-if="planLoading" class="text-muted" style="font-size:11px">Loading…</span>
      </div>
    </div>
    <div id="rp-header-right">
      <div v-if="currentPlan" class="text-muted" style="font-size:12px; margin-right: 12px; display: flex; align-items: center; gap: 4px; color: var(--green, #16a34a)">
        <span class="rp-icon" style="font-size:16px;">check_circle</span> Auto-Saved
      </div>
      <button class="rp-btn rp-btn-default" :disabled="isGenerating" @click="generateShipments" title="Refresh unassigned shipments from Operations Shift data">
        <span class="rp-icon">{{ isGenerating ? 'hourglass_empty' : 'sync' }}</span> {{ isGenerating ? 'Generating…' : 'Generate Shipments' }}
      </button>
      <button class="rp-btn rp-btn-default rp-btn-manifest" :disabled="!canSave || !currentPlan" @click="openManifest">
        <span class="rp-icon">assignment</span> Manifest
      </button>
      <button class="rp-btn rp-btn-icon-only" @click="toggleTheme" :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'">
        <span class="rp-icon">{{ isDark ? 'light_mode' : 'dark_mode' }}</span>
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
                 :class="['rp-card', card.direction === 'OUTBOUND' ? 'rp-card-out' : 'rp-card-ret', selectedPoolCard && selectedPoolCard.id === card.id ? 'rp-card-selected' : '']"
                 draggable="true"
                 @dragstart="onCardDragStart($event, card)"
                 @dragend="onCardDragEnd"
                 @click="onCardTap(card)">
              <div class="rp-card-header">
                <span class="rp-card-site">{{ card.site_location }}</span>
                <span :class="['rp-card-dir', card.direction === 'OUTBOUND' ? 'rp-dir-out' : 'rp-dir-ret']">
                  {{ card.direction === 'OUTBOUND' ? '→ OUT' : '← RET' }}
                </span>
                <span :class="['rp-card-type', card.type === 'OLM' ? 'rp-tag-olm' : 'rp-tag-osm']">{{ card.type }}</span>
              </div>
              <div class="rp-card-shift">{{ card.shift_name }}</div>
              <div class="rp-card-meta">
                <span class="rp-card-meta-item">
                  <span class="rp-meta-icon"><span class="rp-icon">group</span></span>{{ card.headcount }} employees
                </span>
                <span class="rp-card-meta-item">
                  <span class="rp-meta-icon"><span class="rp-icon">location_on</span></span>{{ card.stop_location }}
                </span>
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
                <span v-for="(e, ei) in card.employees.slice(0,3)" :key="card.id + '_' + ei" class="rp-emp-chip rp-emp-chip-call" @click.stop="handleEmployeeCall(e)" :title="empMobile(e) ? 'Call ' + empMobile(e) : 'No mobile number'">
                  {{ empName(e) }}
                  <span class="rp-icon rp-call-icon" :class="empMobile(e) ? '' : 'rp-call-disabled'">call</span>
                </span>
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
          <button class="rp-btn-icon rp-btn-icon-label" title="Show full 24 hours" @click="show24h()">24h</button>
          <button class="rp-btn-icon rp-btn-icon-label" title="Show working hours (05:00–19:00)" @click="showWorkHours()"><span class="rp-icon" style="font-size:14px">schedule</span> Work</button>
        </div>
        <div class="rp-tb-hint">
          Drag cards to lanes &nbsp;&middot;&nbsp; Drag blocks to reposition &nbsp;&middot;&nbsp;
          Scroll to pan &nbsp;&middot;&nbsp; Ctrl + Scroll to zoom
        </div>
        <div id="rp-timeline-legend">
          <span class="rp-legend-item rp-legend-out">Outbound</span>
          <span class="rp-legend-item rp-legend-ret">Return</span>
          <span class="rp-legend-item rp-legend-conflict">Conflict</span>
          <span class="rp-legend-item rp-legend-overcap">Overcapacity</span>
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
               :class="['rp-lane-row', vi % 2 === 1 ? 'rp-lane-alt' : '', lockedLaneIds.has(vehicle.id) ? 'rp-lane-locked' : '']"
               :data-vehicle-id="vehicle.id">

            <!-- Vehicle label column -->
            <div class="rp-lane-label">
              <div class="rp-gv-plate">
                {{ vehicle.label }}
                <span v-if="lockedLaneIds.has(vehicle.id)" class="rp-lock-badge" title="Reserved for a multi-day run — blocked for other shipments">&#x1F512;</span>
                <span v-else-if="upcomingLockByVehicle[vehicle.id]" class="rp-lock-upcoming" :title="'Reserved for an upcoming multi-day run from ' + upcomingLockByVehicle[vehicle.id]">&#x1F512; from {{ upcomingLockByVehicle[vehicle.id] }}</span>
              </div>
              <div v-if="vehicle.license_plate" class="rp-gv-lp">{{ vehicle.license_plate }}</div>
              <div class="rp-gv-meta">{{ vehicle.driver }} &middot; {{ vehicle.seats }} seats</div>
              <div class="rp-gv-acc">{{ vehicle.accommodation }}</div>
            </div>

            <!-- SVG swimlane canvas -->
            <div class="rp-lane-svg-wrap"
                 @dragover="onLaneDragOver"
                 @drop="onLaneDrop($event, vehicle)"
                 @click="onLaneTap($event, vehicle)">
              <svg :width="svgWidth" :height="rowHeight"
                   class="rp-lane-svg"
                   @wheel.prevent="onSvgWheel"
                   @click.self="closeDetail">

                <!-- Vertical grid lines -->
                <line v-for="tick in axisTicks" :key="'g' + tick.key"
                      :x1="tick.x" :x2="tick.x" y1="0" :y2="rowHeight"
                      :stroke="tick.isMajor ? '#ebebeb' : '#f6f6f6'" stroke-width="1"/>

                <!-- Locked-lane wash: a vehicle held by an active multi-day lock is
                     blocked out for any other shipment (TR-8). -->
                <rect v-if="lockedLaneIds.has(vehicle.id)" x="0" y="0" :width="svgWidth" :height="rowHeight"
                      fill="rgba(120,120,120,0.10)" style="pointer-events:none"/>

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

                <!-- ── Swim items (merged trip view) ── -->
                <template v-for="entry in mergedItemsByVehicle[vehicle.id]" :key="entry.type === 'merged' ? 'trip_' + entry.tripId : entry.item.id">

                  <!-- ═══ Single (non-chained) block ═══ -->
                  <g v-if="entry.type === 'single'"
                     :class="isDraggingBlock && bsel(entry.item) ? 'rp-block-grabbing' : 'rp-block-grab'"
                     @mousedown="onBlockMouseDown($event, entry.item)"
                     @touchstart.prevent="onBlockTouchStart($event, entry.item)"
                     @mouseenter="showStopHover($event, [entry.item])"
                     @mousemove="moveStopHover($event)"
                     @mouseleave="hideStopHover()"
                     @click.stop="onBlockClick(entry.item, $event)">

                    <!-- Native tooltip showing full site name + shift + time + driver -->
                    <title>{{ bcard(entry.item).site_location || 'Unknown' }} — {{ bcard(entry.item).shift_name || '' }} | {{ fmtTime(entry.item.start) }}–{{ fmtTime(entry.item.end) }} · {{ entry.item.headcount }} pax · Driver: {{ blockDriver(entry.item, vehicle) }}</title>

                    <!-- Clip path for text overflow -->
                    <defs>
                      <clipPath :id="'sclip-' + entry.item.id">
                        <rect :x="bx(entry.item)" :y="by(entry.item)"
                              :width="bw(entry.item)" :height="bh(entry.item)" rx="5"/>
                      </clipPath>
                    </defs>

                    <rect :x="bx(entry.item) + 1" :y="by(entry.item) + 2"
                          :width="bw(entry.item)" :height="bh(entry.item)"
                          fill="rgba(0,0,0,0.10)" rx="5"/>
                    <rect :x="bx(entry.item)" :y="by(entry.item)"
                          :width="bw(entry.item)" :height="bh(entry.item)"
                          :fill="bfill(entry.item)"
                          :stroke="bsel(entry.item) ? '#f97316' : 'transparent'"
                          stroke-width="2.5" rx="5"/>

                    <!-- Clipped text group -->
                    <g :clip-path="'url(#sclip-' + entry.item.id + ')'">

                      <!-- Line 1: Direction arrow + trip name -->
                      <text v-if="bw(entry.item) >= 18"
                            :x="bx(entry.item) + 8" :y="by(entry.item) + 18"
                            fill="white" font-size="12"
                            font-weight="700" dominant-baseline="middle"
                            style="user-select:none;pointer-events:none">
                        {{ entry.item.direction === 'OUTBOUND' ? '\u2192' : '\u2190' }}{{ entry.item.tripName ? ' ' + entry.item.tripName : (entry.item.direction === 'OUTBOUND' ? ' To' : ' From') }}
                      </text>

                      <!-- Line 2: Site name (bold, large) -->
                      <text v-if="bw(entry.item) >= 40 && bh(entry.item) >= 36"
                            :x="bx(entry.item) + 8" :y="bcy(entry.item) + 2"
                            fill="white" font-size="14" font-weight="700"
                            dominant-baseline="middle"
                            style="user-select:none;pointer-events:none">
                        {{ bcard(entry.item).site_location }}
                      </text>

                      <!-- Line 3: Time range + headcount -->
                      <text v-if="bw(entry.item) >= 60 && bh(entry.item) >= 50"
                            :x="bx(entry.item) + 8" :y="by(entry.item) + bh(entry.item) - 12"
                            fill="rgba(255,255,255,0.85)" font-size="12"
                            dominant-baseline="middle"
                            style="user-select:none;pointer-events:none">
                        {{ fmtTime(entry.item.start) }}–{{ fmtTime(entry.item.end) }} · {{ entry.item.headcount }} pax
                      </text>

                      <!-- Line 4: driver holding the vehicle for this block (WI-001577).
                           Handed-over blocks are marked so a rotation is visible at a
                           glance; blocks on the permanent driver read plainly. -->
                      <text v-if="bw(entry.item) >= 60 && bh(entry.item) >= 68"
                            :x="bx(entry.item) + 8" :y="by(entry.item) + bh(entry.item) - 27"
                            fill="rgba(255,255,255,0.95)" font-size="11"
                            :font-weight="handoverAt(vehicle.id, entry.item.start) ? '700' : '400'"
                            dominant-baseline="middle"
                            style="user-select:none;pointer-events:none">
                        {{ handoverAt(vehicle.id, entry.item.start) ? '⇄ ' : '' }}{{ blockDriver(entry.item, vehicle) }}
                      </text>

                    </g>

                    <rect v-if="bw(entry.item) >= 24"
                          :x="bx(entry.item) + bw(entry.item) - 5" :y="by(entry.item) + 4"
                          width="3" :height="bh(entry.item) - 8"
                          fill="rgba(255,255,255,0.22)" rx="1.5"
                          style="cursor:ew-resize;pointer-events:none"/>
                  </g>

                  <!-- ═══ Merged trip block ═══ -->
                  <g v-else
                     class="rp-block-grab"
                     @mouseenter="showStopHover($event, entry.stops)"
                     @mousemove="moveStopHover($event)"
                     @mouseleave="hideStopHover()"
                     @click.stop="onBlockClick(entry.primaryItem, $event)">

                    <!-- Native tooltip showing all stops + time -->
                    <title>{{ entry.tripName ? entry.tripName + ' — ' : '' }}{{ entry.stopLabels.join(' → ') }} | {{ fmtTime(entry.start) }}–{{ fmtTime(entry.end) }} · {{ entry.headcount }} pax · Driver: {{ blockDriver(entry, vehicle) }}</title>

                    <!-- Clip path scoped to block bounds -->
                    <defs>
                      <clipPath :id="'mclip-' + entry.tripId">
                        <rect :x="mbx(entry)" :y="mby(entry)"
                              :width="mbw(entry)" :height="mbh(entry)" rx="5"/>
                      </clipPath>
                    </defs>

                    <!-- Drop shadow -->
                    <rect :x="mbx(entry) + 1" :y="mby(entry) + 2"
                          :width="mbw(entry)" :height="mbh(entry)"
                          fill="rgba(0,0,0,0.10)" rx="5"/>
                    <!-- Block body -->
                    <rect :x="mbx(entry)" :y="mby(entry)"
                          :width="mbw(entry)" :height="mbh(entry)"
                          :fill="entry.conflict ? '#c62828' : entry.overcapacity ? '#7b1fa2' : (entry.direction === 'OUTBOUND' ? '#1565c0' : '#e65100')"
                          :stroke="selectedItem && entry.stops.some(s => s.id === selectedItem.id) ? '#f97316' : 'transparent'"
                          stroke-width="2.5" rx="5"/>

                    <!-- Clipped content group -->
                    <g :clip-path="'url(#mclip-' + entry.tripId + ')'">

                      <!-- Line 1: Trip name + direction arrow -->
                      <text v-if="mbw(entry) >= 18"
                            :x="mbx(entry) + 8" :y="mby(entry) + 16"
                            fill="white" font-size="12"
                            font-weight="700" dominant-baseline="middle"
                            style="user-select:none;pointer-events:none">
                        {{ entry.direction === 'OUTBOUND' ? '\u2192' : '\u2190' }} {{ entry.tripName || (entry.direction === 'OUTBOUND' ? 'To' : 'From') }}
                      </text>

                      <!-- Stop names — listed vertically, capped by available height -->
                      <template v-for="(label, si) in entry.stopLabels" :key="'sl'+si">
                        <text v-if="mbw(entry) >= 40 && (mby(entry) + 34 + si * 18) < (mby(entry) + mbh(entry) - 22)"
                              :x="mbx(entry) + 8"
                              :y="mby(entry) + 33 + si * 18"
                              fill="white" font-size="13" font-weight="700"
                              dominant-baseline="middle"
                              style="user-select:none;pointer-events:none">
                          {{ entry.stopLabels.length > 1 ? '• ' : '' }}{{ label }}
                        </text>
                      </template>
                      <!-- "+N more" if truncated -->
                      <text v-if="entry.stopLabels.length > Math.floor((mbh(entry) - 56) / 18) && Math.floor((mbh(entry) - 56) / 18) > 0"
                            :x="mbx(entry) + 8"
                            :y="mby(entry) + 33 + Math.floor((mbh(entry) - 56) / 18) * 18"
                            fill="rgba(255,255,255,0.75)" font-size="11" font-weight="600"
                            dominant-baseline="middle"
                            style="user-select:none;pointer-events:none">
                        +{{ entry.stopLabels.length - Math.floor((mbh(entry) - 56) / 18) }} more
                      </text>

                      <!-- Bottom: Time range + total headcount -->
                      <text v-if="mbw(entry) >= 60 && mbh(entry) >= 40"
                            :x="mbx(entry) + 8" :y="mby(entry) + mbh(entry) - 10"
                            fill="rgba(255,255,255,0.85)" font-size="12"
                            dominant-baseline="middle"
                            style="user-select:none;pointer-events:none">
                        {{ fmtTime(entry.start) }}–{{ fmtTime(entry.end) }} · {{ entry.headcount }} pax
                      </text>

                      <!-- Driver holding the vehicle for this trip (WI-001577) -->
                      <text v-if="mbw(entry) >= 60 && mbh(entry) >= 58"
                            :x="mbx(entry) + 8" :y="mby(entry) + mbh(entry) - 25"
                            fill="rgba(255,255,255,0.95)" font-size="11"
                            :font-weight="handoverAt(vehicle.id, entry.start) ? '700' : '400'"
                            dominant-baseline="middle"
                            style="user-select:none;pointer-events:none">
                        {{ handoverAt(vehicle.id, entry.start) ? '⇄ ' : '' }}{{ blockDriver(entry, vehicle) }}
                      </text>

                    </g>

                    <!-- Resize handle (outside clip for visibility) -->
                    <rect v-if="mbw(entry) >= 24"
                          :x="mbx(entry) + mbw(entry) - 5" :y="mby(entry) + 4"
                          width="3" :height="mbh(entry) - 8"
                          fill="rgba(255,255,255,0.22)" rx="1.5"
                          style="cursor:ew-resize;pointer-events:none"/>
                  </g>
                </template>

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
            <span v-if="selectedItem.tripName" class="rp-dir-badge" style="background:#e8f5e9;color:#2e7d32">
              {{ selectedItem.tripName }}
            </span>
            <span v-if="selectedTripStops.length > 0" class="rp-dir-badge" style="background:#f3e8fd;color:#7c3aed">
              {{ selectedTripStops.length }} Stops
            </span>
            <span class="rp-dir-badge" style="background:#e3f2fd;color:#1565c0">
              {{ vehicleLabelForItem(selectedItem) }}
            </span>
          </div>

          <!-- ═══ TRIP VIEW: multiple stops ═══ -->
          <template v-if="selectedTripStops.length > 0">

            <!-- Trip time summary -->
            <div class="rp-detail-card">
              <div class="rp-detail-row-label" style="padding:0 0 6px 0">{{ selectedItem.tripName ? selectedItem.tripName + ' — ' : '' }}Trip Timeline</div>
              <div class="rp-detail-time-display">
                {{ fmtISO(new Date(selectedTripStops[0].item.start).toISOString()) }}
                <span class="rp-detail-time-arrow">\u2192</span>
                {{ fmtISO(new Date(selectedTripStops[selectedTripStops.length - 1].item.end).toISOString()) }}
                <span class="rp-detail-time-dur">({{ Math.round((new Date(selectedTripStops[selectedTripStops.length - 1].item.end) - new Date(selectedTripStops[0].item.start)) / 60000) }} min)</span>
              </div>
            </div>

            <!-- Stops grouped under their pickup accommodation camp banner -->
            <template v-for="(camp, ci) in selectedTripStopsByCamp" :key="'camp_' + ci">

              <!-- Accommodation camp banner: everything below it boards at this camp -->
              <div class="rp-detail-card" style="background:#eef2ff;border-color:#c7d2fe">
                <div style="display:flex;align-items:center;justify-content:space-between">
                  <div style="display:flex;align-items:center;gap:8px">
                    <span class="rp-icon" style="font-size:18px;color:#4338ca">home</span>
                    <div style="font-size:13px;font-weight:700;color:#111">{{ camp.accommodation }}</div>
                  </div>
                  <div class="rp-detail-row-label" style="margin:0">
                    {{ camp.stops.length }} stop<span v-if="camp.stops.length !== 1">s</span>
                    · {{ camp.stops.reduce((sum, s) => sum + ((s.card.employees || []).length), 0) }} pax
                  </div>
                </div>
              </div>

              <!-- Each stop under this camp (draggable for reorder) -->
              <div v-for="stop in camp.stops" :key="stop.item.id"
                   class="rp-detail-card rp-stop-draggable"
                   draggable="true"
                   @dragstart="onStopDragStart($event, stop.stopNum - 1)"
                   @dragover.prevent="onStopDragOver($event, stop.stopNum - 1)"
                   @dragend="onStopDragEnd($event)"
                   @drop.prevent="onStopDrop($event, stop.stopNum - 1)"
                   :class="{ 'rp-stop-drag-over': stopDragOverIndex === (stop.stopNum - 1) && stopDragSourceIndex !== null && stopDragSourceIndex !== (stop.stopNum - 1) }"
                   :style="'border-left:3px solid ' + (stop.item.id === selectedItem.id ? '#f97316' : '#1565c0')">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                  <span class="rp-icon rp-stop-drag-handle" title="Drag to reorder">drag_indicator</span>
                  <span class="rp-stop-num rp-stop-num-out">{{ stop.stopNum }}</span>
                  <div style="font-size:13px;font-weight:700;color:#111">{{ stop.card.site_location || 'Unknown' }}</div>
                </div>
                <div class="rp-detail-row" style="padding:4px 0 3px 30px">
                  <div class="rp-detail-row-icon"><span class="rp-icon">schedule</span></div>
                  <div class="rp-detail-row-content">
                    <div class="rp-detail-row-label">Shift</div>
                    <div class="rp-detail-row-value">{{ stop.card.shift_name || '—' }}</div>
                  </div>
                </div>
                <div class="rp-detail-row" style="padding:4px 0 3px 30px">
                  <div class="rp-detail-row-icon"><span class="rp-icon">location_on</span></div>
                  <div class="rp-detail-row-content">
                    <div class="rp-detail-row-label">Stop Location</div>
                    <div class="rp-detail-row-value">{{ stop.card.stop_location || '—' }}</div>
                  </div>
                </div>
                <!-- Passenger breakdown for this camp stop (AC5): how many board here -->
                <div class="rp-detail-row" style="padding:4px 0 3px 30px">
                  <div class="rp-detail-row-icon"><span class="rp-icon">group</span></div>
                  <div class="rp-detail-row-content">
                    <div class="rp-detail-row-label">Boarding at this stop</div>
                    <div class="rp-detail-row-value">
                      {{ (stop.card.employees || []).length - relieverCount(stop.card.employees) }} regular
                      <span v-if="relieverCount(stop.card.employees) > 0">
                        · {{ relieverCount(stop.card.employees) }} reliever
                      </span>
                      <span class="rp-detail-row-label" style="display:inline">({{ (stop.card.employees || []).length }} total)</span>
                    </div>
                  </div>
                </div>
                <div style="display:flex;gap:6px;margin:6px 0 0 30px">
                  <div class="rp-time-pill rp-time-pill-start">
                    {{ fmtISO(new Date(stop.item.start).toISOString()) }}
                  </div>
                  <span class="rp-detail-time-arrow"><span class="rp-icon" style="font-size:12px">arrow_forward</span></span>
                  <div class="rp-time-pill rp-time-pill-end">
                    {{ fmtISO(new Date(stop.item.end).toISOString()) }}
                  </div>
                </div>

                <!-- Passenger manifest for this camp stop (AC6): regular vs reliever -->
                <div class="rp-detail-emp-list" style="margin:8px 0 0 30px" v-if="stop.card.employees && stop.card.employees.length">
                  <span v-for="(e, ei) in stop.card.employees" :key="stop.stopNum + '_' + ei"
                        class="rp-emp-chip rp-emp-chip-call"
                        :class="{ 'rp-emp-chip-reliever': empIsReliever(e) }"
                        @click.stop="handleEmployeeCall(e)"
                        :title="empMobile(e) ? 'Call ' + empMobile(e) : 'No mobile number'">
                    <span class="rp-emp-tag" :class="empIsReliever(e) ? 'rp-emp-tag-reliever' : 'rp-emp-tag-regular'">{{ empIsReliever(e) ? 'Reliever' : 'Regular' }}</span>
                    {{ empName(e) }}
                    <span class="rp-icon rp-call-icon" :class="empMobile(e) ? '' : 'rp-call-disabled'">call</span>
                  </span>
                </div>
              </div>

            </template>

            <!-- Trip-wide passenger total (regular vs reliever across all stops) -->
            <div class="rp-detail-card">
              <div class="rp-detail-row-label" style="padding:0 0 6px 0"><span class="rp-icon" style="font-size:16px">group</span> Trip Total</div>
              <div class="rp-detail-row-value">
                {{ selectedTripStops.reduce((sum, s) => sum + ((s.card.employees || []).length - relieverCount(s.card.employees)), 0) }} regular
                · {{ selectedTripStops.reduce((sum, s) => sum + relieverCount(s.card.employees), 0) }} reliever
                <span class="rp-detail-row-label" style="display:inline">({{ selectedTripStops.reduce((sum, s) => sum + (s.card.employees || []).length, 0) }} passengers)</span>
              </div>
            </div>
          </template>

          <!-- ═══ SINGLE ITEM VIEW (non-trip) ═══ -->
          <template v-else>

            <!-- Type badge -->
            <div v-if="selectedCard.type === 'OLM'" class="rp-detail-card" style="background:#f3e8fd;border-color:#e0cffc;padding:8px 12px">
              <div style="display:flex;align-items:center;gap:6px">
                <span class="rp-icon" style="font-size:14px">location_on</span>
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
                  <span class="rp-stop-num rp-stop-num-olm">{{ si + 1 }}</span>
                  <div class="rp-detail-row-value" style="font-weight:600">{{ s.site }}</div>
                </div>
                <div style="font-size:11px;color:#888;margin-left:30px" v-for="sh in s.shifts" :key="sh">
                  <span class="rp-icon" style="font-size:14px">schedule</span> {{ sh }}
                </div>
              </div>
            </template>

            <!-- OLM accommodation -->
            <div v-if="selectedCard.type === 'OLM'" class="rp-detail-card">
              <div class="rp-detail-row" style="border:none;padding:4px 0">
                <div class="rp-detail-row-icon"><span class="rp-icon">home</span></div>
                <div class="rp-detail-row-content">
                  <div class="rp-detail-row-label">Accommodation</div>
                  <div class="rp-detail-row-value">{{ selectedCard.accommodation }}</div>
                </div>
              </div>
            </div>

            <!-- DIRECT / OSM: Simple info card -->
            <div v-if="selectedCard.type !== 'OLM'" class="rp-detail-card">
              <div class="rp-detail-row">
                <div class="rp-detail-row-icon"><span class="rp-icon">business</span></div>
                <div class="rp-detail-row-content">
                  <div class="rp-detail-row-label">Site</div>
                  <div class="rp-detail-row-value">{{ selectedCard.site_location }}</div>
                </div>
              </div>
              <div class="rp-detail-row">
                <div class="rp-detail-row-icon"><span class="rp-icon">schedule</span></div>
                <div class="rp-detail-row-content">
                  <div class="rp-detail-row-label">Shift</div>
                  <div class="rp-detail-row-value">{{ selectedCard.shift_name }}</div>
                </div>
              </div>
              <div class="rp-detail-row">
                <div class="rp-detail-row-icon"><span class="rp-icon">location_on</span></div>
                <div class="rp-detail-row-content">
                  <div class="rp-detail-row-label">Stop Location</div>
                  <div class="rp-detail-row-value">{{ selectedCard.stop_location }}</div>
                </div>
              </div>
              <div class="rp-detail-row">
                <div class="rp-detail-row-icon"><span class="rp-icon">home</span></div>
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
                <span class="rp-detail-time-arrow"><span class="rp-icon" style="font-size:14px">arrow_forward</span></span>
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

            <!-- Employees (regular vs reliever) -->
            <div class="rp-detail-card">
              <div class="rp-detail-row-label" style="padding:0 0 4px 0"><span class="rp-icon" style="font-size:16px">group</span> Employees ({{ selectedCard.headcount }})</div>
              <div class="rp-detail-row-value" style="padding:0 0 8px 0">
                {{ (selectedCard.employees || []).length - relieverCount(selectedCard.employees) }} regular
                <span v-if="relieverCount(selectedCard.employees) > 0">· {{ relieverCount(selectedCard.employees) }} reliever</span>
              </div>
              <div class="rp-detail-emp-list">
                <span v-for="(e, ei) in selectedCard.employees" :key="'emp_' + ei"
                      class="rp-emp-chip rp-emp-chip-call"
                      :class="{ 'rp-emp-chip-reliever': empIsReliever(e) }"
                      @click.stop="handleEmployeeCall(e)"
                      :title="empMobile(e) ? 'Call ' + empMobile(e) : 'No mobile number'">
                  <span class="rp-emp-tag" :class="empIsReliever(e) ? 'rp-emp-tag-reliever' : 'rp-emp-tag-regular'">{{ empIsReliever(e) ? 'Reliever' : 'Regular' }}</span>
                  {{ empName(e) }}
                  <span class="rp-icon rp-call-icon" :class="empMobile(e) ? '' : 'rp-call-disabled'">call</span>
                </span>
              </div>
            </div>

          </template>

        </div>

        <div id="rp-detail-footer">
          <button v-if="!selectedItem.tripId" class="rp-detail-btn rp-detail-btn-primary" @click="mergeSelectedBlock" style="background-color: var(--rp-color-trip-chain); border-color: var(--rp-color-trip-chain);">
            <span class="rp-icon">merge_type</span> Merge into Trip
          </button>
          <button class="rp-detail-btn rp-detail-btn-primary" @click="reassignSelectedBlock">
            <span class="rp-icon">directions_bus</span> Reassign Vehicle
          </button>
          <button class="rp-detail-btn rp-detail-btn-danger" @click="removeSelectedFromLane">
            <span class="rp-icon">close</span> Remove from Lane
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
        /* ── M3 Design Tokens ── */
        #rp-shell {
            /* M3 Color Tokens (orange 24° primary) */
            --md-sys-color-primary: #9a4500;
            --md-sys-color-on-primary: #ffffff;
            --md-sys-color-primary-container: #ffdbca;
            --md-sys-color-on-primary-container: #341100;
            --md-sys-color-secondary: #765749;
            --md-sys-color-on-secondary: #ffffff;
            --md-sys-color-secondary-container: #ffdbca;
            --md-sys-color-tertiary: #636032;
            --md-sys-color-error: #ba1a1a;
            --md-sys-color-on-error: #ffffff;
            --md-sys-color-error-container: #ffdad6;
            --md-sys-color-surface: #ffffff;
            --md-sys-color-on-surface: #1f1f1f;
            --md-sys-color-on-surface-variant: #525252;
            --md-sys-color-outline: #737373;
            --md-sys-color-outline-variant: #e2e2e2;
            --md-sys-color-surface-container: #f4f4f5;
            --md-sys-color-surface-container-low: #fafafa;
            --md-sys-color-surface-container-high: #f0f0f0;
            --md-sys-color-surface-bright: #ffffff;
            --md-sys-color-inverse-surface: #303030;
            --md-sys-color-inverse-on-surface: #f5f5f5;

            /* Semantic role colors */
            --rp-color-outbound: #1565c0;
            --rp-color-outbound-container: #dbeafe;
            --rp-color-return: #e65100;
            --rp-color-return-container: #ffedd5;
            --rp-color-conflict: #c62828;
            --rp-color-conflict-container: #fee2e2;
            --rp-color-trip-chain: #7c3aed;
            --rp-color-trip-container: #f3e8fd;
            --rp-color-success: #2e7d32;
            --rp-color-success-container: #e8f5e9;
            --rp-color-warning: #e65100;
            --rp-color-warning-container: #fff3e0;
            --rp-color-accent: #f97316;

            /* M3 Elevation */
            --md-sys-elevation-1: 0 1px 2px rgba(0,0,0,0.3), 0 1px 3px 1px rgba(0,0,0,0.15);
            --md-sys-elevation-2: 0 1px 2px rgba(0,0,0,0.3), 0 2px 6px 2px rgba(0,0,0,0.15);
            --md-sys-elevation-3: 0 4px 8px 3px rgba(0,0,0,0.15), 0 1px 3px rgba(0,0,0,0.3);

            /* M3 Motion */
            --md-sys-motion-easing-standard: cubic-bezier(0.2, 0, 0, 1);
            --md-sys-motion-duration-short: 150ms;
            --md-sys-motion-duration-medium: 200ms;
            --md-sys-motion-duration-long: 250ms;

            /* Shell layout */
            display: flex; flex-direction: column; height: 100vh;
            background: var(--md-sys-color-surface-container);
            font-family: 'Google Sans', Roboto, sans-serif;
            overflow: hidden;
        }

        /* ── Material Symbols icon helper ── */
        .rp-icon {
            font-family: 'Material Symbols Outlined';
            font-size: 18px;
            font-weight: normal;
            font-style: normal;
            line-height: 1;
            letter-spacing: normal;
            text-transform: none;
            display: inline-block;
            white-space: nowrap;
            word-wrap: normal;
            direction: ltr;
            vertical-align: middle;
            -webkit-font-smoothing: antialiased;
        }
        .rp-meta-icon .rp-icon { font-size: 16px; }
        .rp-detail-row-icon .rp-icon { font-size: 20px; }

        /* ── Header ── */
        #rp-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 24px; background: var(--md-sys-color-surface-bright);
            border-bottom: 1px solid var(--md-sys-color-outline-variant);
            box-shadow: var(--md-sys-elevation-1); flex-shrink: 0;
        }
        #rp-header-right { display: flex; align-items: center; gap: 8px; }
        #rp-title { font-size: 22px; font-weight: 500; color: var(--md-sys-color-on-surface); }
        #rp-date  { font-size: 12px; color: var(--md-sys-color-on-surface-variant); margin-top: 2px; }

        /* ── Buttons (Frappe-aligned) ── */
        .rp-btn {
            display: inline-flex; align-items: center; gap: 4px;
            padding: 5px 10px; border-radius: 6px;
            border: 1px solid transparent;
            font-size: 12px; font-weight: 500; line-height: 1.5;
            cursor: pointer; white-space: nowrap;
            user-select: none; vertical-align: middle;
            transition: background 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        }
        .rp-btn:focus-visible { outline: 2px solid var(--rp-color-accent); outline-offset: 2px; }
        .rp-btn:active:not(:disabled) { box-shadow: inset 0 3px 5px rgba(0,0,0,.125); }
        .rp-btn[disabled] { pointer-events: none; cursor: not-allowed; opacity: 0.65; }

        /* Primary — Frappe blue */
        .rp-btn-primary {
            background-color: var(--primary, #5e64ff); color: #fff;
            border-color: var(--primary, #444bff);
        }
        .rp-btn-primary:hover:not(:disabled) {
            background-color: #2b33ff; border-color: #0711ff;
        }
        .rp-btn-primary:disabled { background-color: var(--primary, #5e64ff); border-color: var(--primary, #444bff); }

        /* Default — Frappe gray */
        .rp-btn-default {
            background-color: #f0f4f7; color: inherit;
            border-color: transparent;
        }
        .rp-btn-default:hover:not(:disabled) { background-color: #cfdce5; }

        /* Success — green status actions */
        .rp-btn-success {
            background-color: #98d85b; color: #fff;
            border-color: #8bd346;
        }
        .rp-btn-success:hover:not(:disabled) { background-color: #7ece32; border-color: #6db22a; }

        /* Warning — orange status actions */
        .rp-btn-warning {
            background-color: #ffa00a; color: #fff;
            border-color: #f09300;
        }
        .rp-btn-warning:hover:not(:disabled) { background-color: #d68300; border-color: #b26d00; }

        /* Danger — red */
        .rp-btn-danger {
            background-color: #ff5858; color: #fff;
            border-color: #ff3f3f; width: 100%;
        }
        .rp-btn-danger:hover:not(:disabled) { background-color: #ff2525; border-color: #ff0101; }

        /* Manifest — secondary default */
        .rp-btn-manifest { margin-left: 6px; background-color: #f0f4f7; color: inherit; border-color: transparent; }
        .rp-btn-manifest:hover:not(:disabled) { background-color: #cfdce5; }

        /* Helper classes for stop number badges */
        .rp-stop-num {
            font-size: 12px; font-weight: 700; border-radius: 50%;
            width: 22px; height: 22px; display: flex; align-items: center;
            justify-content: center; flex-shrink: 0;
        }
        .rp-stop-num-out { background: var(--rp-color-outbound-container); color: var(--rp-color-outbound); }
        .rp-stop-num-olm { background: var(--rp-color-trip-container); color: var(--rp-color-trip-chain); }

        /* Drag-to-reorder affordances */
        .rp-stop-drag-handle {
            cursor: grab; opacity: 0.35; font-size: 18px;
            transition: opacity 0.15s; flex-shrink: 0;
            color: var(--md-sys-color-on-surface-variant);
        }
        .rp-stop-draggable:hover .rp-stop-drag-handle { opacity: 0.7; }
        .rp-stop-draggable:active .rp-stop-drag-handle { cursor: grabbing; }
        .rp-stop-drag-over {
            border-top: 2.5px solid var(--rp-color-trip-chain) !important;
            padding-top: 10px;
            transition: border-top 0.12s, padding-top 0.12s;
        }

        /* Helper: time pill badges */
        .rp-time-pill {
            font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600;
        }
        .rp-time-pill-start { background: var(--rp-color-success-container); color: var(--rp-color-success); }
        .rp-time-pill-end   { background: var(--rp-color-warning-container); color: var(--rp-color-warning); }

        /* ── Body ── */
        #rp-body { display: flex; flex: 1; overflow: hidden; }

        /* ── Pool Panel ── */
        #rp-pool-panel {
            width: 300px; min-width: 300px; background: var(--md-sys-color-surface-bright);
            border-right: 1px solid var(--md-sys-color-outline-variant);
            display: flex; flex-direction: column; overflow: hidden;
        }
        #rp-pool-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 16px; border-bottom: 1px solid var(--md-sys-color-surface-container-high); flex-shrink: 0;
        }
        #rp-pool-title {
            font-size: 11px; font-weight: 700; text-transform: uppercase;
            letter-spacing: .10em; color: var(--md-sys-color-on-surface-variant);
        }
        #rp-pool-count { font-size: 11px; color: var(--md-sys-color-outline); }
        #rp-pool-search { padding: 8px 12px; border-bottom: 1px solid var(--md-sys-color-surface-container-high); flex-shrink: 0; }
        #rp-search-input {
            width: 100%; padding: 7px 12px;
            border: 1px solid var(--md-sys-color-outline-variant); border-radius: 8px;
            font-size: 14px; outline: none;
            transition: border-color var(--md-sys-motion-duration-medium) var(--md-sys-motion-easing-standard);
            box-sizing: border-box;
        }
        #rp-search-input:focus { border-color: var(--rp-color-accent); }
        #rp-pool-groups { flex: 1; overflow-y: auto; padding: 4px 0; }
        .rp-pool-empty  { padding: 36px 16px; text-align: center; font-size: 14px; color: var(--md-sys-color-outline); }

        /* Pool groups */
        .rp-pool-group  { }
        .rp-group-header {
            display: flex; align-items: center; padding: 8px 14px;
            cursor: pointer; user-select: none;
            background: var(--md-sys-color-surface-container-low);
            border-top: 1px solid var(--md-sys-color-surface-container-high); border-bottom: 1px solid var(--md-sys-color-surface-container-high);
            transition: background var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard);
        }
        .rp-group-header:hover { background: var(--md-sys-color-surface-container-high); }
        .rp-group-label   { flex: 1; font-size: 12px; font-weight: 700; color: var(--md-sys-color-on-surface); }
        .rp-group-count   { font-size: 11px; color: var(--md-sys-color-outline); margin-right: 6px; }
        .rp-group-chevron { font-size: 11px; color: var(--md-sys-color-outline); }
        .rp-group-cards   {
            display: flex; flex-direction: column; gap: 8px; padding: 8px 10px;
        }

        /* Cards */
        /* WI-001732: distinct colour for Unassigned Outbound vs Return cards */
        .rp-card-out { border-left: 4px solid #1565c0; }
        .rp-card-ret { border-left: 4px solid #c62828; }
        .rp-card {
            background: var(--md-sys-color-surface-bright); border: 1px solid var(--md-sys-color-outline-variant); border-radius: 12px;
            padding: 11px 12px; cursor: grab;
            transition: box-shadow var(--md-sys-motion-duration-medium) var(--md-sys-motion-easing-standard),
                        transform var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard),
                        border-color var(--md-sys-motion-duration-medium) var(--md-sys-motion-easing-standard);
            box-shadow: var(--md-sys-elevation-1);
        }
        .rp-card:hover  {
            box-shadow: var(--md-sys-elevation-3);
            transform: translateY(-1px);
            border-color: var(--md-sys-color-outline);
        }
        .rp-card:active { cursor: grabbing; }
        .rp-card:focus-visible { outline: 2px solid var(--rp-color-accent); outline-offset: 2px; }
        .rp-card-selected {
            border-color: var(--rp-color-accent) !important;
            box-shadow: 0 0 0 2px rgba(249,115,22,.25), 0 4px 12px rgba(249,115,22,.15) !important;
            transform: scale(1.01);
        }
        .rp-card-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
        .rp-card-site   { font-size: 14px; font-weight: 600; color: var(--md-sys-color-on-surface); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .rp-card-type   { font-size: 11px; font-weight: 700; letter-spacing: .06em; padding: 2px 7px; border-radius: 4px; flex-shrink: 0; }
        .rp-card-dir    { font-size: 10px; font-weight: 700; letter-spacing: .04em; padding: 2px 7px; border-radius: 4px; text-transform: uppercase; flex-shrink: 0; }
        .rp-dir-out     { background: #e3f2fd; color: #1565c0; }
        .rp-dir-ret     { background: #fce4ec; color: #c62828; }
        .rp-tag-osm     { background: var(--rp-color-outbound-container); color: var(--rp-color-outbound); }
        .rp-tag-olm     { background: var(--rp-color-trip-container); color: var(--rp-color-trip-chain); }
        .rp-card-shift  { font-size: 12px; color: var(--md-sys-color-on-surface-variant); margin-bottom: 7px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .rp-card-meta   { display: flex; flex-direction: column; gap: 2px; margin-bottom: 8px; }
        .rp-card-meta-item { font-size: 12px; color: var(--md-sys-color-on-surface-variant); display: flex; align-items: center; gap: 5px; }
        .rp-meta-icon   { font-size: 14px; }
        .rp-card-windows{ display: flex; gap: 5px; margin-bottom: 8px; }
        .rp-window      { flex: 1; border-radius: 6px; padding: 4px 8px; }
        .rp-window-out  { background: var(--rp-color-success-container); }
        .rp-window-ret  { background: var(--rp-color-warning-container); }
        .rp-window-label{ display: block; font-size: 11px; font-weight: 700; letter-spacing: .08em; color: var(--md-sys-color-on-surface-variant); }
        .rp-window-time { display: block; font-size: 12px; font-weight: 600; color: var(--md-sys-color-on-surface); }
        .rp-card-employees { display: flex; flex-wrap: wrap; gap: 3px; }
        .rp-emp-chip    { font-size: 11px; background: var(--md-sys-color-surface-container); border: 1px solid var(--md-sys-color-outline-variant); border-radius: 4px; padding: 2px 6px; color: var(--md-sys-color-on-surface-variant); display: inline-flex; align-items: center; gap: 3px; }
        .rp-emp-more    { background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-outline); }
        .rp-emp-chip-call { cursor: pointer; transition: border-color 0.15s, background 0.15s; }
        .rp-emp-chip-call:hover { border-color: var(--rp-color-success); background: rgba(34,197,94,0.06); }
        .rp-call-icon { font-size: 13px !important; color: var(--rp-color-success); transition: color 0.15s; }
        .rp-emp-chip-call:hover .rp-call-icon { color: #16a34a; }
        .rp-call-disabled { color: var(--md-sys-color-outline) !important; opacity: 0.35; cursor: default; }

        /* ── Regular vs Reliever passenger labels (MA3-12 AC6) ── */
        .rp-emp-chip-reliever { border-color: #c084fc; background: rgba(124,58,237,0.06); }
        .rp-emp-chip-reliever:hover { border-color: var(--rp-color-trip-chain); background: rgba(124,58,237,0.12); }
        .rp-emp-tag { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; border-radius: 3px; padding: 1px 4px; line-height: 1.4; }
        .rp-emp-tag-regular  { background: var(--rp-color-outbound-container); color: var(--rp-color-outbound); }
        .rp-emp-tag-reliever { background: var(--rp-color-trip-container); color: var(--rp-color-trip-chain); }

        /* ── Timeline Panel ── */
        #rp-timeline-panel {
            flex: 1; display: flex; flex-direction: column;
            overflow: hidden; min-width: 0;
        }
        #rp-timeline-toolbar {
            display: flex; align-items: center; justify-content: space-between;
            padding: 8px 14px; background: var(--md-sys-color-surface-bright);
            border-bottom: 1px solid var(--md-sys-color-outline-variant); flex-shrink: 0; gap: 12px;
        }
        #rp-timeline-zoom { display: flex; gap: 4px; }
        .rp-btn-icon {
            padding: 5px 10px; border: 1px solid #d1d5db; border-radius: 6px;
            background: #f0f4f7; cursor: pointer; font-size: 12px; color: inherit;
            line-height: 1.5; transition: background 0.15s ease;
        }
        .rp-btn-icon:hover { background: #cfdce5; border-color: #adb5bd; }
        .rp-btn-icon:focus-visible { outline: 2px solid var(--rp-color-accent); outline-offset: 2px; }
        .rp-btn-icon-label { font-weight: 600; font-size: 11px; display: inline-flex; align-items: center; gap: 3px; }
        .rp-tb-hint { font-size: 12px; color: var(--md-sys-color-outline); flex: 1; text-align: center; }
        #rp-timeline-legend { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
        .rp-legend-item     { font-size: 11px; padding: 2px 9px; border-radius: 4px; font-weight: 600; }
        .rp-legend-out      { background: var(--rp-color-outbound-container); color: var(--rp-color-outbound); }
        .rp-legend-ret      { background: var(--rp-color-return-container); color: var(--rp-color-return); }
        .rp-legend-conflict { background: var(--rp-color-conflict-container); color: var(--rp-color-conflict); }
        .rp-legend-overcap { background: #f3e5f5; color: #7b1fa2; }

        /* ── Grid ── */
        #rp-grid-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

        /* Sticky axis */
        #rp-axis-row {
            display: flex; align-items: stretch; background: var(--md-sys-color-surface-bright);
            border-bottom: 2px solid var(--md-sys-color-outline-variant); flex-shrink: 0;
        }
        #rp-axis-wrap { flex: 1; overflow: hidden; min-width: 0; }

        /* Lane label column */
        .rp-lane-label {
            width: 200px; min-width: 200px; flex-shrink: 0;
            padding: 6px 14px; border-right: 1px solid var(--md-sys-color-outline-variant);
            display: flex; flex-direction: column; justify-content: center;
        }
        .rp-label-stub { background: var(--md-sys-color-surface-container-low); min-height: 44px; }

        /* Scrollable lanes */
        #rp-lanes-area { flex: 1; overflow-y: auto; overflow-x: hidden; }
        .rp-lane-row   {
            display: flex; align-items: stretch;
            border-bottom: 1px solid var(--md-sys-color-surface-container-high);
            transition: background var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard);
        }
        .rp-lane-alt   { background: var(--md-sys-color-surface-container-low); }
        .rp-lane-row:hover { background: rgba(249,115,22,.015); }
        .rp-lane-drop-target { background: rgba(33,150,243,0.10) !important; outline: 2px dashed #2196f3; outline-offset: -2px; }
        .rp-lane-svg-wrap  { flex: 1; overflow: hidden; min-width: 0; }
        .rp-lane-svg       { display: block; }

        .rp-gv-plate { font-size: 14px; font-weight: 700; color: var(--md-sys-color-on-surface); }
        .rp-lock-badge { font-size: 12px; margin-left: 4px; vertical-align: middle; }
        .rp-lock-upcoming { font-size: 10px; margin-left: 4px; padding: 1px 5px; border-radius: 8px; background: rgba(124,58,237,0.12); color: #7c3aed; white-space: nowrap; vertical-align: middle; }
        .rp-lane-locked .rp-lane-label { background: rgba(120,120,120,0.08); }
        .rp-gv-lp    { font-size: 11px; font-weight: 500; color: var(--md-sys-color-outline); margin-top: 1px; }
        .rp-gv-meta  { font-size: 12px; color: var(--md-sys-color-on-surface-variant); margin-top: 1px; }
        .rp-gv-acc   { font-size: 11px; color: var(--md-sys-color-outline); margin-top: 1px; }

        .rp-block-grab     { cursor: grab; }
        .rp-block-grabbing { cursor: grabbing; }
        .rp-empty-state    { padding: 48px; text-align: center; font-size: 14px; color: var(--md-sys-color-outline); }

        /* ── Drag time tooltip (5-min snap) ── */
        .rp-drag-tooltip {
            position: fixed;
            z-index: 9999;
            pointer-events: none;
            background: rgba(0, 0, 0, 0.85);
            color: #fff;
            font-family: 'Google Sans', Roboto, monospace;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.04em;
            padding: 6px 14px;
            border-radius: 8px;
            white-space: nowrap;
            transform: translateX(-50%);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(4px);
            animation: rp-tooltip-in 0.1s ease-out;
        }
        @keyframes rp-tooltip-in {
            from { opacity: 0; transform: translateX(-50%) translateY(4px); }
            to   { opacity: 1; transform: translateX(-50%) translateY(0); }
        }

        /* ── Multi-stop hover popup ── */
        .rp-stop-hover {
            position: fixed;
            z-index: 9999;
            pointer-events: none;
            background: rgba(17, 24, 39, 0.94);
            color: #fff;
            font-family: 'Google Sans', Roboto, sans-serif;
            padding: 10px 12px;
            border-radius: 10px;
            max-width: 460px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(4px);
            animation: rp-tooltip-in 0.1s ease-out;
            transform: translateX(-50%);
        }
        .rp-stop-hover-title {
            font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
            text-transform: uppercase; color: rgba(255, 255, 255, 0.6);
            margin-bottom: 6px;
        }
        .rp-stop-hover-flow {
            display: flex; flex-wrap: wrap; align-items: center; gap: 4px 6px;
        }
        .rp-stop-hover-chip {
            display: inline-flex; align-items: center; gap: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 7px; padding: 4px 8px; font-size: 13px; white-space: nowrap;
        }
        .rp-stop-hover-seq {
            font-size: 10px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.04em; color: #93c5fd;
            background: rgba(59, 130, 246, 0.18); border-radius: 4px; padding: 1px 6px;
        }
        .rp-stop-hover-acc  { font-weight: 600; }
        .rp-stop-hover-pax  { color: #86efac; font-weight: 700; }
        .rp-stop-hover-arrow { color: rgba(255, 255, 255, 0.5); font-size: 15px; font-weight: 700; }

        /* ── Detail Panel ── */
        #rp-detail-panel {
            width: 0; min-width: 0; background: var(--md-sys-color-surface-container-low);
            border-left: 1px solid var(--md-sys-color-outline-variant);
            display: flex; flex-direction: column;
            transition: width var(--md-sys-motion-duration-long) var(--md-sys-motion-easing-standard),
                        min-width var(--md-sys-motion-duration-long) var(--md-sys-motion-easing-standard);
            overflow: hidden; flex-shrink: 0;
        }
        #rp-detail-panel.rp-detail-open { width: 320px; min-width: 320px; }

        #rp-detail-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px 16px; background: var(--md-sys-color-surface-bright); border-bottom: 1px solid var(--md-sys-color-outline-variant); flex-shrink: 0;
        }
        #rp-detail-title {
            font-size: 12px; font-weight: 700; text-transform: uppercase;
            letter-spacing: .08em; color: var(--md-sys-color-on-surface-variant);
        }
        #rp-detail-close {
            background: none; border: none; cursor: pointer;
            font-size: 15px; color: var(--md-sys-color-outline); padding: 4px 8px; border-radius: 6px;
            transition: all var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard);
        }
        #rp-detail-close:hover { background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface); }
        #rp-detail-close:focus-visible { outline: 2px solid var(--rp-color-accent); outline-offset: 2px; }
        #rp-detail-body   { flex: 1; overflow-y: auto; padding: 12px; }
        #rp-detail-footer { padding: 12px 16px; background: var(--md-sys-color-surface-bright); border-top: 1px solid var(--md-sys-color-outline-variant); flex-shrink: 0; }

        .rp-detail-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }

        .rp-detail-card {
            background: var(--md-sys-color-surface-bright); border-radius: 10px; padding: 12px 14px;
            margin-bottom: 10px; border: 1px solid var(--md-sys-color-outline-variant);
        }
        .rp-detail-row {
            display: flex; align-items: flex-start; gap: 10px;
            padding: 7px 0; border-bottom: 1px solid var(--md-sys-color-surface-container);
        }
        .rp-detail-row:last-child { border-bottom: none; }
        .rp-detail-row-icon { font-size: 16px; width: 24px; text-align: center; flex-shrink: 0; margin-top: 1px; }
        .rp-detail-row-content { flex: 1; min-width: 0; }
        .rp-detail-row-label {
            font-size: 11px; font-weight: 700; text-transform: uppercase;
            letter-spacing: .08em; color: var(--md-sys-color-outline); margin-bottom: 2px;
        }
        .rp-detail-row-value { font-size: 14px; color: var(--md-sys-color-on-surface); font-weight: 500; word-break: break-word; }

        .rp-detail-time-display { font-size: 14px; font-weight: 600; color: var(--md-sys-color-on-surface); margin-bottom: 10px; }
        .rp-detail-time-arrow { color: var(--md-sys-color-outline); margin: 0 4px; }
        .rp-detail-time-dur { color: var(--md-sys-color-on-surface-variant); font-size: 12px; font-weight: 400; }

        .rp-detail-shift-pills { display: flex; gap: 8px; }
        .rp-detail-pill {
            flex: 1; border-radius: 8px; padding: 8px 10px; text-align: center;
        }
        .rp-detail-pill-start { background: var(--rp-color-success-container); }
        .rp-detail-pill-end   { background: var(--rp-color-warning-container); }
        .rp-detail-pill-label { font-size: 11px; font-weight: 700; letter-spacing: .06em; color: var(--md-sys-color-on-surface-variant); text-transform: uppercase; }
        .rp-detail-pill-value { font-size: 14px; font-weight: 600; color: var(--md-sys-color-on-surface); margin-top: 2px; }

        .rp-detail-emp-list { display: flex; flex-wrap: wrap; gap: 5px; }

        .rp-detail-btn-row { display: flex; gap: 6px; margin-bottom: 8px; }
        .rp-detail-btn {
            display: block; width: 100%; padding: 9px 0; border: none; border-radius: 8px;
            font-size: 13px; font-weight: 600; cursor: pointer;
            transition: all var(--md-sys-motion-duration-short) var(--md-sys-motion-easing-standard);
            text-align: center; margin-bottom: 6px;
        }
        .rp-detail-btn:last-child { margin-bottom: 0; }
        .rp-detail-btn:focus-visible { outline: 2px solid var(--rp-color-accent); outline-offset: 2px; }
        .rp-detail-btn-row .rp-detail-btn { flex: 1; margin-bottom: 0; }
        .rp-detail-btn-neutral  { background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface); }
        .rp-detail-btn-neutral:hover { background: var(--md-sys-color-surface-container); }
        .rp-detail-btn-neutral:disabled { opacity: .4; cursor: default; }
        .rp-detail-btn-primary  { background: var(--rp-color-outbound); color: var(--md-sys-color-on-primary); }
        .rp-detail-btn-primary:hover { background: #0d47a1; }
        .rp-detail-btn-danger   { background: var(--md-sys-color-error-container); color: var(--md-sys-color-error); border: 1px solid #fecaca; }
        .rp-detail-btn-danger:hover { background: #fef2f2; }

        .rp-detail-section { margin-bottom: 16px; }
        .rp-detail-label {
            font-size: 11px; font-weight: 700; text-transform: uppercase;
            letter-spacing: .10em; color: var(--md-sys-color-outline); margin-bottom: 3px;
        }
        .rp-detail-value { font-size: 14px; color: var(--md-sys-color-on-surface); line-height: 1.5; }

        .rp-dir-badge { font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 4px; display: inline-block; }
        .rp-dir-out   { background: var(--rp-color-outbound-container); color: var(--rp-color-outbound); }
        .rp-dir-ret   { background: var(--rp-color-return-container); color: var(--rp-color-return); }
        .rp-dir-trip  { background: var(--rp-color-trip-container); color: var(--rp-color-trip-chain); }

        /* ══════════════════════════════════════════════════════════════
           MOBILE RESPONSIVE (≤ 768px)
           ══════════════════════════════════════════════════════════════ */
        @media (max-width: 768px) {
            /* Shell: allow scroll on mobile */
            #rp-shell { height: auto; min-height: 100vh; overflow: auto; }

            /* Header: stack vertically */
            #rp-header {
                flex-direction: column; gap: 8px;
                padding: 10px 14px; align-items: stretch;
            }
            #rp-title { font-size: 16px; }
            #rp-date  { font-size: 11px; }
            .rp-btn { padding: 10px 16px; font-size: 14px; width: 100%; text-align: center; }

            /* Body: stack vertically instead of side-by-side */
            #rp-body { flex-direction: column; overflow: visible; }

            /* Pool panel: collapsible section on top */
            #rp-pool-panel {
                width: 100% !important; min-width: 0 !important;
                border-right: none; border-bottom: 1px solid #e2e2e2;
                max-height: 45vh; flex-shrink: 0;
            }
            #rp-pool-header { padding: 10px 12px; }
            .rp-card { padding: 10px; }
            .rp-card-site { font-size: 12px; }
            .rp-card-shift { font-size: 10px; }
            .rp-card-windows { flex-direction: column; gap: 4px; }
            .rp-card-employees { display: none; } /* Hide employee chips to save space */

            /* Timeline panel */
            #rp-timeline-panel { flex: none; min-height: 55vh; overflow: visible; }

            /* Timeline toolbar: wrap items */
            #rp-timeline-toolbar {
                flex-wrap: wrap; gap: 6px; padding: 6px 10px;
            }
            .rp-tb-hint { display: none; } /* Hide "Drag cards..." hint */
            #rp-timeline-legend { gap: 4px; }
            .rp-legend-item { font-size: 9px; padding: 2px 6px; }

            /* Lane labels: narrower */
            .rp-lane-label { width: 100px; min-width: 100px; padding: 4px 8px; }
            .rp-label-stub { min-height: 36px; }
            .rp-gv-plate { font-size: 11px; }
            .rp-gv-lp    { font-size: 9px; }
            .rp-gv-meta  { font-size: 9px; }
            .rp-gv-acc   { display: none; } /* Hide accommodation on label */

            /* Lane rows */
            .rp-lane-row { min-height: 60px; }

            /* Detail panel: full-screen overlay on mobile */
            #rp-detail-panel {
                position: fixed !important; top: 0; left: 0; right: 0; bottom: 0;
                width: 100% !important; min-width: 0 !important;
                z-index: 1050; border-left: none;
                transition: transform .25s ease;
                transform: translateY(100%);
            }
            #rp-detail-panel.rp-detail-open {
                width: 100% !important; min-width: 0 !important;
                transform: translateY(0);
            }
            #rp-detail-header { padding: 12px 14px; }
            #rp-detail-close { font-size: 18px; padding: 8px 12px; min-height: 44px; }
            #rp-detail-body { padding: 10px; }
            #rp-detail-footer { padding: 10px 12px; }
            .rp-detail-btn { padding: 12px 0; font-size: 14px; min-height: 44px; }
        }

        /* ══════════════════════════════════════════════════════════════
           SMALL MOBILE (≤ 480px)
           ══════════════════════════════════════════════════════════════ */
        @media (max-width: 480px) {
            #rp-header { padding: 8px 10px; }
            #rp-title { font-size: 14px; }

            /* Pool: shorter on very small screens */
            #rp-pool-panel { max-height: 35vh; }

            /* Lane labels: even narrower */
            .rp-lane-label { width: 75px; min-width: 75px; padding: 3px 6px; }
            .rp-gv-plate { font-size: 10px; }
            .rp-gv-lp    { display: none; }
            .rp-gv-meta  { display: none; }

            /* Zoom buttons */
            .rp-btn-icon { padding: 6px 10px; font-size: 16px; min-width: 36px; min-height: 36px; }

            /* Detail panel */
            .rp-detail-card { padding: 10px; }
            .rp-detail-row-icon { font-size: 14px; width: 20px; }
            .rp-detail-row-value { font-size: 12px; }
            .rp-detail-badges { gap: 4px; }
            .rp-dir-badge { font-size: 9px; padding: 2px 7px; }
        }

        /* ══════════════════════════════════════════════════════════════
           DARK MODE
           ══════════════════════════════════════════════════════════════ */
        #rp-shell.rp-dark {
            /* M3 Dark Color Tokens */
            --md-sys-color-primary: #ffb68e;
            --md-sys-color-on-primary: #552000;
            --md-sys-color-primary-container: #783100;
            --md-sys-color-on-primary-container: #ffdbca;
            --md-sys-color-secondary: #e7beaf;
            --md-sys-color-on-secondary: #442a1f;
            --md-sys-color-secondary-container: #5d4033;
            --md-sys-color-tertiary: #ceca93;
            --md-sys-color-error: #ffb4ab;
            --md-sys-color-on-error: #690005;
            --md-sys-color-error-container: #93000a;
            --md-sys-color-surface: #1a1a1a;
            --md-sys-color-on-surface: #e6e1e0;
            --md-sys-color-on-surface-variant: #d0c4bf;
            --md-sys-color-outline: #9a8e89;
            --md-sys-color-outline-variant: #52443e;
            --md-sys-color-surface-container: #242424;
            --md-sys-color-surface-container-low: #1f1f1f;
            --md-sys-color-surface-container-high: #2e2e2e;
            --md-sys-color-surface-bright: #2a2a2a;
            --md-sys-color-inverse-surface: #e6e1e0;
            --md-sys-color-inverse-on-surface: #1f1f1f;

            /* Dark semantic role colors */
            --rp-color-outbound: #64b5f6;
            --rp-color-outbound-container: #1a3a5c;
            --rp-color-return: #ffab76;
            --rp-color-return-container: #4a2800;
            --rp-color-conflict: #ff8a80;
            --rp-color-conflict-container: #4a0e0e;
            --rp-color-trip-chain: #b39ddb;
            --rp-color-trip-container: #2d1f4e;
            --rp-color-success: #81c784;
            --rp-color-success-container: #1a3a1c;
            --rp-color-warning: #ffab76;
            --rp-color-warning-container: #4a2800;
            --rp-color-accent: #fb8c00;

            /* Dark elevations */
            --md-sys-elevation-1: 0 1px 3px rgba(0,0,0,0.6), 0 1px 2px rgba(0,0,0,0.4);
            --md-sys-elevation-2: 0 2px 6px rgba(0,0,0,0.5), 0 1px 2px rgba(0,0,0,0.4);
            --md-sys-elevation-3: 0 4px 8px rgba(0,0,0,0.5), 0 1px 3px rgba(0,0,0,0.4);
        }

        /* ── Dark mode: Buttons ── */
        #rp-shell.rp-dark .rp-btn-default {
            background-color: #383838; color: #e0e0e0;
            border-color: #4a4a4a;
        }
        #rp-shell.rp-dark .rp-btn-default:hover:not(:disabled) {
            background-color: #444; border-color: #555;
        }
        #rp-shell.rp-dark .rp-btn-success {
            background-color: #2e7d32; color: #e8f5e9;
            border-color: #388e3c;
        }
        #rp-shell.rp-dark .rp-btn-warning {
            background-color: #e65100; color: #fff3e0;
            border-color: #ef6c00;
        }
        #rp-shell.rp-dark .rp-btn-icon {
            background: #383838; color: #e0e0e0; border-color: #4a4a4a;
        }
        #rp-shell.rp-dark .rp-btn-icon:hover { background: #444; }

        /* ── Dark mode: Pool panel ── */
        #rp-shell.rp-dark #rp-pool-panel { background: var(--md-sys-color-surface); border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark #rp-pool-header { border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark #rp-search-input {
            background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface);
            border-color: var(--md-sys-color-outline-variant);
        }
        #rp-shell.rp-dark #rp-search-input::placeholder { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-group-header { color: var(--md-sys-color-on-surface-variant); }
        #rp-shell.rp-dark .rp-group-header:hover { background: var(--md-sys-color-surface-container-high); }
        #rp-shell.rp-dark .rp-group-count { background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-outline); }

        /* ── Dark mode: Cards ── */
        #rp-shell.rp-dark .rp-card {
            background: var(--md-sys-color-surface-container); border-color: var(--md-sys-color-outline-variant);
        }
        #rp-shell.rp-dark .rp-card:hover { border-color: #64b5f6; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
        #rp-shell.rp-dark .rp-card-site { color: var(--md-sys-color-on-surface); }
        #rp-shell.rp-dark .rp-card-shift { color: var(--md-sys-color-on-surface-variant); }
        #rp-shell.rp-dark .rp-card-meta { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-tag-olm { background: #1a3a5c; color: #93c5fd; }
        #rp-shell.rp-dark .rp-tag-osm { background: #4a2800; color: #fdba74; }
        #rp-shell.rp-dark .rp-dir-out { background: #1a2744; color: #64b5f6; }
        #rp-shell.rp-dark .rp-dir-ret { background: #3e1e24; color: #ef9a9a; }
        #rp-shell.rp-dark .rp-window-out { background: #1a3a5c; }
        #rp-shell.rp-dark .rp-window-ret { background: #4a2800; }
        #rp-shell.rp-dark .rp-window-label { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-window-time { color: var(--md-sys-color-on-surface); }
        #rp-shell.rp-dark .rp-emp-chip { background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface-variant); border-color: var(--md-sys-color-outline-variant); }

        /* ── Dark mode: Timeline ── */
        #rp-shell.rp-dark #rp-timeline-panel { background: var(--md-sys-color-surface); }
        #rp-shell.rp-dark #rp-timeline-toolbar { border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark .rp-tb-hint { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark #rp-axis-row { background: var(--md-sys-color-surface-container); border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark .rp-lane-row { border-color: var(--md-sys-color-surface-container); }
        #rp-shell.rp-dark .rp-lane-alt { background: rgba(255,255,255,0.02); }
        #rp-shell.rp-dark .rp-lane-label { border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark .rp-gv-plate { color: var(--md-sys-color-on-surface); }
        #rp-shell.rp-dark .rp-gv-lp    { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-gv-meta { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-gv-acc { color: var(--md-sys-color-outline); }

        /* ── Dark mode: Legend ── */
        #rp-shell.rp-dark .rp-legend-out { background: #1a3a5c; color: #93c5fd; }
        #rp-shell.rp-dark .rp-legend-ret { background: #4a2800; color: #fdba74; }
        #rp-shell.rp-dark .rp-legend-conflict { background: #4a0e0e; color: #ff8a80; }
        #rp-shell.rp-dark .rp-legend-overcap { background: #2d1f4e; color: #ce93d8; }

        /* ── Dark mode: Detail Panel ── */
        #rp-shell.rp-dark #rp-detail-panel { background: var(--md-sys-color-surface); border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark #rp-detail-header { border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark #rp-detail-title { color: var(--md-sys-color-on-surface); }
        #rp-shell.rp-dark #rp-detail-close { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark #rp-detail-close:hover { background: var(--md-sys-color-surface-container-high); }
        #rp-shell.rp-dark .rp-detail-card { background: var(--md-sys-color-surface-container); border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark .rp-detail-row { border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark .rp-detail-row-label { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-detail-row-value { color: var(--md-sys-color-on-surface); }
        #rp-shell.rp-dark .rp-detail-row-icon { color: var(--md-sys-color-on-surface-variant); }
        #rp-shell.rp-dark .rp-detail-time-display { color: var(--md-sys-color-on-surface); }
        #rp-shell.rp-dark .rp-detail-time-arrow { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-detail-time-dur { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-time-pill-start { background: #1a3a5c; color: #93c5fd; }
        #rp-shell.rp-dark .rp-time-pill-end { background: #4a2800; color: #fdba74; }
        #rp-shell.rp-dark .rp-detail-pill-start { background: #1a3a5c; }
        #rp-shell.rp-dark .rp-detail-pill-end { background: #4a2800; }
        #rp-shell.rp-dark .rp-detail-pill-label { color: var(--md-sys-color-outline); }
        #rp-shell.rp-dark .rp-detail-pill-value { color: var(--md-sys-color-on-surface); }
        #rp-shell.rp-dark #rp-detail-footer { border-color: var(--md-sys-color-outline-variant); }
        #rp-shell.rp-dark .rp-detail-btn-primary { background: #1565c0; color: #e3f2fd; }
        #rp-shell.rp-dark .rp-detail-btn-primary:hover { background: #1976d2; }
        #rp-shell.rp-dark .rp-detail-btn-danger { background: #4a0e0e; color: #ff8a80; border-color: #6d1a1a; }
        #rp-shell.rp-dark .rp-detail-btn-danger:hover { background: #5a1212; }

        /* ── Dark mode: Direction badges ── */
        #rp-shell.rp-dark .rp-dir-out { background: #1a3a5c; color: #93c5fd; }
        #rp-shell.rp-dark .rp-dir-ret { background: #4a2800; color: #fdba74; }
        #rp-shell.rp-dark .rp-dir-trip { background: #2d1f4e; color: #ce93d8; }

        /* ── Dark mode: Stop number badges ── */
        #rp-shell.rp-dark .rp-stop-num-out { background: #1a3a5c; color: #93c5fd; }
        #rp-shell.rp-dark .rp-stop-num-olm { background: #2d1f4e; color: #ce93d8; }

        /* ── Dark mode: Icon-only button ── */
        .rp-btn-icon-only {
            display: inline-flex; align-items: center; justify-content: center;
            padding: 4px 8px; border-radius: 6px;
            border: 1px solid var(--md-sys-color-outline-variant);
            background: var(--md-sys-color-surface-container);
            color: var(--md-sys-color-on-surface-variant);
            cursor: pointer; font-size: 12px;
            transition: background 0.15s, color 0.15s;
        }
        .rp-btn-icon-only:hover {
            background: var(--md-sys-color-surface-container-high);
            color: var(--md-sys-color-on-surface);
        }
        .rp-btn-icon-only .rp-icon { font-size: 20px; }

        /* ── Dark mode: Plan selector ── */
        #rp-shell.rp-dark #rp-plan-selector select.form-control {
            background: var(--md-sys-color-surface-container-high); color: var(--md-sys-color-on-surface);
            border-color: var(--md-sys-color-outline-variant);
        }

        /* ── Dark mode: Pool empty state ── */
        #rp-shell.rp-dark .rp-pool-empty { color: var(--md-sys-color-outline); }

        /* ── Dark mode: Scrollbar ── */
        #rp-shell.rp-dark ::-webkit-scrollbar { width: 6px; }
        #rp-shell.rp-dark ::-webkit-scrollbar-track { background: transparent; }
        #rp-shell.rp-dark ::-webkit-scrollbar-thumb { background: #444; border-radius: 3px; }
        #rp-shell.rp-dark ::-webkit-scrollbar-thumb:hover { background: #555; }
    `;
    document.head.appendChild(s);
}