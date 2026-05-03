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
        const s  = document.createElement('script');
        s.id     = 'vue3-cdn';
        s.src    = 'https://unpkg.com/vue@3/dist/vue.global.prod.js';
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
            const planEnd   = new Date(data.global_end);
            return {
                planData:        data,
                // swimItems: { id, cardId, vehicleId, direction, start, end, headcount, conflict, tripId }
                swimItems:       [],
                assignedCards:   new Set(),   // reactive Set<cardId>
                windowStart:     new Date(planStart),
                windowEnd:       new Date(planEnd),
                planStart,
                planEnd,
                svgWidth:        800,         // updated by ResizeObserver
                rowHeight:       80,
                selectedItem:    null,        // highlighted swim block
                draggingCard:    null,        // card being dragged from pool
                isDraggingBlock: false,       // block being moved on lane
                searchQuery:     '',
                collapsedGroups: {},          // { [accommodation]: boolean }
                canSave:         false,
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
                    if (this.assignedCards.has(c.id)) return false;
                    if (!q) return true;
                    return (
                        c.shift_name.toLowerCase().includes(q)    ||
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
                const step15 = 15 * 60 * 1000;
                const origin = new Date(Math.ceil(this.windowStart.getTime() / step15) * step15);
                const ticks  = [];
                let t = new Date(origin);
                while (t <= this.windowEnd) {
                    const x = this.timeToX(t);
                    if (x >= -1 && x <= this.svgWidth + 1) {
                        const isMajor = t.getMinutes() === 0;
                        const isHalf  = t.getMinutes() === 30;
                        ticks.push({
                            key:    t.getTime(),
                            x,
                            isMajor,
                            label:  (isMajor || isHalf) ? this.fmtTime(t) : null
                        });
                    }
                    t = new Date(t.getTime() + step15);
                }
                return ticks;
            },

            itemsByVehicle() {
                const map = {};
                this.planData.vehicles.forEach(v => { map[v.id] = []; });
                this.swimItems.forEach(item => {
                    if (map[item.vehicleId] !== undefined) map[item.vehicleId].push(item);
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
                this.windowEnd   = new Date(c + h);
            },

            zoomOut() {
                const c    = (this.windowStart.getTime() + this.windowEnd.getTime()) / 2;
                const maxH = (this.planEnd - this.planStart) / 2;
                const h    = Math.min(maxH, this.windowDurationMs * 0.75);
                this.windowStart = new Date(Math.max(this.planStart.getTime(), c - h));
                this.windowEnd   = new Date(Math.min(this.planEnd.getTime(),   c + h));
            },

            fitAll() {
                this.windowStart = new Date(this.planStart);
                this.windowEnd   = new Date(this.planEnd);
            },

            onSvgWheel(e) {
                e.preventDefault();
                if (e.ctrlKey || e.metaKey) {
                    // ── Zoom to cursor position ──
                    const rect   = e.currentTarget.getBoundingClientRect();
                    const x      = Math.max(0, Math.min(this.svgWidth, e.clientX - rect.left));
                    const pivot  = this.xToTime(x);
                    const factor = e.deltaY > 0 ? 1.4 : 0.714;
                    const minDur = 30 * 60 * 1000;
                    const maxDur = this.planEnd - this.planStart;
                    const newDur = Math.min(maxDur, Math.max(minDur, this.windowDurationMs * factor));
                    const ratio  = x / this.svgWidth;
                    const newS   = pivot.getTime() - ratio * newDur;
                    this.windowStart = new Date(Math.max(this.planStart.getTime(), newS));
                    this.windowEnd   = new Date(Math.min(this.planEnd.getTime(), this.windowStart.getTime() + newDur));
                } else {
                    // ── Pan ──
                    const delta = (e.deltaX || e.deltaY) / this.svgWidth * this.windowDurationMs;
                    const newS  = this.windowStart.getTime() + delta;
                    const newE  = this.windowEnd.getTime()   + delta;
                    if (newS >= this.planStart.getTime() && newE <= this.planEnd.getTime()) {
                        this.windowStart = new Date(newS);
                        this.windowEnd   = new Date(newE);
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
                const rect     = e.currentTarget.getBoundingClientRect();
                const x        = Math.max(0, e.clientX - rect.left);
                const dropTime = this.xToTime(x);
                this.handleDrop(card, vehicle, dropTime);
            },

            handleDrop(card, vehicle, dropTime) {
                // ── Seat capacity check ──
                const usedSeats = this.swimItems
                    .filter(i => i.vehicleId === vehicle.id)
                    .reduce((sum, i) => sum + (i.headcount || 0), 0);

                if (usedSeats + card.headcount > vehicle.seats) {
                    frappe.show_alert({
                        message: `Not enough seats — ${vehicle.seats - usedSeats} remaining on ${vehicle.label}`,
                        indicator: 'red'
                    });
                    return;
                }

                // ── Overlap / multi-stop check ──
                const overlapping = this.findOverlappingOutbound(card, vehicle.id);
                if (overlapping.length > 0) {
                    frappe.confirm(
                        `${overlapping.length} existing shipment(s) on ${vehicle.label} share this time window. Group into a multi-stop trip?`,
                        () => this.groupIntoTrip(card, overlapping, vehicle.id),
                        () => this.placeCard(card, vehicle.id, dropTime)
                    );
                    return;
                }

                this.placeCard(card, vehicle.id, dropTime);
            },

            findOverlappingOutbound(card, vehicleId) {
                const cS = new Date(card.outbound_window_start).getTime();
                const cE = new Date(new Date(card.shift_start).getTime() - 10 * 60000).getTime();
                return this.swimItems.filter(i =>
                    i.vehicleId === vehicleId && i.direction === 'OUTBOUND' &&
                    new Date(i.start).getTime() < cE &&
                    new Date(i.end).getTime()   > cS
                );
            },

            // ─ Place card + duration dialog ────────────────────────────────

            placeCard(card, vehicleId, dropTime) {
                const DEF      = 3600000; // 1 h default
                const outEnd   = new Date(new Date(card.shift_start).getTime() - 10 * 60000);
                const outStart = new Date(outEnd.getTime() - DEF);
                const retStart = new Date(new Date(card.shift_end).getTime() + 10 * 60000);
                const retEnd   = new Date(retStart.getTime() + DEF);
                const ts       = Date.now();
                const outId    = `${card.id}_OUT_${ts}`;
                const retId    = `${card.id}_RET_${ts + 1}`;

                this.swimItems.push(
                    { id: outId, cardId: card.id, vehicleId, direction: 'OUTBOUND',
                      start: outStart, end: outEnd, headcount: card.headcount, conflict: false, tripId: null },
                    { id: retId, cardId: card.id, vehicleId, direction: 'RETURN',
                      start: retStart, end: retEnd, headcount: card.headcount, conflict: false, tripId: null }
                );

                this.assignedCards.add(card.id);
                this.checkConflicts();
                this.canSave = this.assignedCards.size > 0;
                this.showDurationDialog(card, outId, retId);
            },

            showDurationDialog(card, outId, retId) {
                const self = this;
                const d = new frappe.ui.Dialog({
                    title:  `Set Trip Duration — ${card.site_location}`,
                    fields: [
                        { fieldtype: 'Int', fieldname: 'out_min', label: 'Outbound Duration (minutes)', default: 60, reqd: 1 },
                        { fieldtype: 'Int', fieldname: 'ret_min', label: 'Return Duration (minutes)',   default: 60, reqd: 1 }
                    ],
                    primary_action_label: 'Confirm',
                    primary_action(vals) {
                        const outItem = self.swimItems.find(i => i.id === outId);
                        const retItem = self.swimItems.find(i => i.id === retId);
                        if (outItem) outItem.start = new Date(new Date(outItem.end).getTime() - vals.out_min * 60000);
                        if (retItem) retItem.end   = new Date(new Date(retItem.start).getTime() + vals.ret_min * 60000);
                        self.checkConflicts();
                        d.hide();
                    }
                });
                d.show();
            },

            // ─ Multi-stop trip ─────────────────────────────────────────────

            groupIntoTrip(newCard, existingItems, vehicleId) {
                const seen = new Set();
                const allCards = [];
                const push = c => { if (!seen.has(c.id)) { seen.add(c.id); allCards.push(c); } };
                existingItems
                    .map(i => this.planData.shipment_cards.find(c => c.id === i.cardId))
                    .filter(Boolean)
                    .forEach(push);
                push(newCard);

                const deadline = new Date(Math.min(...allCards.map(c => new Date(c.shift_start).getTime() - 10 * 60000)));

                const fields = [{
                    fieldtype: 'HTML', fieldname: 'intro',
                    options: `<div style="padding:8px 0;font-size:13px;color:#555;">
                        Enter drive time per leg. Works backwards from deadline:
                        <strong>${this.fmtISO(deadline.toISOString())}</strong>
                    </div>`
                }];

                allCards.forEach((card, i) => {
                    fields.push({ fieldtype: 'Section Break', label: `Leg ${i + 1} — ${card.site_location}` });
                    fields.push({ fieldtype: 'Int', fieldname: `drive_${i}`, label: `Drive time to ${card.site_location} (min)`, default: 30, reqd: 1 });
                    fields.push({ fieldtype: 'Int', fieldname: `board_${i}`, label: `Boarding / alighting (min)`,
                                  default: Math.ceil(Math.max(card.headcount * 5, 30) / 60), reqd: 1 });
                });

                fields.push({ fieldtype: 'Section Break', label: 'Trip Summary' });
                fields.push({
                    fieldtype: 'HTML', fieldname: 'trip_summary',
                    options: '<div id="rp-trip-summary" style="padding:10px;background:#f5f5f5;border-radius:6px;font-size:12px;color:#555;">Fill durations above to preview departure time</div>'
                });

                const self = this;
                const d = new frappe.ui.Dialog({
                    title:  `Plan Multi-Stop Trip — ${allCards.length} sites`,
                    fields,
                    primary_action_label: 'Confirm Trip',
                    primary_action(vals) {
                        self.buildTripOnTimeline(allCards, vehicleId, deadline, vals, existingItems);
                        d.hide();
                    }
                });

                setTimeout(() => {
                    allCards.forEach((_, i) => {
                        const df  = d.fields_dict[`drive_${i}`];
                        const bf  = d.fields_dict[`board_${i}`];
                        const upd = () => self.updateTripSummary(d, allCards, deadline);
                        if (df) df.$input.on('input', upd);
                        if (bf) bf.$input.on('input', upd);
                    });
                }, 300);

                d.show();
            },

            updateTripSummary(dialog, cards, deadline) {
                let total = 0;
                cards.forEach((_, i) => {
                    total += (parseInt(dialog.get_value(`drive_${i}`)) || 0);
                    total += (parseInt(dialog.get_value(`board_${i}`)) || 0);
                });
                const accBoard = cards.reduce((s, c) => s + Math.max(c.headcount * 5, 30), 0);
                total += Math.ceil(accBoard / 1000 / 60);

                const dep  = new Date(deadline.getTime() - total * 60000);
                const past = dep < new Date();
                const el   = document.getElementById('rp-trip-summary');
                if (el) el.innerHTML = `
                    <div style="display:flex;gap:24px;flex-wrap:wrap;">
                        <div>
                            <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#888">Total Duration</div>
                            <div style="font-size:16px;font-weight:600;color:#1a1a1a">${total} min</div>
                        </div>
                        <div>
                            <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#888">Depart Accommodation</div>
                            <div style="font-size:16px;font-weight:600;color:${past ? '#c62828' : '#1565c0'}">
                                ${this.fmtISO(dep.toISOString())} ${past ? '⚠' : ''}
                            </div>
                        </div>
                        <div>
                            <div style="font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#888">Must Arrive By</div>
                            <div style="font-size:16px;font-weight:600;color:#1a1a1a">${this.fmtISO(deadline.toISOString())}</div>
                        </div>
                    </div>`;
            },

            buildTripOnTimeline(cards, vehicleId, deadline, vals, oldItems) {
                // Remove existing items belonging to these cards
                const deadIds = new Set([
                    ...oldItems.map(i => i.id),
                    ...cards.flatMap(c => this.swimItems.filter(i => i.cardId === c.id).map(i => i.id))
                ]);
                this.swimItems = this.swimItems.filter(i => !deadIds.has(i.id));

                const accBoardMs = cards.reduce((s, c) => s + Math.max(c.headcount * 5, 30) * 1000, 0);
                let totalMs = accBoardMs;
                cards.forEach((_, i) => {
                    totalMs += (parseInt(vals[`drive_${i}`]) || 30) * 60000;
                    totalMs += (parseInt(vals[`board_${i}`]) || 5)  * 60000;
                });

                const tripStart = new Date(deadline.getTime() - totalMs);
                const tripId    = `TRIP_${vehicleId}_${Date.now()}`;
                let cursor      = new Date(tripStart.getTime() + accBoardMs);

                cards.forEach((card, i) => {
                    const driveMs  = (parseInt(vals[`drive_${i}`]) || 30) * 60000;
                    const boardMs  = (parseInt(vals[`board_${i}`]) || 5)  * 60000;
                    const segStart = new Date(cursor);
                    const segEnd   = new Date(cursor.getTime() + driveMs + boardMs);
                    const ts       = Date.now() + i;

                    this.swimItems.push(
                        { id: `${card.id}_OUT_TRIP_${ts}`, cardId: card.id, vehicleId,
                          direction: 'OUTBOUND', start: segStart, end: segEnd,
                          headcount: card.headcount, conflict: false, tripId },
                        { id: `${card.id}_RET_TRIP_${ts}`, cardId: card.id, vehicleId,
                          direction: 'RETURN',
                          start: new Date(new Date(card.shift_end).getTime() + 10 * 60000),
                          end:   new Date(new Date(card.shift_end).getTime() + 10 * 60000 + 3600000),
                          headcount: card.headcount, conflict: false, tripId: null }
                    );
                    this.assignedCards.add(card.id);
                    cursor = segEnd;
                });

                frappe.show_alert({
                    message: `Trip planned — vehicle departs at ${this.fmtISO(tripStart.toISOString())}`,
                    indicator: 'green'
                }, 6);

                this.checkConflicts();
                this.canSave = this.assignedCards.size > 0;
            },

            // ─ Conflict detection ───────────────────────────────────────────

            checkConflicts() {
                this.swimItems.forEach(i => { i.conflict = false; });
                this.planData.vehicles.forEach(v => {
                    const vi = this.swimItems.filter(i => i.vehicleId === v.id);
                    for (let a = 0; a < vi.length; a++) {
                        for (let b = a + 1; b < vi.length; b++) {
                            const ia = vi[a], ib = vi[b];
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

            // Drag a block horizontally to reposition it on the lane
            onBlockMouseDown(e, item) {
                e.stopPropagation();
                const startX    = e.clientX;
                const origStart = new Date(item.start).getTime();
                const origEnd   = new Date(item.end).getTime();
                let moved = false;

                const onMove = me => {
                    const dx = me.clientX - startX;
                    if (!moved && Math.abs(dx) > 3) moved = true;
                    if (!moved) return;
                    this.isDraggingBlock = true;
                    const deltaMs = (dx / this.svgWidth) * this.windowDurationMs;
                    item.start    = new Date(origStart + deltaMs);
                    item.end      = new Date(origEnd   + deltaMs);
                    this.checkConflicts();
                };

                const onUp = () => {
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup',   onUp);
                    setTimeout(() => { this.isDraggingBlock = false; }, 60);
                    if (moved) this.canSave = this.assignedCards.size > 0;
                };

                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup',   onUp);
            },

            closeDetail() { this.selectedItem = null; },

            removeSelectedFromLane() {
                if (!this.selectedItem) return;
                const cid = this.selectedItem.cardId;
                this.swimItems = this.swimItems.filter(i => i.cardId !== cid);
                this.assignedCards.delete(cid);
                this.selectedItem = null;
                this.checkConflicts();
                this.canSave = this.assignedCards.size > 0;
            },

            // ─ Block geometry (used in template) ───────────────────────────

            bx(item)   { return this.timeToX(item.start); },
            bw(item)   { return Math.max(8, this.timeToX(item.end) - this.timeToX(item.start)); },

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

                const btn  = document.getElementById('rp-save-btn');
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

                const safeJson  = JSON.stringify(routeData).replace(/<\//g, '<\\/');
                const injection = `<script>
    const ROUTE_DATA = ${safeJson};
    window.addEventListener('error', function(e) {
        document.body.style.cssText = 'background:#fff;color:#c00;padding:40px;font-family:monospace;font-size:13px';
        document.body.innerHTML = '<h2 style="margin-bottom:12px">Manifest Error</h2><pre>' + e.message + '\\nat line ' + e.lineno + '</pre>';
    });
<\/script>`;

                const finalHtml = tpl.replace('</head>', injection + '\n</head>');
                const blob      = new Blob([finalHtml], { type: 'text/html' });
                const url       = URL.createObjectURL(blob);
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

                    const uid    = si;
                    const outLbl = `${slug(card.accommodation)}_${uid}_${slug(card.site_location)}_OUTBOUND`;
                    const retLbl = `${slug(card.accommodation)}_${uid}_${slug(card.site_location)}_RETURN`;
                    const outIdx = si++, retIdx = si++;

                    shipments.push({ label: outLbl, pickups: [{}], deliveries: [{}] });
                    shipments.push({ label: retLbl, pickups: [{}], deliveries: [{}] });

                    shipEmp[outLbl]   = shipEmp[retLbl]   = card.employees;
                    shipSite[outLbl]  = shipSite[retLbl]  = card.site_location;
                    shipShift[outLbl] = shipShift[retLbl] = card.shift_name;
                    cMap[cid]         = { outLbl, retLbl, outIdx, retIdx };
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
                        const hc   = item.headcount || 0;
                        const iS   = new Date(item.start).toISOString();
                        const iE   = new Date(item.end).toISOString();
                        const dSec = Math.round((new Date(item.end) - new Date(item.start)) / 1000);

                        visits.push({ shipmentIndex: sIdx, isPickup: true,  startTime: iS,
                                      loadDemands: { seats: { amount: String(hc) } } });
                        trans.push({ travelDuration: `${dSec}s`, waitDuration: '0s',
                                     travelDistanceMeters: Math.round(dSec * 10) });
                        visits.push({ shipmentIndex: sIdx, isPickup: false, startTime: iE,
                                      loadDemands: { seats: { amount: String(-hc) } } });

                        const nxt = vItems[idx + 1];
                        const gap = nxt ? Math.max(0, new Date(nxt.start) - new Date(item.end)) : 0;
                        trans.push({ travelDuration: `${Math.round(gap / 1000)}s`, waitDuration: '0s',
                                     travelDistanceMeters: Math.round(gap / 1000 * 8) });
                    });

                    const rS    = new Date(vItems[0].start).toISOString();
                    const rE    = new Date(vItems[vItems.length - 1].end).toISOString();
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
                    request:  { model: {
                        shipments, vehicles: vehiclesList,
                        globalStartTime: this.planData.global_start,
                        globalEndTime:   this.planData.global_end
                    }},
                    response: { routes, skippedShipments: [], metrics: { totalCost: 0 } },
                    shipmentEmployees:     shipEmp,
                    shipmentSiteLocations: shipSite,
                    shipmentShiftNames:    shipShift,
                    vehicleMeta:           vMeta
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
    const s  = document.createElement('script');
    s.type   = 'text/x-template';
    s.id     = 'rp-vue-template';
    s.textContent = `
<div id="rp-shell">

  <!-- ══ Header ══ -->
  <div id="rp-header">
    <div id="rp-header-left">
      <div id="rp-title">Route Planner</div>
      <div id="rp-date">{{ fmtDate(planData.date) }}</div>
    </div>
    <div id="rp-header-right">
      <button id="rp-save-btn" class="rp-btn rp-btn-primary" :disabled="!canSave" @click="openManifest">
        Save Plan
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
               :class="['rp-lane-row', vi % 2 === 1 ? 'rp-lane-alt' : '']">

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

                <!-- ── Swim items ── -->
                <g v-for="item in itemsByVehicle[vehicle.id]" :key="item.id"
                   :class="isDraggingBlock && bsel(item) ? 'rp-block-grabbing' : 'rp-block-grab'"
                   @mousedown="onBlockMouseDown($event, item)"
                   @click.stop="onBlockClick(item, $event)">

                  <!-- Drop shadow -->
                  <rect :x="bx(item) + 1" y="10"
                        :width="bw(item)" :height="rowHeight - 20"
                        fill="rgba(0,0,0,0.10)" rx="6"/>

                  <!-- Block body -->
                  <rect :x="bx(item)" y="8"
                        :width="bw(item)" :height="rowHeight - 16"
                        :fill="bfill(item)"
                        :stroke="bsel(item) ? '#f97316' : 'transparent'"
                        stroke-width="2.5" rx="6"/>

                  <!-- Direction arrow -->
                  <text v-if="bw(item) >= 18"
                        :x="bx(item) + 8" :y="rowHeight * 0.5 + 1"
                        fill="rgba(255,255,255,0.95)" font-size="12" dominant-baseline="middle"
                        style="user-select:none;pointer-events:none">
                    {{ item.direction === 'OUTBOUND' ? '\u2192' : '\u2190' }}
                  </text>

                  <!-- Site name -->
                  <text v-if="bw(item) >= 54"
                        :x="bx(item) + 25" :y="rowHeight * 0.5 - 5"
                        fill="white" font-size="11" font-weight="600" dominant-baseline="middle"
                        style="user-select:none;pointer-events:none">
                    {{ bcard(item).site_location }}
                  </text>

                  <!-- Headcount -->
                  <text v-if="bw(item) >= 54"
                        :x="bx(item) + 25" :y="rowHeight * 0.5 + 10"
                        fill="rgba(255,255,255,0.72)" font-size="9" dominant-baseline="middle"
                        style="user-select:none;pointer-events:none">
                    &#x1F465;{{ item.headcount }}
                  </text>

                  <!-- Resize handle (visual only) -->
                  <rect v-if="bw(item) >= 24"
                        :x="bx(item) + bw(item) - 6" y="18"
                        width="4" :height="rowHeight - 36"
                        fill="rgba(255,255,255,0.22)" rx="2"
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
          <div class="rp-detail-section">
            <span :class="['rp-dir-badge', selectedItem.direction === 'OUTBOUND' ? 'rp-dir-out' : 'rp-dir-ret']">
              {{ selectedItem.direction === 'OUTBOUND' ? '\u2192 Outbound' : '\u2190 Return' }}
            </span>
            <span v-if="selectedItem.tripId" class="rp-dir-badge rp-dir-trip" style="margin-left:6px">
              MULTI-STOP TRIP
            </span>
          </div>

          <div class="rp-detail-section">
            <div class="rp-detail-label">Site</div>
            <div class="rp-detail-value">{{ selectedCard.site_location }}</div>
          </div>
          <div class="rp-detail-section">
            <div class="rp-detail-label">Shift</div>
            <div class="rp-detail-value">{{ selectedCard.shift_name }}</div>
          </div>
          <div class="rp-detail-section">
            <div class="rp-detail-label">Stop Location</div>
            <div class="rp-detail-value">{{ selectedCard.stop_location }}</div>
          </div>
          <div class="rp-detail-section">
            <div class="rp-detail-label">Accommodation</div>
            <div class="rp-detail-value">{{ selectedCard.accommodation }}</div>
          </div>

          <div class="rp-detail-section">
            <div class="rp-detail-label">Time on Lane</div>
            <div class="rp-detail-value">
              {{ fmtISO(new Date(selectedItem.start).toISOString()) }}
              &#x2192;
              {{ fmtISO(new Date(selectedItem.end).toISOString()) }}
              <span style="color:#aaa;font-size:12px">({{ durMin(selectedItem) }} min)</span>
            </div>
          </div>

          <div class="rp-detail-section">
            <div class="rp-detail-label">Shift Times</div>
            <div style="display:flex;gap:8px;margin-top:4px">
              <div style="flex:1;background:#e8f5e9;border-radius:6px;padding:6px 10px">
                <div style="font-size:9px;font-weight:700;letter-spacing:.08em;color:#888">SHIFT START TIME</div>
                <div style="font-size:12px;font-weight:500">
                  {{ fmtISO(selectedCard.shift_start) }}
                </div>
              </div>
              <div style="flex:1;background:#fff3e0;border-radius:6px;padding:6px 10px">
                <div style="font-size:9px;font-weight:700;letter-spacing:.08em;color:#888">SHIFT END TIME</div>
                <div style="font-size:12px;font-weight:500">
                  {{ fmtISO(selectedCard.shift_end) }}
                </div>
              </div>
            </div>
          </div>

          <div class="rp-detail-section">
            <div class="rp-detail-label">Employees ({{ selectedCard.headcount }})</div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">
              <span v-for="e in selectedCard.employees" :key="e" class="rp-emp-chip">{{ e }}</span>
            </div>
          </div>
        </div>

        <div id="rp-detail-footer">
          <button class="rp-btn rp-btn-danger" @click="removeSelectedFromLane">Remove from Lane</button>
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
            width: 0; min-width: 0; background: #fff;
            border-left: 1px solid #e2e2e2;
            display: flex; flex-direction: column;
            transition: width .22s ease, min-width .22s ease;
            overflow: hidden; flex-shrink: 0;
        }
        #rp-detail-panel.rp-detail-open { width: 300px; min-width: 300px; }

        #rp-detail-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 14px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
        }
        #rp-detail-title {
            font-size: 10px; font-weight: 800; text-transform: uppercase;
            letter-spacing: .10em; color: #aaa;
        }
        #rp-detail-close {
            background: none; border: none; cursor: pointer;
            font-size: 16px; color: #ccc; padding: 2px 6px; border-radius: 4px;
            transition: background .14s, color .14s;
        }
        #rp-detail-close:hover { background: #f5f5f5; color: #555; }
        #rp-detail-body   { flex: 1; overflow-y: auto; padding: 14px; }
        #rp-detail-footer { padding: 14px; border-top: 1px solid #f0f0f0; flex-shrink: 0; }

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