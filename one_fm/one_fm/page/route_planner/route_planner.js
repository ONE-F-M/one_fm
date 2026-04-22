frappe.pages['route-planner'].on_page_load = function (wrapper) {
    if (!document.querySelector('#vis-css')) {
        const visCSS = document.createElement('link');
        visCSS.id = 'vis-css';
        visCSS.rel = 'stylesheet';
        visCSS.href = 'https://unpkg.com/vis-timeline/styles/vis-timeline-graph2d.min.css';
        document.head.appendChild(visCSS);
    }

    if (!document.querySelector('#vis-js')) {
        const visJS = document.createElement('script');
        visJS.id = 'vis-js';
        visJS.src = 'https://unpkg.com/vis-timeline/standalone/umd/vis-timeline-graph2d.min.js';
        visJS.onload = () => init(wrapper);
        document.head.appendChild(visJS);
    } else {
        init(wrapper);
    }
}

// ── Global state ──
let timelineInstance = null;
let axisTimeline = null;
let timelineItems = null;
let timelineGroups = null;
let assignedCards = {};
let planData = null;
let draggingCard = null;

function init(wrapper) {
    injectLoadingStyles();
    // ── Show loading indicator ──
    $(wrapper).html(`
        <div id="rp-loading">
            <div id="rp-loading-spinner"></div>
            <div id="rp-loading-text">Loading Route Planner...</div>
            <div id="rp-loading-sub">Fetching vehicles, shifts and employee data</div>
        </div>
    `);
    frappe.call({
        method: "one_fm.one_fm.page.route_planner.route_planner.get_route_planner_data",
        callback: function (r) {
            if (!r.message || r.message.status === "error") {
                frappe.msgprint(r.message ? r.message.message : "Failed to load data");
                return;
            }
            const data = r.message;
            renderPage(wrapper, data);
            initTimeline(data);
            bindDragEvents();
        }
    });
}

function injectLoadingStyles() {
    if (document.getElementById('rp-loading-styles')) return;
    const style = document.createElement('style');
    style.id = 'rp-loading-styles';
    style.textContent = `
        #rp-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            background: #f5f5f5;
            font-family: 'Google Sans', Roboto, sans-serif;
            gap: 16px;
        }
        #rp-loading-spinner {
            width: 40px;
            height: 40px;
            border: 3px solid #e0e0e0;
            border-top-color: #5e5c5bff;
            border-radius: 50%;
            animation: rp-spin 0.8s linear infinite;
        }
        @keyframes rp-spin {
            to { transform: rotate(360deg); }
        }
        #rp-loading-text {
            font-size: 16px;
            font-weight: 500;
            color: #1a1a1a;
        }
        #rp-loading-sub {
            font-size: 13px;
            color: #888;
        }
    `;
    document.head.appendChild(style);
}

function renderPage(wrapper, data) {
    $(wrapper).html(`
        <div id="rp-shell">
            <div id="rp-header">
                <div id="rp-header-left">
                    <div id="rp-title">Route Planner</div>
                    <div id="rp-date">${frappe.datetime.str_to_user(data.date)}</div>
                </div>
                <div id="rp-header-right">
                    <button id="rp-save-btn" class="rp-btn rp-btn-primary" disabled>Save Plan</button>
                </div>
            </div>
            <div id="rp-body">
                <div id="rp-pool-panel">
                    <div id="rp-pool-header">
                        <div id="rp-pool-title">Unassigned Shipments</div>
                        <div id="rp-pool-count">${data.shipment_cards.length} cards</div>
                    </div>
                    <div id="rp-pool-search">
                        <input type="text" id="rp-search-input" placeholder="Search shift, site, accommodation...">
                    </div>
                    <div id="rp-pool-groups"></div>
                </div>
                <div id="rp-timeline-panel">
                    <div id="rp-timeline-toolbar">
                        <div id="rp-timeline-zoom">
                            <button class="rp-btn-icon" id="rp-zoom-in">+</button>
                            <button class="rp-btn-icon" id="rp-zoom-out">−</button>
                            <button class="rp-btn-icon" id="rp-zoom-fit">⊡ Fit</button>
                        </div>
                        <div id="rp-timeline-legend">
                            <span class="rp-legend-item rp-legend-out">Outbound</span>
                            <span class="rp-legend-item rp-legend-ret">Return</span>
                            <span class="rp-legend-item rp-legend-conflict">Conflict</span>
                        </div>
                    </div>
                    <div id="rp-timeline-axis-container"></div>
                    <div id="rp-timeline-container"></div>
                </div>
                <div id="rp-detail-panel" class="rp-detail-hidden">
                    <div id="rp-detail-header">
                        <div id="rp-detail-title">Shipment Details</div>
                        <button id="rp-detail-close">✕</button>
                    </div>
                    <div id="rp-detail-body"></div>
                    <div id="rp-detail-footer">
                        <button id="rp-detail-remove" class="rp-btn rp-btn-danger">Remove from Lane</button>
                    </div>
                </div>
            </div>
        </div>
    `);

    injectStyles();
    renderCardPool(data.shipment_cards);
    bindSearch(data.shipment_cards);

    // ── Save Plan → open manifest ──
    document.getElementById('rp-save-btn').addEventListener('click', openManifest);

    // ── Detail panel close ──
    document.getElementById('rp-detail-close').addEventListener('click', closeDetailPanel);
    document.getElementById('rp-detail-remove').addEventListener('click', function () {
        const itemId = this.dataset.itemId;
        if (!itemId) return;
        const item = timelineItems.get(itemId);
        if (!item) return;
        hideTooltips();
        returnCardToPool(item.cardId);
        // Remove all items belonging to this card
        const assignment = assignedCards[item.cardId];
        if (assignment) assignment.itemIds.forEach(id => timelineItems.remove(id));
        closeDetailPanel();
        checkConflicts();
        updateSaveButton();
    });
}

function closeDetailPanel() {
    const panel = document.getElementById('rp-detail-panel');
    if (panel) panel.classList.add('rp-detail-hidden');
}

function openDetailPanel(item) {
    const card = planData.shipment_cards.find(c => c.id === item.cardId);
    if (!card) return;

    const panel = document.getElementById('rp-detail-panel');
    const body = document.getElementById('rp-detail-body');
    const removeBtn = document.getElementById('rp-detail-remove');

    removeBtn.dataset.itemId = item.id;

    const dir = item.direction === "OUTBOUND" ? "→ Outbound" : "← Return";
    const dirColor = item.direction === "OUTBOUND" ? "#1565c0" : "#e65100";
    const dirBg = item.direction === "OUTBOUND" ? "#e3f2fd" : "#fff3e0";
    const timeStart = fmtTimeLocal(new Date(item.start).toISOString());
    const timeEnd = fmtTimeLocal(new Date(item.end).toISOString());
    const duration = Math.round((new Date(item.end) - new Date(item.start)) / 60000);

    const empChips = card.employees.map(e =>
        `<span class="rp-emp-chip">${e}</span>`
    ).join('');

    body.innerHTML = `
        <div class="rp-detail-section">
            <span style="background:${dirBg};color:${dirColor};padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700">${dir}</span>
            ${item.tripId ? `<span style="background:#f3e8fd;color:#7c3aed;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;margin-left:6px">MULTI-STOP TRIP</span>` : ''}
        </div>

        <div class="rp-detail-section">
            <div class="rp-detail-label">Site</div>
            <div class="rp-detail-value">${card.site_location}</div>
        </div>

        <div class="rp-detail-section">
            <div class="rp-detail-label">Shift</div>
            <div class="rp-detail-value">${card.shift_name}</div>
        </div>

        <div class="rp-detail-section">
            <div class="rp-detail-label">Stop Location</div>
            <div class="rp-detail-value">${card.stop_location}</div>
        </div>

        <div class="rp-detail-section">
            <div class="rp-detail-label">Accommodation</div>
            <div class="rp-detail-value">${card.accommodation}</div>
        </div>

        <div class="rp-detail-section">
            <div class="rp-detail-label">Time on Lane</div>
            <div class="rp-detail-value">${timeStart} → ${timeEnd} <span style="color:#888;font-size:12px">(${duration} min)</span></div>
        </div>

        <div class="rp-detail-section">
            <div class="rp-detail-label">Time Window</div>
            <div class="rp-detail-value">
                <div style="display:flex;gap:8px;margin-top:4px">
                    <div style="flex:1;background:#e8f5e9;border-radius:6px;padding:6px 10px">
                        <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;color:#888">OUT</div>
                        <div style="font-size:12px;font-weight:500">${fmtTimeLocal(card.outbound_window_start)} – ${fmtTimeLocal(card.outbound_window_end)}</div>
                    </div>
                    <div style="flex:1;background:#fff3e0;border-radius:6px;padding:6px 10px">
                        <div style="font-size:9px;font-weight:700;letter-spacing:0.08em;color:#888">RET</div>
                        <div style="font-size:12px;font-weight:500">${fmtTimeLocal(card.return_window_start)} – ${fmtTimeLocal(card.return_window_end)}</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="rp-detail-section">
            <div class="rp-detail-label">Employees (${card.headcount})</div>
            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">${empChips}</div>
        </div>
    `;

    panel.classList.remove('rp-detail-hidden');
}

// ── Card Pool ──────────────────────────────────────────────────────

function renderCardPool(cards) {
    const groups = {};
    cards.forEach(card => {
        if (!groups[card.accommodation]) groups[card.accommodation] = [];
        groups[card.accommodation].push(card);
    });

    const container = document.getElementById('rp-pool-groups');
    container.innerHTML = '';

    Object.entries(groups).forEach(([acc, accCards]) => {
        const group = document.createElement('div');
        group.className = 'rp-pool-group';
        group.innerHTML = `
            <div class="rp-group-header" data-acc="${acc}">
                <span class="rp-group-label">${acc}</span>
                <span class="rp-group-count">${accCards.length}</span>
                <span class="rp-group-chevron">▾</span>
            </div>
            <div class="rp-group-cards" id="group-${acc.replace(/\s+/g, '-')}">
                ${accCards.map(card => renderCard(card)).join('')}
            </div>
        `;
        container.appendChild(group);

        group.querySelector('.rp-group-header').addEventListener('click', function () {
            const cardsEl = group.querySelector('.rp-group-cards');
            const chevron = group.querySelector('.rp-group-chevron');
            const collapsed = cardsEl.style.display === 'none';
            cardsEl.style.display = collapsed ? 'flex' : 'none';
            chevron.textContent = collapsed ? '▾' : '▸';
        });
    });
}

function renderCard(card) {
    const outStart = fmtTimeLocal(card.outbound_window_start);
    const outEnd = fmtTimeLocal(card.outbound_window_end);
    const retStart = fmtTimeLocal(card.return_window_start);
    const retEnd = fmtTimeLocal(card.return_window_end);

    return `
        <div class="rp-card"
             data-id="${card.id}"
             data-headcount="${card.headcount}"
             draggable="true">
            <div class="rp-card-header">
                <span class="rp-card-site">${card.site_location}</span>
                <span class="rp-card-type ${card.type === 'OLM' ? 'rp-tag-olm' : 'rp-tag-osm'}">${card.type}</span>
            </div>
            <div class="rp-card-shift">${card.shift_name}</div>
            <div class="rp-card-meta">
                <span class="rp-card-meta-item"><span class="rp-meta-icon">👥</span>${card.headcount} employees</span>
                <span class="rp-card-meta-item"><span class="rp-meta-icon">📍</span>${card.stop_location}</span>
            </div>
            <div class="rp-card-windows">
                <div class="rp-window rp-window-out">
                    <span class="rp-window-label">OUT</span>
                    <span class="rp-window-time">${outStart} – ${outEnd}</span>
                </div>
                <div class="rp-window rp-window-ret">
                    <span class="rp-window-label">RET</span>
                    <span class="rp-window-time">${retStart} – ${retEnd}</span>
                </div>
            </div>
            <div class="rp-card-employees">
                ${card.employees.slice(0, 3).map(e => `<span class="rp-emp-chip">${e}</span>`).join('')}
                ${card.employees.length > 3
            ? `<span class="rp-emp-chip rp-emp-more">+${card.employees.length - 3} more</span>`
            : ''}
            </div>
        </div>
    `;
}

function bindSearch(allCards) {
    document.getElementById('rp-search-input').addEventListener('input', function () {
        const q = this.value.toLowerCase();
        const filtered = allCards.filter(c =>
            c.shift_name.toLowerCase().includes(q) ||
            c.site_location.toLowerCase().includes(q) ||
            c.accommodation.toLowerCase().includes(q) ||
            c.stop_location.toLowerCase().includes(q)
        );
        document.getElementById('rp-pool-count').textContent = `${filtered.length} cards`;
        renderCardPool(filtered);
    });
}

// ── Timeline ───────────────────────────────────────────────────────

function hideTooltips() {
    document.querySelectorAll('.vis-tooltip').forEach(t => {
        t.style.display = 'none';
        t.style.visibility = 'hidden';
    });
    const custom = document.getElementById('rp-custom-tooltip');
    if (custom) custom.style.display = 'none';
}

function initTimeline(data) {
    planData = data;
    timelineItems = new vis.DataSet([]);
    timelineGroups = new vis.DataSet([]);

    data.vehicles.forEach(v => {
        timelineGroups.add({ id: v.id, content: buildGroupLabel(v) });
    });

    const start = new Date(data.global_start);
    const end = new Date(data.global_end);
    const rowHeight = 70;
    const timelineHeight = data.vehicles.length * rowHeight;

    const sharedOptions = {
        start: start,
        end: end,
        min: start,
        max: end,
        zoomMin: 1000 * 60 * 30,
        zoomMax: 1000 * 60 * 60 * 24,
        margin: { item: { horizontal: 4, vertical: 4 } }
    };

    // ── Sticky axis ──
    const axisContainer = document.getElementById('rp-timeline-axis-container');
    axisTimeline = new vis.Timeline(
        axisContainer, new vis.DataSet([]), new vis.DataSet([]),
        {
            ...sharedOptions,
            height: 50, showCurrentTime: false,
            selectable: false, moveable: true, zoomable: true,
            orientation: { axis: "top" }
        }
    );

    // ── Main timeline ──
    const container = document.getElementById('rp-timeline-container');
    timelineInstance = new vis.Timeline(container, timelineItems, timelineGroups, {
        ...sharedOptions,
        height: timelineHeight,
        selectable: true,
        editable: { updateTime: true, remove: true },
        groupEditable: false,
        stack: false,
        showCurrentTime: false,
        tooltip: { followMouse: false, delay: 99999 },
        orientation: { axis: "none", item: "top" },
        onMove: function (item, callback) {
            hideTooltips();
            callback(item);
            checkConflicts();
            updateSaveButton();
        },
        onRemove: function (item, callback) {
            hideTooltips();
            // Remove all paired items for this card
            const assignment = assignedCards[item.cardId];
            if (assignment) {
                assignment.itemIds
                    .filter(id => id !== item.id)
                    .forEach(id => timelineItems.remove(id));
            }
            returnCardToPool(item.cardId);
            callback(item);
            checkConflicts();
            updateSaveButton();
            closeDetailPanel();
        }
    });

    // ── Click to open detail panel ──
    timelineInstance.on('click', function (props) {
        if (!props.item) {
            closeDetailPanel();
            return;
        }
        const item = timelineItems.get(props.item);
        if (item && item.cardId) openDetailPanel(item);
    });

    // ── Sync zoom/pan ──
    let syncing = false;
    timelineInstance.on('rangechange', function (props) {
        if (syncing) return;
        syncing = true;
        axisTimeline.setWindow(props.start, props.end, { animation: false });
        syncing = false;
    });
    axisTimeline.on('rangechange', function (props) {
        if (syncing) return;
        syncing = true;
        timelineInstance.setWindow(props.start, props.end, { animation: false });
        syncing = false;
    });

    // ── Custom tooltip ──
    const visTooltipDiv = document.createElement('div');
    visTooltipDiv.id = 'rp-custom-tooltip';
    visTooltipDiv.style.cssText = `
        position: fixed; z-index: 9999; display: none;
        background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12); padding: 8px 12px;
        font-size: 12px; line-height: 1.5; max-width: 260px; pointer-events: none;
    `;
    document.body.appendChild(visTooltipDiv);

    timelineInstance.on('itemover', function (props) {
        const item = timelineItems.get(props.item);
        if (!item || !item.cardId) return;
        const card = planData.shipment_cards.find(c => c.id === item.cardId);
        if (!card) return;
        const dir = item.direction === "OUTBOUND" ? "→ Outbound" : "← Return";
        visTooltipDiv.innerHTML = `
            <div style="font-weight:600;font-size:13px">${card.site_location}</div>
            <div style="color:#888;font-size:11px;margin-bottom:4px">${card.shift_name}</div>
            <div style="font-size:11px">${dir} · 👥 ${card.headcount} employees</div>
            <div style="font-size:10px;color:#aaa;margin-top:4px">Click to view full details</div>
        `;
        visTooltipDiv.style.display = 'block';
    });

    timelineInstance.on('itemout', function () {
        visTooltipDiv.style.display = 'none';
    });

    container.addEventListener('mousemove', function (e) {
        if (visTooltipDiv.style.display === 'block') {
            visTooltipDiv.style.left = (e.clientX + 16) + 'px';
            visTooltipDiv.style.top = (e.clientY + 16) + 'px';
            const rect = visTooltipDiv.getBoundingClientRect();
            if (rect.right > window.innerWidth) visTooltipDiv.style.left = (e.clientX - rect.width - 8) + 'px';
            if (rect.bottom > window.innerHeight) visTooltipDiv.style.top = (e.clientY - rect.height - 8) + 'px';
        }
    });

    container.addEventListener('mouseleave', function () {
        visTooltipDiv.style.display = 'none';
        hideTooltips();
    });

    timelineInstance.on('changed', () => setTimeout(hideTooltips, 50));

    // ── Zoom controls ──
    document.getElementById('rp-zoom-in').addEventListener('click', () => {
        timelineInstance.zoomIn(0.5);
        axisTimeline.zoomIn(0.5);
    });
    document.getElementById('rp-zoom-out').addEventListener('click', () => {
        timelineInstance.zoomOut(0.5);
        axisTimeline.zoomOut(0.5);
    });
    document.getElementById('rp-zoom-fit').addEventListener('click', () => {
        timelineInstance.fit();
        const w = timelineInstance.getWindow();
        axisTimeline.setWindow(w.start, w.end, { animation: false });
    });

    // ── Drop targets ──
    function addDropListeners(el) {
        el.addEventListener('dragover', function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        });
        el.addEventListener('drop', function (e) {
            e.preventDefault();
            e.stopPropagation();
            handleTimelineDrop(e);
        });
    }

    addDropListeners(container);
    setTimeout(() => {
        container.querySelectorAll(
            '.vis-content, .vis-itemset, .vis-background, .vis-group, .vis-foreground'
        ).forEach(el => addDropListeners(el));
    }, 500);
}

function buildGroupLabel(v) {
    return `
        <div class="rp-group-vehicle">
            <div class="rp-gv-label">${v.label}</div>
            <div class="rp-gv-meta">${v.driver} · ${v.seats} seats</div>
            <div class="rp-gv-acc">${v.accommodation}</div>
        </div>
    `;
}

// ── Drag events ────────────────────────────────────────────────────

function bindDragEvents() {
    document.addEventListener('dragstart', function (e) {
        const card = e.target.closest('.rp-card');
        if (!card) return;
        draggingCard = planData.shipment_cards.find(c => c.id === card.dataset.id);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', card.dataset.id);
        card.style.opacity = '0.5';
        const tc = document.getElementById('rp-timeline-container');
        if (tc) tc.classList.add('rp-drop-active');
    });

    document.addEventListener('dragend', function (e) {
        const card = e.target.closest('.rp-card');
        if (card) card.style.opacity = '1';
        const tc = document.getElementById('rp-timeline-container');
        if (tc) tc.classList.remove('rp-drop-active');
        setTimeout(() => { draggingCard = null; }, 100);
    });
}

function handleTimelineDrop(e) {
    e.preventDefault();
    e.stopPropagation();

    const tc = document.getElementById('rp-timeline-container');
    if (tc) tc.classList.remove('rp-drop-active');

    if (!draggingCard) return;

    const card = draggingCard;
    draggingCard = null;

    let props, time, group;
    try {
        props = timelineInstance.getEventProperties(e);
        time = props.time;
        group = props.group;
    } catch (err) { }

    if (!group) { showVehiclePickerDialog(card); return; }

    const vehicle = planData.vehicles.find(v => v.id === group);
    if (!vehicle) { showVehiclePickerDialog(card); return; }

    const existing = timelineItems.get({ filter: i => i.group === group });
    const usedSeats = existing.reduce((sum, i) => sum + (i.headcount || 0), 0);

    if (usedSeats + card.headcount > vehicle.seats) {
        frappe.show_alert({
            message: `Not enough seats — ${vehicle.seats - usedSeats} remaining on ${vehicle.label}`,
            indicator: "red"
        });
        return;
    }

    const overlapping = findOverlappingOutbound(card, group);
    if (overlapping.length > 0) {
        frappe.confirm(
            `${overlapping.length} existing shipment(s) on ${vehicle.label} share this time window. Group into a multi-stop trip?`,
            () => groupIntoTrip(card, overlapping, group),
            () => placeCardOnTimeline(card, group, time || new Date(card.outbound_window_start))
        );
        return;
    }

    placeCardOnTimeline(card, group, time || new Date(card.outbound_window_start));
}

function findOverlappingOutbound(card, vehicleId) {
    const cardStart = new Date(card.outbound_window_start).getTime();
    const cardEnd = new Date(card.outbound_window_end).getTime();
    return timelineItems.get({
        filter: i =>
            i.group === vehicleId &&
            i.direction === "OUTBOUND" &&
            new Date(i.start).getTime() < cardEnd &&
            new Date(i.end).getTime() > cardStart
    });
}

function showVehiclePickerDialog(card) {
    const vehicleOptions = planData.vehicles.map(v => v.id);
    const d = new frappe.ui.Dialog({
        title: `Assign "${card.site_location}" to a Vehicle`,
        fields: [{
            fieldtype: "Select", fieldname: "vehicle_id",
            label: "Vehicle", options: vehicleOptions.join("\n"), reqd: 1
        }],
        primary_action_label: "Assign",
        primary_action: function (values) {
            const vehicle = planData.vehicles.find(v => v.id === values.vehicle_id);
            const existing = timelineItems.get({ filter: i => i.group === values.vehicle_id });
            const usedSeats = existing.reduce((sum, i) => sum + (i.headcount || 0), 0);
            if (usedSeats + card.headcount > vehicle.seats) {
                frappe.show_alert({ message: `Not enough seats on ${vehicle.label}`, indicator: "red" });
                return;
            }
            const overlapping = findOverlappingOutbound(card, values.vehicle_id);
            if (overlapping.length > 0) {
                d.hide();
                frappe.confirm(
                    `${overlapping.length} existing shipment(s) share this time window. Group into a multi-stop trip?`,
                    () => groupIntoTrip(card, overlapping, values.vehicle_id),
                    () => placeCardOnTimeline(card, values.vehicle_id, new Date(card.outbound_window_start))
                );
                return;
            }
            placeCardOnTimeline(card, values.vehicle_id, new Date(card.outbound_window_start));
            d.hide();
        }
    });
    d.show();
}

function placeCardOnTimeline(card, vehicleId, dropTime) {
    const DEFAULT_DURATION_MS = 60 * 60 * 1000;
    const outEnd = new Date(card.outbound_window_end);
    const outStart = new Date(outEnd.getTime() - DEFAULT_DURATION_MS);
    const retStart = new Date(card.return_window_start);
    const retEnd = new Date(retStart.getTime() + DEFAULT_DURATION_MS);
    const outItemId = `${card.id}_OUT_${Date.now()}`;
    const retItemId = `${card.id}_RET_${Date.now() + 1}`;

    timelineItems.add([
        {
            id: outItemId, group: vehicleId, start: outStart, end: outEnd,
            content: buildItemContent(card, "OUTBOUND"), className: "rp-item-out",
            cardId: card.id, headcount: card.headcount, direction: "OUTBOUND", title: ""
        },
        {
            id: retItemId, group: vehicleId, start: retStart, end: retEnd,
            content: buildItemContent(card, "RETURN"), className: "rp-item-ret",
            cardId: card.id, headcount: card.headcount, direction: "RETURN", title: ""
        }
    ]);

    assignedCards[card.id] = { vehicleId, itemIds: [outItemId, retItemId] };
    removeCardFromPool(card.id);
    showDurationDialog(card, outItemId, retItemId);
    checkConflicts();
    updateSaveButton();
}

function showDurationDialog(card, outItemId, retItemId) {
    const d = new frappe.ui.Dialog({
        title: `Set Trip Duration — ${card.site_location}`,
        fields: [
            { fieldtype: "Int", fieldname: "outbound_duration", label: "Outbound Trip Duration (minutes)", default: 60, reqd: 1 },
            { fieldtype: "Int", fieldname: "return_duration", label: "Return Trip Duration (minutes)", default: 60, reqd: 1 }
        ],
        primary_action_label: "Confirm",
        primary_action: function (values) {
            const outMs = values.outbound_duration * 60 * 1000;
            const retMs = values.return_duration * 60 * 1000;
            const outItem = timelineItems.get(outItemId);
            const retItem = timelineItems.get(retItemId);
            const outDeadline = new Date(outItem.end);
            const retDepart = new Date(retItem.start);
            timelineItems.update([
                { id: outItemId, start: new Date(outDeadline.getTime() - outMs), end: outDeadline },
                { id: retItemId, start: retDepart, end: new Date(retDepart.getTime() + retMs) }
            ]);
            checkConflicts();
            d.hide();
        }
    });
    d.show();
}

function groupIntoTrip(newCard, existingItems, vehicleId) {
    const existingCards = existingItems
        .map(i => planData.shipment_cards.find(c => c.id === i.cardId))
        .filter(Boolean);
    const seen = new Set();
    const allCards = [];
    [...existingCards, newCard].forEach(c => {
        if (!seen.has(c.id)) { seen.add(c.id); allCards.push(c); }
    });

    const deadline = new Date(Math.min(...allCards.map(c => new Date(c.outbound_window_end).getTime())));

    const fields = [
        {
            fieldtype: "HTML", fieldname: "trip_intro",
            options: `<div style="padding:8px 0;font-size:13px;color:#555;">
                Enter drive time for each leg. Works backwards from
                <strong>${fmtTimeLocal(deadline.toISOString())}</strong> deadline.
            </div>`
        }
    ];

    allCards.forEach((card, idx) => {
        fields.push({ fieldtype: "Section Break", label: `Leg ${idx + 1} — ${card.site_location}` });
        fields.push({ fieldtype: "Int", fieldname: `drive_${idx}`, label: `Drive time to ${card.site_location} (minutes)`, default: 30, reqd: 1 });
        fields.push({ fieldtype: "Int", fieldname: `board_${idx}`, label: `Boarding/alighting time (minutes)`, default: Math.ceil(Math.max(card.headcount * 5, 30) / 60), reqd: 1 });
    });

    fields.push({ fieldtype: "Section Break", label: "Trip Summary" });
    fields.push({
        fieldtype: "HTML", fieldname: "trip_summary",
        options: `<div id="rp-trip-summary" style="padding:10px;background:#f5f5f5;border-radius:6px;font-size:12px;color:#555;">
            Fill in durations above to see departure time
        </div>`
    });

    const d = new frappe.ui.Dialog({
        title: `Plan Multi-Stop Trip — ${allCards.length} sites`,
        fields: fields,
        primary_action_label: "Confirm Trip",
        primary_action: function (values) {
            buildTripOnTimeline(allCards, vehicleId, deadline, values, existingItems);
            d.hide();
        }
    });

    setTimeout(() => {
        allCards.forEach((card, idx) => {
            const df = d.fields_dict[`drive_${idx}`];
            const bf = d.fields_dict[`board_${idx}`];
            if (df) df.$input.on('input', () => updateTripSummary(d, allCards, deadline));
            if (bf) bf.$input.on('input', () => updateTripSummary(d, allCards, deadline));
        });
    }, 300);

    d.show();
}

function updateTripSummary(dialog, cards, deadline) {
    let totalMinutes = 0;
    cards.forEach((card, idx) => {
        totalMinutes += (parseInt(dialog.get_value(`drive_${idx}`)) || 0);
        totalMinutes += (parseInt(dialog.get_value(`board_${idx}`)) || 0);
    });
    const accBoardMs = cards.reduce((sum, c) => sum + Math.max(c.headcount * 5, 30), 0);
    totalMinutes += Math.ceil(accBoardMs / 1000 / 60);

    const departure = new Date(deadline.getTime() - totalMinutes * 60 * 1000);
    const isPast = departure < new Date();
    const summary = document.getElementById('rp-trip-summary');
    if (summary) {
        summary.innerHTML = `
            <div style="display:flex;gap:24px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.06em;color:#888">Total Trip Duration</div>
                    <div style="font-size:16px;font-weight:600;color:#1a1a1a">${totalMinutes} min</div>
                </div>
                <div>
                    <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.06em;color:#888">Depart Accommodation</div>
                    <div style="font-size:16px;font-weight:600;color:${isPast ? '#c62828' : '#1565c0'}">
                        ${fmtTimeLocal(departure.toISOString())} ${isPast ? '⚠' : ''}
                    </div>
                </div>
                <div>
                    <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.06em;color:#888">Must Arrive By</div>
                    <div style="font-size:16px;font-weight:600;color:#1a1a1a">${fmtTimeLocal(deadline.toISOString())}</div>
                </div>
            </div>
        `;
    }
}

function buildTripOnTimeline(cards, vehicleId, deadline, values, oldItems) {
    const allOldItemIds = new Set(oldItems.map(i => i.id));
    cards.forEach(card => {
        const a = assignedCards[card.id];
        if (a) a.itemIds.forEach(id => allOldItemIds.add(id));
    });
    allOldItemIds.forEach(id => timelineItems.remove(id));

    const accBoardMs = cards.reduce((sum, c) => sum + Math.max(c.headcount * 5, 30) * 1000, 0);
    let totalMs = accBoardMs;
    cards.forEach((card, idx) => {
        totalMs += (parseInt(values[`drive_${idx}`]) || 30) * 60 * 1000;
        totalMs += (parseInt(values[`board_${idx}`]) || 5) * 60 * 1000;
    });

    const tripStart = new Date(deadline.getTime() - totalMs);
    const tripId = `TRIP_${vehicleId}_${Date.now()}`;
    let cursor = new Date(tripStart.getTime() + accBoardMs);

    cards.forEach((card, idx) => {
        const driveMs = (parseInt(values[`drive_${idx}`]) || 30) * 60 * 1000;
        const boardMs = (parseInt(values[`board_${idx}`]) || 5) * 60 * 1000;
        const segStart = new Date(cursor);
        const segEnd = new Date(cursor.getTime() + driveMs + boardMs);

        const outItemId = `${card.id}_OUT_TRIP_${Date.now()}_${idx}`;
        timelineItems.add({
            id: outItemId, group: vehicleId, start: segStart, end: segEnd,
            content: buildItemContent(card, "OUTBOUND"), className: "rp-item-out",
            cardId: card.id, headcount: card.headcount, direction: "OUTBOUND",
            tripId: tripId, title: ""
        });

        const retItemId = `${card.id}_RET_TRIP_${Date.now()}_${idx}`;
        const retStart = new Date(card.return_window_start);
        const retEnd = new Date(retStart.getTime() + 60 * 60 * 1000);
        timelineItems.add({
            id: retItemId, group: vehicleId, start: retStart, end: retEnd,
            content: buildItemContent(card, "RETURN"), className: "rp-item-ret",
            cardId: card.id, headcount: card.headcount, direction: "RETURN",
            title: ""
        });

        assignedCards[card.id] = { vehicleId, itemIds: [outItemId, retItemId], tripId };
        removeCardFromPool(card.id);
        cursor = segEnd;
    });

    frappe.show_alert({
        message: `Trip planned — vehicle departs at ${fmtTimeLocal(tripStart.toISOString())}`,
        indicator: "green"
    }, 6);

    checkConflicts();
    updateSaveButton();
}

function buildItemContent(card, direction) {
    const icon = direction === "OUTBOUND" ? "→" : "←";
    return `
        <div class="rp-item-inner">
            <div class="rp-item-top">
                <span class="rp-item-icon">${icon}</span>
                <span class="rp-item-site">${card.site_location}</span>
                <span class="rp-item-count">👥${card.headcount}</span>
            </div>
            <div class="rp-item-shift">${card.shift_name}</div>
        </div>
    `;
}

function checkConflicts() {
    hideTooltips();
    const all = timelineItems.get();
    all.forEach(item => {
        timelineItems.update({ id: item.id, className: item.className.replace(" rp-item-conflict", "") });
    });
    planData.vehicles.forEach(v => {
        const vItems = timelineItems.get({ filter: i => i.group === v.id });
        vItems.forEach((a, ai) => {
            vItems.forEach((b, bi) => {
                if (ai >= bi) return;
                if (a.tripId && a.tripId === b.tripId) return;
                const aS = new Date(a.start).getTime(), aE = new Date(a.end).getTime();
                const bS = new Date(b.start).getTime(), bE = new Date(b.end).getTime();
                if (aS < bE && aE > bS) {
                    timelineItems.update([
                        { id: a.id, className: a.className + " rp-item-conflict" },
                        { id: b.id, className: b.className + " rp-item-conflict" }
                    ]);
                }
            });
        });
    });
}

function removeCardFromPool(cardId) {
    const el = document.querySelector(`.rp-card[data-id="${CSS.escape(cardId)}"]`);
    if (el) el.remove();
}

function returnCardToPool(cardId) {
    delete assignedCards[cardId];
    const card = planData.shipment_cards.find(c => c.id === cardId);
    if (!card) return;
    const groupEl = document.getElementById(`group-${card.accommodation.replace(/\s+/g, '-')}`);
    if (groupEl) groupEl.insertAdjacentHTML('beforeend', renderCard(card));
}

function updateSaveButton() {
    const btn = document.getElementById('rp-save-btn');
    if (btn) btn.disabled = Object.keys(assignedCards).length === 0;
}

function fmtTimeLocal(isoStr) {
    if (!isoStr) return "—";
    return new Date(isoStr).toLocaleTimeString("en-GB", {
        hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kuwait"
    });
}

// ── Manifest generation ────────────────────────────────────────────
//
//  Builds a synthetic ROUTE_DATA object from the current planner state
//  and opens the route_manifest_template.html in a new tab with the
//  data injected.
// ──────────────────────────────────────────────────────────────────

function buildManifestData() {
    // Slugify for use in shipment labels (the manifest engine splits on "_")
    const slug = s => (s || '').replace(/[\s_]+/g, '-').replace(/[^a-zA-Z0-9\-]/g, '');

    const shipments = [];
    const vehiclesList = [];
    const routes = [];
    const shipmentEmployees = {};
    const shipmentSiteLocations = {};
    const shipmentShiftNames = {};
    const vehicleMeta = {};

    // ── 1. Build one OUTBOUND + one RETURN shipment per assigned card ──
    //
    //  Label format: {accSlug}_S_{siteSlug}_{DIRECTION}
    //  parseLabel() in the manifest engine reads:
    //    acc       = parts[0]               → accSlug (shown as sub-label)
    //    direction = parts[last]            → OUTBOUND | RETURN
    //    title     = shipmentSiteLocations  → real site name (overrides parseLabel location)
    //
    const cardInfoMap = {};
    let shipIdx = 0;

    Object.keys(assignedCards).forEach(cardId => {
        const card = planData.shipment_cards.find(c => c.id === cardId);
        if (!card) return;

        const accSlug = slug(card.accommodation);
        const siteSlug = slug(card.site_location);

        // Make labels unique per card even if acc+site collide across cards
        const uid = shipIdx;
        const outLabel = `${accSlug}_${uid}_${siteSlug}_OUTBOUND`;
        const retLabel = `${accSlug}_${uid}_${siteSlug}_RETURN`;

        const outIdx = shipIdx++;
        const retIdx = shipIdx++;

        shipments.push({ label: outLabel, pickups: [{}], deliveries: [{}] });
        shipments.push({ label: retLabel, pickups: [{}], deliveries: [{}] });

        // Lookup maps used by the manifest renderer
        shipmentEmployees[outLabel] = card.employees;
        shipmentEmployees[retLabel] = card.employees;
        shipmentSiteLocations[outLabel] = card.site_location;
        shipmentSiteLocations[retLabel] = card.site_location;
        shipmentShiftNames[outLabel] = card.shift_name;
        shipmentShiftNames[retLabel] = card.shift_name;

        cardInfoMap[cardId] = { outLabel, retLabel, outIdx, retIdx };
    });

    // ── 2. Build one route per vehicle that has at least one assignment ──
    planData.vehicles.forEach((v, vidx) => {
        vehiclesList.push({ label: v.label, startLocation: null });

        vehicleMeta[v.label] = {
            accommodation: v.accommodation,
            driver: v.driver,
            seats: v.seats,
            location: v.accommodation
        };

        // Get all timeline items for this vehicle and sort chronologically
        const vItems = timelineItems.get({ filter: i => i.group === v.id });
        if (vItems.length === 0) return; // vehicle has no assignments — skip

        vItems.sort((a, b) => new Date(a.start) - new Date(b.start));

        const visits = [];
        const transitions = [];

        // Transition[0]: depot start → first visit
        transitions.push({ travelDuration: "0s", waitDuration: "0s", travelDistanceMeters: 0 });

        vItems.forEach((item, idx) => {
            const info = cardInfoMap[item.cardId];
            if (!info) return;

            const isOutbound = item.direction === "OUTBOUND";
            const shipmentIndex = isOutbound ? info.outIdx : info.retIdx;
            const headcount = item.headcount || 0;
            const itemStartISO = new Date(item.start).toISOString();
            const itemEndISO = new Date(item.end).toISOString();
            const durationMs = new Date(item.end) - new Date(item.start);
            const durationSec = Math.round(durationMs / 1000);

            // ── Pickup visit (depart accommodation / depart site) ──
            visits.push({
                shipmentIndex,
                isPickup: true,
                startTime: itemStartISO,
                loadDemands: { seats: { amount: String(headcount) } }
            });

            // Transition: pickup → dropoff (the driving portion of this leg)
            transitions.push({
                travelDuration: `${durationSec}s`,
                waitDuration: "0s",
                travelDistanceMeters: Math.round(durationSec * 10) // ~36 km/h estimate
            });

            // ── Dropoff visit (arrive at site / arrive at accommodation) ──
            visits.push({
                shipmentIndex,
                isPickup: false,
                startTime: itemEndISO,
                loadDemands: { seats: { amount: String(-headcount) } } // negative = alighting
            });

            // Transition: dropoff → next pickup (gap between this item and the next)
            const nextItem = vItems[idx + 1];
            const gapMs = nextItem
                ? Math.max(0, new Date(nextItem.start) - new Date(item.end))
                : 0;
            transitions.push({
                travelDuration: `${Math.round(gapMs / 1000)}s`,
                waitDuration: "0s",
                travelDistanceMeters: Math.round(gapMs / 1000 * 8)
            });
        });

        // Route window
        const routeStartISO = new Date(vItems[0].start).toISOString();
        const routeEndISO = new Date(vItems[vItems.length - 1].end).toISOString();
        const totalMs = new Date(routeEndISO) - new Date(routeStartISO);

        routes.push({
            vehicleIndex: vidx,
            vehicleLabel: v.label,
            vehicleStartTime: routeStartISO,
            vehicleEndTime: routeEndISO,
            visits,
            transitions,
            metrics: {
                travelDistanceMeters: 0,
                totalDuration: `${Math.round(totalMs / 1000)}s`,
                travelDuration: `${Math.round(totalMs / 1000)}s`
            }
        });
    });

    return {
        request: {
            model: {
                shipments,
                vehicles: vehiclesList,
                globalStartTime: planData.global_start,
                globalEndTime: planData.global_end
            }
        },
        response: {
            routes,
            skippedShipments: [],
            metrics: { totalCost: 0 }
        },
        shipmentEmployees,
        shipmentSiteLocations,
        shipmentShiftNames,
        vehicleMeta
    };
}

async function openManifest() {
    const routeData = buildManifestData();

    if (routeData.response.routes.length === 0) {
        frappe.show_alert({
            message: "No assigned shipments to generate a manifest from.",
            indicator: "orange"
        });
        return;
    }

    const btn = document.getElementById('rp-save-btn');
    const originalLabel = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Generating...";

    let templateHtml;
    try {
        const res = await fetch('/assets/one_fm/html/route_manifest_template.html');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        templateHtml = await res.text();
    } catch (err) {
        frappe.show_alert({
            message: `Could not load manifest template (${err.message}).`,
            indicator: "red"
        }, 8);
        btn.disabled = false;
        btn.textContent = originalLabel;
        return;
    }

    const safeJson = JSON.stringify(routeData).replace(/<\//g, '<\\/');

    const injection = `<script>
    const ROUTE_DATA = ${safeJson};

    // Show any JS error visibly — blob URLs suppress error reporting in some browsers
    window.addEventListener('error', function(e) {
        document.body.style.cssText = 'background:#fff;color:#c00;padding:40px;font-family:monospace;font-size:13px';
        document.body.innerHTML = '<h2 style="margin-bottom:12px">Manifest Error</h2><pre>'
            + e.message + '\\nat line ' + e.lineno + '</pre>';
    });
    <\/script>`;

    const finalHtml = templateHtml.replace('</head>', injection + '\n</head>');

    const blob = new Blob([finalHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60_000);

    btn.disabled = false;
    btn.textContent = originalLabel;

    frappe.show_alert({
        message: `Manifest opened — ${routeData.response.routes.length} vehicles`,
        indicator: "green"
    }, 4);
}

function injectStyles() {
    if (document.getElementById('rp-styles')) return;
    const style = document.createElement('style');
    style.id = 'rp-styles';
    style.textContent = `
        #rp-shell {
            display: flex; flex-direction: column; height: 100vh;
            background: #f5f5f5; font-family: 'Google Sans', Roboto, sans-serif;
        }
        #rp-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 16px 24px; background: #fff;
            border-bottom: 1px solid #e0e0e0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08); flex-shrink: 0;
        }
        #rp-title { font-size: 20px; font-weight: 500; color: #1a1a1a; }
        #rp-date  { font-size: 13px; color: #666; margin-top: 2px; }
        .rp-btn {
            padding: 8px 20px; border-radius: 20px; border: none;
            font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;
        }
        .rp-btn-primary { background: #f97316; color: white; }
        .rp-btn-primary:hover:not(:disabled) { background: #ea6c0a; }
        .rp-btn-primary:disabled { background: #ccc; cursor: not-allowed; }
        .rp-btn-danger  { background: #ef4444; color: white; width: 100%; border-radius: 8px; }
        .rp-btn-danger:hover { background: #dc2626; }

        #rp-body { display: flex; flex: 1; overflow: hidden; }

        /* ── Pool panel ── */
        #rp-pool-panel {
            width: 300px; min-width: 300px; background: #fff;
            border-right: 1px solid #e0e0e0;
            display: flex; flex-direction: column; overflow: hidden;
        }
        #rp-pool-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 16px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
        }
        #rp-pool-title {
            font-size: 13px; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.08em; color: #888;
        }
        #rp-pool-count { font-size: 12px; color: #aaa; }
        #rp-pool-search { padding: 10px 16px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }
        #rp-search-input {
            width: 100%; padding: 8px 12px; border: 1px solid #e0e0e0;
            border-radius: 8px; font-size: 13px; outline: none; transition: border-color 0.2s;
        }
        #rp-search-input:focus { border-color: #f97316; }
        #rp-pool-groups { flex: 1; overflow-y: auto; padding: 8px 0; }

        .rp-pool-group { margin-bottom: 4px; }
        .rp-group-header {
            display: flex; align-items: center; padding: 8px 16px;
            cursor: pointer; user-select: none; background: #fafafa;
            border-top: 1px solid #f0f0f0; border-bottom: 1px solid #f0f0f0;
        }
        .rp-group-header:hover { background: #f5f5f5; }
        .rp-group-label   { flex: 1; font-size: 13px; font-weight: 600; color: #333; }
        .rp-group-count   { font-size: 11px; color: #999; margin-right: 8px; }
        .rp-group-chevron { font-size: 12px; color: #999; }
        .rp-group-cards   { display: flex; flex-direction: column; gap: 8px; padding: 8px 12px; }

        .rp-card {
            background: #fff; border: 1px solid #e8e8e8; border-radius: 12px;
            padding: 12px; cursor: grab;
            transition: box-shadow 0.2s, transform 0.15s;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .rp-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); transform: translateY(-1px); }
        .rp-card:active { cursor: grabbing; }
        .rp-card-header  { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
        .rp-card-site    { font-size: 14px; font-weight: 600; color: #1a1a1a; }
        .rp-card-type    { font-size: 10px; font-weight: 700; letter-spacing: 0.06em; padding: 2px 7px; border-radius: 4px; }
        .rp-tag-osm { background: #e8f4fd; color: #1a73e8; }
        .rp-tag-olm { background: #f3e8fd; color: #7c3aed; }
        .rp-card-shift   { font-size: 11px; color: #888; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .rp-card-meta    { display: flex; flex-direction: column; gap: 3px; margin-bottom: 8px; }
        .rp-card-meta-item { font-size: 12px; color: #555; display: flex; align-items: center; gap: 5px; }
        .rp-meta-icon    { font-size: 11px; }
        .rp-card-windows { display: flex; gap: 6px; margin-bottom: 8px; }
        .rp-window       { flex: 1; border-radius: 6px; padding: 4px 8px; display: flex; flex-direction: column; }
        .rp-window-out   { background: #e8f5e9; }
        .rp-window-ret   { background: #fff3e0; }
        .rp-window-label { font-size: 9px; font-weight: 700; letter-spacing: 0.08em; color: #888; }
        .rp-window-time  { font-size: 11px; font-weight: 500; color: #333; }
        .rp-card-employees { display: flex; flex-wrap: wrap; gap: 4px; }
        .rp-emp-chip  { font-size: 10px; background: #f5f5f5; border: 1px solid #e8e8e8; border-radius: 4px; padding: 2px 6px; color: #555; }
        .rp-emp-more  { background: #f0f0f0; color: #888; }

        /* ── Timeline panel ── */
        #rp-timeline-panel {
            flex: 1; display: flex; flex-direction: column; overflow: hidden;
        }
        #rp-timeline-toolbar {
            display: flex; align-items: center; justify-content: space-between;
            padding: 10px 16px; background: #fff; border-bottom: 1px solid #e0e0e0;
            flex-shrink: 0;
        }
        #rp-timeline-zoom { display: flex; gap: 6px; }
        .rp-btn-icon {
            padding: 4px 12px; border: 1px solid #e0e0e0; border-radius: 6px;
            background: #fff; cursor: pointer; font-size: 14px; color: #555;
        }
        .rp-btn-icon:hover { background: #f5f5f5; }
        #rp-timeline-legend { display: flex; gap: 12px; align-items: center; }
        .rp-legend-item     { font-size: 12px; padding: 3px 10px; border-radius: 4px; font-weight: 500; }
        .rp-legend-out      { background: #e3f2fd; color: #1565c0; }
        .rp-legend-ret      { background: #fff3e0; color: #e65100; }
        .rp-legend-conflict { background: #ffebee; color: #c62828; }

        /* ── Sticky axis ── */
        #rp-timeline-axis-container {
            flex-shrink: 0; position: sticky; top: 0; z-index: 10;
            background: #fff; border-bottom: 1px solid #e0e0e0;
        }
        #rp-timeline-axis-container .vis-timeline { border: none !important; }

        /* ── Scrollable rows ── */
        #rp-timeline-container { flex: 1; overflow-y: auto; overflow-x: hidden; }
        #rp-timeline-container .vis-timeline { border: none !important; }
        #rp-timeline-container.rp-drop-active {
            outline: 2px dashed #f97316; outline-offset: -2px;
            background: rgba(249,115,22,0.03);
        }

        /* ── Detail panel ── */
        #rp-detail-panel {
            width: 300px; min-width: 300px; background: #fff;
            border-left: 1px solid #e0e0e0;
            display: flex; flex-direction: column;
            transition: width 0.2s, min-width 0.2s;
            overflow: hidden;
        }
        #rp-detail-panel.rp-detail-hidden {
            width: 0; min-width: 0;
        }
        #rp-detail-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 16px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0;
        }
        #rp-detail-title {
            font-size: 13px; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.08em; color: #888;
        }
        #rp-detail-close {
            background: none; border: none; cursor: pointer;
            font-size: 16px; color: #aaa; padding: 2px 6px; border-radius: 4px;
        }
        #rp-detail-close:hover { background: #f5f5f5; color: #555; }
        #rp-detail-body { flex: 1; overflow-y: auto; padding: 16px; }
        #rp-detail-footer { padding: 16px; border-top: 1px solid #f0f0f0; flex-shrink: 0; }

        .rp-detail-section { margin-bottom: 16px; }
        .rp-detail-label {
            font-size: 10px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.08em; color: #aaa; margin-bottom: 4px;
        }
        .rp-detail-value { font-size: 13px; color: #1a1a1a; line-height: 1.4; }

        /* ── Vehicle group labels ── */
        .rp-group-vehicle { padding: 4px 8px; }
        .rp-gv-label { font-size: 13px; font-weight: 600; color: #1a1a1a; }
        .rp-gv-meta  { font-size: 11px; color: #888; margin-top: 1px; }
        .rp-gv-acc   { font-size: 10px; color: #aaa; margin-top: 1px; }
        .vis-label { min-height: 70px !important; }
        .vis-group { min-height: 70px !important; }

        /* ── Timeline items ── */
        .vis-item { min-height: 36px !important; line-height: 1.3 !important; }
        .vis-item .vis-item-content { padding: 4px 8px !important; width: 100%; }
        .rp-item-out      { background: #1565c0 !important; border-color: #0d47a1 !important; color: white !important; border-radius: 6px !important; }
        .rp-item-ret      { background: #e65100 !important; border-color: #bf360c !important; color: white !important; border-radius: 6px !important; }
        .rp-item-conflict { background: #c62828 !important; border-color: #b71c1c !important; }
        .vis-item.vis-selected { box-shadow: 0 0 0 3px rgba(249,115,22,0.5) !important; }
        .rp-item-inner { display: flex; flex-direction: column; gap: 2px; padding: 2px 0; font-size: 11px; overflow: hidden; }
        .rp-item-top   { display: flex; align-items: center; gap: 4px; overflow: hidden; }
        .rp-item-icon  { font-size: 11px; flex-shrink: 0; }
        .rp-item-site  { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .rp-item-count { font-size: 10px; opacity: 0.85; flex-shrink: 0; }
        .rp-item-shift { font-size: 10px; opacity: 0.75; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

        /* ── Suppress vis built-in tooltip ── */
        .vis-tooltip { display: none !important; }
    `;
    document.head.appendChild(style);
}