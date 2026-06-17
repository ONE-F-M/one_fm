/**
 * Transportation Manifest — Persistent Frappe Page
 *
 * URL: /app/transportation-manifest/<Route_Plan_Name>
 *
 * Fetches manifest data from the server using the plan name in the URL,
 * then renders the same manifest UI previously served via a blob: URL.
 * Redesigned for DRIVERS — large text, big tap targets, mobile-first.
 */

frappe.pages["transportation-manifest"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Transportation Manifest"),
		single_column: true,
	});

	// Remove Frappe page header — we render our own branded header
	$(wrapper).find(".page-head").hide();

	const $container = $(wrapper).find(".layout-main-section");
	$container.empty();

	// Extract plan name from URL: /app/transportation-manifest/<plan_name>
	const route = frappe.get_route();
	const planName = route.length > 1 ? route.slice(1).join("/") : "";

	const STATE_STYLES = `
		<style>
			.mfst-state-screen { display:flex; flex-direction:column; align-items:center; justify-content:center; padding:80px 40px; text-align:center; min-height:60vh; font-family:'Google Sans',Roboto,sans-serif; }
			.mfst-state-screen .mfst-state-icon { font-size:64px; margin-bottom:20px; color:#9ca3af; }
			.mfst-state-screen .mfst-state-icon.error { color:#ef4444; }
			.mfst-state-screen h2 { font-size:24px; font-weight:700; color:#1f1f1f; margin:0 0 10px; }
			.mfst-state-screen p { font-size:15px; line-height:1.7; color:#6b7280; margin:0 0 24px; max-width:480px; }
			.mfst-state-btn { display:inline-flex; align-items:center; gap:8px; padding:12px 28px; border-radius:8px; font-size:14px; font-weight:600; text-decoration:none; cursor:pointer; border:none; transition:all 0.2s; }
			.mfst-state-btn-primary { background:#f97316; color:#fff; }
			.mfst-state-btn-primary:hover { background:#ea580c; transform:translateY(-1px); box-shadow:0 4px 12px rgba(249,115,22,0.3); }
			.mfst-state-btn-secondary { background:#f3f4f6; color:#374151; border:1px solid #d1d5db; }
			.mfst-state-btn-secondary:hover { background:#e5e7eb; }
			.mfst-state-btn-group { display:flex; gap:12px; flex-wrap:wrap; justify-content:center; }
			@keyframes mfst-spin { to { transform:rotate(360deg); } }
			.mfst-spinner { width:48px; height:48px; border:4px solid #e5e7eb; border-top-color:#f97316; border-radius:50%; animation:mfst-spin 0.8s linear infinite; margin-bottom:24px; }
		</style>
	`;

	if (!planName) {
		$container.html(`
			${STATE_STYLES}
			<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
			<div class="mfst-state-screen">
				<span class="material-symbols-outlined mfst-state-icon">directions_bus</span>
				<h2>No Transportation Plan Selected</h2>
				<p>
					To view a manifest, open the <strong>Transportation Schedule</strong> page,
					select a plan, and tap the <strong>Manifest</strong> button.
				</p>
				<a href="/app/transportation-schedule" class="mfst-state-btn mfst-state-btn-primary">
					<span class="material-symbols-outlined" style="font-size:18px">arrow_back</span>
					Go to Transportation Schedule
				</a>
			</div>
		`);
		return;
	}

	// Show loading
	$container.html(`
		${STATE_STYLES}
		<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
		<div class="mfst-state-screen">
			<div class="mfst-spinner"></div>
			<h2>Loading Manifest…</h2>
			<p>Fetching vehicle assignments and employee data. This usually takes a few seconds.</p>
		</div>
	`);

	// Fetch manifest data from server
	frappe.call({
		method: "one_fm.one_fm.page.transportation_schedule.transportation_schedule.get_manifest_data_for_plan",
		args: { plan_name: planName },
		async: true,
		callback: function (r) {
			if (!r.message || r.message.status === "empty") {
				$container.html(`
					${STATE_STYLES}
					<div class="mfst-state-screen">
						<span class="material-symbols-outlined mfst-state-icon">inventory_2</span>
						<h2>No Assignments Yet</h2>
						<p>
							This plan doesn't have any vehicle assignments saved yet.<br>
							Ask the Dispatcher to assign vehicles and employees in the Transportation Schedule first.
						</p>
						<a href="/app/transportation-schedule" class="mfst-state-btn mfst-state-btn-primary">
							<span class="material-symbols-outlined" style="font-size:18px">arrow_back</span>
							Open Transportation Schedule
						</a>
					</div>
				`);
				return;
			}

			if (r.message.status !== "ok") {
				$container.html(`
					${STATE_STYLES}
					<div class="mfst-state-screen">
						<span class="material-symbols-outlined mfst-state-icon error">error_outline</span>
						<h2>Something Went Wrong</h2>
						<p>${frappe.utils.escape_html(r.message.message || "We couldn't load this manifest. Please try again or contact the Dispatcher.")}</p>
						<div class="mfst-state-btn-group">
							<button class="mfst-state-btn mfst-state-btn-primary" onclick="location.reload()">
								<span class="material-symbols-outlined" style="font-size:18px">refresh</span>
								Try Again
							</button>
							<a href="/app/transportation-schedule" class="mfst-state-btn mfst-state-btn-secondary">
								Go to Schedule
							</a>
						</div>
					</div>
				`);
				return;
			}

			// Render the manifest
			renderManifest($container, r.message);
		},
		error: function () {
			$container.html(`
				${STATE_STYLES}
				<div class="mfst-state-screen">
					<span class="material-symbols-outlined mfst-state-icon error">wifi_off</span>
					<h2>Unable to Load Manifest</h2>
					<p>
						We couldn't reach the server. Please check your internet connection and try again.<br>
						If the problem continues, contact the Dispatcher for help.
					</p>
					<div class="mfst-state-btn-group">
						<button class="mfst-state-btn mfst-state-btn-primary" onclick="location.reload()">
							<span class="material-symbols-outlined" style="font-size:18px">refresh</span>
							Try Again
						</button>
						<a href="/app/transportation-schedule" class="mfst-state-btn mfst-state-btn-secondary">
							Go to Schedule
						</a>
					</div>
				</div>
			`);
		},
	});
};


// ════════════════════════════════════════════════════════════════════════════
//  MANIFEST RENDERER — Driver-Friendly Design
// ════════════════════════════════════════════════════════════════════════════

function renderManifest($container, data) {
	const ROUTE_DATA = data.route_data;
	const SITE_URL = window.location.origin;
	const FRAPPE_CSRF_TOKEN = frappe.csrf_token;

	// Inject CSS + HTML skeleton
	$container.html(getManifestHTML());

	// Inject CSS into head
	if (!document.getElementById("manifest-page-css")) {
		const style = document.createElement("style");
		style.id = "manifest-page-css";
		style.textContent = getManifestCSS();
		document.head.appendChild(style);
	}

	// ── State ──
	let activeView = null;
	let shipmentEmployees = {};
	let shipmentReturnEmployees = {};
	let shipmentSiteLocations = {};
	let shipmentShiftNames = {};

	// Expose state globally for modal scripts
	window.manifestData = data;
	window.checkerState = window.checkerState || {};

	// ── Utilities ──
	function fmtTime(isoStr) {
		if (!isoStr) return "—";
		const d = new Date(isoStr);
		return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kuwait" });
	}

	function escHtml(s) {
		if (!s) return "";
		return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
	}

	function showToast(msg) {
		const toast = document.createElement("div");
		toast.textContent = msg;
		toast.style.cssText = "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:12px 24px;border-radius:12px;font-size:15px;z-index:9999;opacity:0;transition:opacity 0.3s;font-family:var(--mfst-font-body);box-shadow:0 4px 12px rgba(0,0,0,0.25)";
		document.body.appendChild(toast);
		requestAnimationFrame(() => toast.style.opacity = "1");
		setTimeout(() => { toast.style.opacity = "0"; setTimeout(() => toast.remove(), 300); }, 2500);
	}

	function showNoNumber(name) {
		showToast("No mobile number on file for " + name);
	}

	function copyNumber(event, mobile) {
		event.preventDefault();
		event.stopPropagation();
		navigator.clipboard.writeText(mobile).then(() => {
			showToast("Number Copied: " + mobile);
		}).catch(() => {
			showToast(mobile);
		});
	}

	// Make functions globally accessible for onclick handlers
	window._mfst_showNoNumber = showNoNumber;
	window._mfst_copyNumber = copyNumber;

	function empChipHtml(e, chipStyle, interactive) {
		interactive = interactive || false;
		const id = (typeof e === "object" && e !== null) ? (e.id || e.name || "—") : (e || "—");
		const name = (typeof e === "object" && e !== null) ? (e.name || "—") : (e || "—");
		const rawMobile = (typeof e === "object" && e !== null) ? (e.mobile || "") : "";
		const mobile = rawMobile.replace(/[^\d+\-() ]/g, "");

		const state = window.checkerState[id] || {};

		let classes = "mfst-emp-chip";
		let displayName = name;
		let statusIcon = "";

		if (state.replacement) {
			classes += " mfst-state-replacement";
			displayName = state.replacement.name;
			statusIcon = `<span class="material-symbols-outlined mfst-chip-status-icon">swap_horiz</span>`;
		} else if (state.attendance === "Absent") {
			classes += " mfst-state-error";
			statusIcon = `<span class="material-symbols-outlined mfst-chip-status-icon">close</span>`;
		} else if (state.attendance === "Present" && state.qoa === "Fail") {
			classes += " mfst-state-warning";
			statusIcon = `<span class="material-symbols-outlined mfst-chip-status-icon">warning</span>`;
		} else if (state.attendance === "Present" && state.qoa === "Pass") {
			classes += " mfst-state-success";
			statusIcon = `<span class="material-symbols-outlined mfst-chip-status-icon">check_circle</span>`;
		}

		if (interactive) {
			classes += " mfst-interactive";
		}

		const esc = s => s.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
		const safeName = esc(displayName);
		const safeMobile = esc(mobile);
		let phoneIcon;
		if (mobile || (state.replacement && state.replacement.mobile)) {
			const mobToUse = (state.replacement && state.replacement.mobile) ? state.replacement.mobile.replace(/[^\d+\-() ]/g, "") : safeMobile;
			const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry/i.test(navigator.userAgent);
			if (isMobile) {
				phoneIcon = `<a href="tel:${mobToUse}" class="mfst-emp-call-btn" title="Call ${mobToUse}" onclick="event.stopPropagation()"><span class="material-symbols-outlined">call</span></a>`;
			} else {
				phoneIcon = `<span class="mfst-emp-call-btn" title="Copy ${mobToUse}" onclick="window._mfst_copyNumber(event,'${mobToUse}')"><span class="material-symbols-outlined">call</span></span>`;
			}
		} else {
			phoneIcon = `<span class="mfst-emp-call-btn mfst-emp-call-disabled" title="No mobile number" onclick="event.stopPropagation();window._mfst_showNoNumber('${safeName}')"><span class="material-symbols-outlined">call</span></span>`;
		}

		const onclickAttr = interactive ? ` onclick="window._mfst_openCheckInModal('${esc(id)}', '${safeName}')"` : "";
		return `<span class="${classes}"${onclickAttr}><span class="mfst-chip-name">${safeName}</span>${statusIcon}${phoneIcon}</span>`;
	}

	function fmtDuration(secStr) {
		if (!secStr) return "";
		let s = parseInt(secStr.replace("s", ""), 10);
		if (isNaN(s) || s === 0) return "";
		if (s > 86400) s = 86400;
		if (s < 60) return `${s}s`;
		if (s < 3600) return `${Math.round(s / 60)} min`;
		const h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60);
		return m ? `${h}h ${m}m` : `${h}h`;
	}

	function fmtKm(m) {
		return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${m} m`;
	}

	function parseLabel(label) {
		const parts = label.split("_");
		const direction = parts[parts.length - 1];
		const location = parts.slice(0, -1).join("_").split("_").slice(2).join(" ");
		const acc = parts[0];
		return { acc, location, direction, raw: label };
	}

	function seatsLoad(demands) {
		if (!demands) return 0;
		const raw = demands.seats?.amount ?? "0";
		return parseInt(raw, 10) || 0;
	}

	function buildRoute(route, shipments, vehicles) {
		const vidx = route.vehicleIndex ?? 0;
		const vehicle = vehicles[vidx] ?? {};
		const label = route.vehicleLabel ?? vehicle.label ?? `Vehicle ${vidx}`;
		const startLoc = vehicle.startLocation;
		const vehicleMeta = (ROUTE_DATA.vehicleMeta ?? {})[label] ?? {};

		let currentLoad = 0;
		const visits = route.visits ?? [];
		const trans = route.transitions ?? [];
		const stops = [];

		stops.push({
			type: "depot",
			time: route.vehicleStartTime,
			title: vehicleMeta.accommodation || vehicleMeta.location || "Depot / Garage",
			depotNote: "Vehicle start location - Employee pick-up starts here",
			subtitle: startLoc ? `${startLoc.latitude.toFixed(4)}, ${startLoc.longitude.toFixed(4)}` : "Start location",
			load: 0,
			transition: trans[0]
		});

		visits.forEach((v, i) => {
			const shipment = shipments[v.shipmentIndex] ?? {};
			const isRest = (shipment.label ?? "").endsWith("_REST");
			const isPickup = v.isPickup !== false;
			const delta = seatsLoad(v.loadDemands);
			currentLoad += delta;

			const parsed = parseLabel(shipment.label ?? "Unknown");
			const visitReq = isPickup ? (shipment.pickups?.[0] ?? {}) : (shipment.deliveries?.[0] ?? {});
			const coords = visitReq.arrivalLocation;

			stops.push({
				type: isPickup ? "pickup" : "dropoff",
				isRest: isRest,
				time: v.startTime,
				title: isRest ? `Rest at ${vehicleMeta.accommodation || vehicleMeta.location || "Depot"}` : (shipmentSiteLocations[parsed.raw] || parsed.location || shipment.label),
				subtitle: coords ? `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}` : "",
				direction: parsed.direction,
				acc: parsed.acc,
				raw: parsed.raw,
				load: currentLoad,
				delta: delta,
				transition: trans[i + 1],
				tripId: v.tripId || null,
				tripName: v.tripName || null,
				stopIndex: v.stopIndex || 0
			});
		});

		stops.push({
			type: "end",
			time: route.vehicleEndTime,
			title: `Return to ${vehicleMeta.accommodation || vehicleMeta.location || "Depot"}`,
			load: 0
		});

		return { label, stops, route, vehicle };
	}

	// ── INIT ──
	const req = ROUTE_DATA.request;
	const res = ROUTE_DATA.response;
	const shipments = req.model.shipments ?? [];
	const vehicles = req.model.vehicles ?? [];
	const routes = res.routes ?? [];
	const skipped = res.skippedShipments ?? [];

	shipmentEmployees = ROUTE_DATA.shipmentEmployees ?? {};
	shipmentReturnEmployees = ROUTE_DATA.shipmentReturnEmployees ?? {};
	shipmentSiteLocations = ROUTE_DATA.shipmentSiteLocations ?? {};
	shipmentShiftNames = ROUTE_DATA.shipmentShiftNames ?? {};

	const parsed = routes.map(r => buildRoute(r, shipments, vehicles));

	// Header date
	const now = new Date();
	$container.find("#mfst-run-date").text(
		now.toLocaleDateString("en-GB", { weekday: "long", day: "2-digit", month: "short", year: "numeric", timeZone: "Asia/Kuwait" })
	);
	if (data.plan_title) {
		$container.find("#mfst-plan-title").text(data.plan_title);
	}

	// ── BUILD VEHICLE TABS ──
	const tabBar = $container.find("#mfst-tab-bar")[0];
	tabBar.innerHTML = "";

	parsed.forEach((pr, idx) => {
		const meta = (ROUTE_DATA.vehicleMeta ?? {})[pr.label] ?? {};
		const tab = document.createElement("button");
		tab.className = "mfst-tab";
		tab.innerHTML = `
			<span class="mfst-tab-name">${pr.label}</span>
			${meta.license_plate ? `<span class="mfst-tab-plate">${escHtml(meta.license_plate)}</span>` : ""}
			<span class="mfst-tab-time">${fmtTime(pr.route.vehicleStartTime)} → ${fmtTime(pr.route.vehicleEndTime)}</span>
		`;
		tab.addEventListener("click", () => {
			$container.find(".mfst-tab").removeClass("active");
			$container.find(".mfst-skipped-tab").removeClass("active");
			$(tab).addClass("active");
			renderRoute(pr);
		});
		tabBar.appendChild(tab);
		if (idx === 0) {
			tab.classList.add("active");
			activeView = pr;
		}
	});

	// Skipped tab
	if (skipped.length > 0) {
		const sk = document.createElement("button");
		sk.className = "mfst-tab mfst-skipped-tab";
		sk.innerHTML = `<span class="mfst-tab-name" style="color:var(--mfst-red)"><span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">warning</span> Skipped</span><span class="mfst-tab-plate" style="background:var(--mfst-red);color:#fff;padding:2px 8px;border-radius:10px">${skipped.length}</span>`;
		sk.addEventListener("click", () => {
			$container.find(".mfst-tab").removeClass("active");
			$(sk).addClass("active");
			renderSkipped(skipped);
		});
		tabBar.appendChild(sk);
	}

	// Wire up Print and Help buttons
	$container.on("click", "#mfst-btn-print", function() {
		window.print();
	});

	$container.on("click", "#mfst-btn-help", function() {
		$container.find("#mfst-helpPanel").toggleClass("active");
	});

	$container.on("click", "#mfst-btn-close-help", function() {
		$container.find("#mfst-helpPanel").removeClass("active");
		try { localStorage.setItem("mfst_help_seen", "1"); } catch(e) {}
	});

	// Show help panel automatically for first-time visitors
	try {
		if (!localStorage.getItem("mfst_help_seen")) {
			setTimeout(() => $container.find("#mfst-helpPanel").addClass("active"), 800);
		}
	} catch(e) {}

	// Render first vehicle
	if (parsed.length > 0) {
		renderRoute(parsed[0]);
	} else {
		$container.find("#mfst-main").html(`
			<div class="mfst-empty-state">
				<span class="material-symbols-outlined" style="font-size:56px;color:var(--mfst-text-dim);margin-bottom:16px">no_transfer</span>
				<h2>No Routes Found</h2>
				<p>This plan doesn't have any active vehicle routes yet.<br>Ask the Dispatcher to assign vehicles and save the plan first.</p>
				<a href="/app/transportation-schedule" class="mfst-state-btn mfst-state-btn-primary" style="margin-top:8px;display:inline-flex;align-items:center;gap:8px;padding:12px 28px;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;background:#f97316;color:#fff">
					<span class="material-symbols-outlined" style="font-size:18px">arrow_back</span>
					Open Transportation Schedule
				</a>
			</div>
		`);
	}

	// ── RENDER ROUTE ──
	function renderRoute(pr) {
		activeView = pr;
		const meta = (ROUTE_DATA.vehicleMeta ?? {})[pr.label] ?? {};
		const accommodation = meta.accommodation || meta.location || "Depot";
		const allTrips = buildTrips(pr);

		// ─ Compute Total Time & Trip Time ─
		const m = pr.route.metrics ?? {};
		const totalTimeStr = m.totalDuration ? fmtDuration(m.totalDuration) : "—";
		const tripTimeStr = m.travelDuration ? fmtDuration(m.travelDuration) : "—";

		// ─ Vehicle Info Card ─
		const infoParts = [];
		if (meta.driver && meta.driver !== "—") infoParts.push(`<span class="material-symbols-outlined mfst-info-icon">person</span> ${escHtml(meta.driver)}`);
		if (meta.make) infoParts.push(meta.make);
		if (meta.type) infoParts.push(meta.type);
		if (meta.seats) infoParts.push(`${meta.seats} seats`);

		let html = `
			<div class="mfst-vehicle-card">
				<div class="mfst-vehicle-card-top">
					<div class="mfst-vehicle-card-left">
						<div class="mfst-vehicle-name">
							<span class="material-symbols-outlined" style="font-size:28px;vertical-align:middle;margin-right:8px;color:var(--mfst-accent)">directions_bus</span>
							${pr.label}
						</div>
						${meta.license_plate ? `<div class="mfst-vehicle-plate">${escHtml(meta.license_plate)}</div>` : ""}
					</div>
					<div class="mfst-vehicle-card-right">
						<div class="mfst-vehicle-time-badge">
							<span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle">schedule</span>
							${fmtTime(pr.route.vehicleStartTime)} → ${fmtTime(pr.route.vehicleEndTime)}
						</div>
						<div class="mfst-vehicle-trips">${allTrips.length} trip${allTrips.length !== 1 ? "s" : ""}</div>
					</div>
				</div>
				<div class="mfst-vehicle-stats">
					<div class="mfst-stat-box">
						<div class="mfst-stat-val">${totalTimeStr}</div>
						<div class="mfst-stat-lbl">Total Time</div>
					</div>
					<div class="mfst-stat-box">
						<div class="mfst-stat-val">${tripTimeStr}</div>
						<div class="mfst-stat-lbl">Trip Time</div>
					</div>
				</div>
				${infoParts.length > 0 ? `<div class="mfst-vehicle-card-details">${infoParts.join(" · ")}</div>` : ""}
			</div>
		`;

		// ─ Render Trips ─
		allTrips.forEach((trip, ti) => {
			const tripStops = trip.stops;
			if (!tripStops.length) return;

			function calcTransit(t1, t2) {
				const ms = new Date(t2).getTime() - new Date(t1).getTime();
				if (ms <= 0) return { travelDuration: "0s", waitDuration: "0s", travelDistanceMeters: 0 };
				return { travelDuration: Math.round(ms / 1000) + "s", waitDuration: "0s", travelDistanceMeters: 0 };
			}

			const actualSiteStops = [];
			tripStops.forEach(stop => {
				if (stop.direction === "OUTBOUND" && stop.type === "pickup") return;
				if (stop.direction === "RETURN" && stop.type === "dropoff") return;
				actualSiteStops.push(stop);

				if (stop.direction === "OUTBOUND" && stop.type === "dropoff") {
					const retEmps = shipmentReturnEmployees[stop.raw] || [];
					if (retEmps.length > 0) {
						actualSiteStops.push({
							...stop,
							type: "pickup",
							_isVirtualReturn: true,
							_virtualEmps: retEmps
						});
					}
				}
			});

			const siteStops = {};
			actualSiteStops.forEach(stop => {
				const site = shipmentSiteLocations[stop.raw] || stop.title || "Unknown";
				if (!siteStops[site]) siteStops[site] = { dropoffs: [], pickups: [] };
				if (stop.type === "dropoff") siteStops[site].dropoffs.push(stop);
				else if (stop.type === "pickup") siteStops[site].pickups.push(stop);
			});

			const siteOrder = Object.entries(siteStops)
				.map(([site, sdata]) => {
					const allS = [...sdata.dropoffs, ...sdata.pickups];
					const earliest = allS.reduce((mn, s) => Math.min(mn, new Date(s.time).getTime()), Infinity);
					return { site, data: sdata, earliest };
				})
				.sort((a, b) => a.earliest - b.earliest);

			const orderedStops = [];
			siteOrder.forEach(({ site, data: sdata }, siteIdx) => {
				const siteNum = siteIdx + 1;
				sdata.dropoffs.sort((a, b) => new Date(a.time) - new Date(b.time));
				sdata.pickups.sort((a, b) => new Date(a.time) - new Date(b.time));
				const maxLen = Math.max(sdata.dropoffs.length, sdata.pickups.length);
				for (let i = 0; i < maxLen; i++) {
					if (i < sdata.dropoffs.length) orderedStops.push({ stop: sdata.dropoffs[i], siteNum });
					if (i < sdata.pickups.length) orderedStops.push({ stop: sdata.pickups[i], siteNum });
				}
			});

			const firstTime = tripStops.reduce((min, s) => { const t = new Date(s.time).getTime(); return t < min ? t : min; }, Infinity);
			const lastTime = tripStops.reduce((max, s) => { const t = new Date(s.time).getTime(); return t > max ? t : max; }, 0);
			const firstTimeISO = new Date(firstTime).toISOString();
			const lastTimeISO = new Date(lastTime).toISOString();

			const hasOutbound = tripStops.some(s => s.direction === "OUTBOUND");
			const hasReturn = tripStops.some(s => s.direction === "RETURN");
			const dirClass = !hasOutbound && hasReturn ? "return" : "outbound";
			const dirIcon = !hasOutbound && hasReturn ? "keyboard_return" : "arrow_forward";

			html += `
				<div class="mfst-trip-group ${dirClass}">
					<div class="mfst-trip-header">
						<span class="material-symbols-outlined mfst-trip-header-icon">${dirIcon}</span>
						<span class="mfst-trip-header-title">${escHtml(trip.label)}</span>
						<span class="mfst-trip-header-meta">${siteOrder.length} site${siteOrder.length !== 1 ? "s" : ""} · ${fmtTime(firstTimeISO)} → ${fmtTime(lastTimeISO)}</span>
					</div>
					<div class="mfst-trip-body">
			`;

			// Boarding employees for DEPART
			const boardingEmployees = [];
			const boardingNames = new Set();
			orderedStops.forEach(item => {
				if (item.stop.type === "dropoff") {
					(shipmentEmployees[item.stop.raw] ?? []).forEach(e => {
						const eName = (typeof e === "object" && e !== null) ? (e.name || "") : (e || "");
						if (eName && !boardingNames.has(eName)) {
							boardingNames.add(eName);
							boardingEmployees.push(e);
						}
					});
				}
			});

			// DEPART card
			html += renderDepartCard(firstTimeISO, accommodation, boardingEmployees);

			// Transit to first site
			const firstSiteStop = orderedStops[0]?.stop;
			if (firstSiteStop) {
				html += renderTransit(calcTransit(firstTimeISO, firstSiteStop.time));
			}

			// Site stops
			orderedStops.forEach((item, si) => {
				const stop = item.stop;
				const siteNum = item.siteNum;
				const site = shipmentSiteLocations[stop.raw] || stop.title || "Unknown";
				const emps = stop._isVirtualReturn ? stop._virtualEmps : (shipmentEmployees[stop.raw] ?? []);
				const shift = shipmentShiftNames[stop.raw] || "";
				const isDropoff = stop.type === "dropoff";

				let empHtml = "";
				if (emps.length > 0) {
					const actionWord = isDropoff ? "Dropping off" : "Picking up";
					const actionColor = isDropoff ? "var(--mfst-accent)" : "var(--mfst-green)";
					const actionIcon = isDropoff ? "south" : "north";
					empHtml = `<div class="mfst-stop-emp-section">
						<div class="mfst-stop-emp-label" style="color:${actionColor}">
							<span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">${actionIcon}</span>
							${actionWord} ${emps.length} employee${emps.length !== 1 ? "s" : ""}
						</div>
						<div class="mfst-stop-employees">${emps.map(n => empChipHtml(n)).join("")}</div>
					</div>`;
				}

				html += `
					<div class="mfst-stop-card ${isDropoff ? 'dropoff' : 'pickup'}">
						<div class="mfst-stop-card-header">
							<div class="mfst-stop-card-left">
								<span class="mfst-stop-tag ${isDropoff ? 'tag-dropoff' : 'tag-pickup'}">${isDropoff ? 'DROP OFF' : 'PICK UP'}</span>
								<span class="mfst-stop-tag tag-stop">STOP ${siteNum}</span>
							</div>
							<div class="mfst-stop-card-time">
								<span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">schedule</span>
								${fmtTime(stop.time)}
							</div>
						</div>
						<div class="mfst-stop-card-title">${escHtml(site)}</div>
						${shift ? `<div class="mfst-stop-card-shift">${escHtml(shift)}</div>` : ""}
						${empHtml}
					</div>
				`;

				if (si < orderedStops.length - 1) {
					const nextStop = orderedStops[si + 1].stop;
					if (item.siteNum !== orderedStops[si + 1].siteNum) {
						html += renderTransit(calcTransit(stop.time, nextStop.time));
					}
				}
			});

			// Return employees
			const returningEmployees = [];
			const returningNames = new Set();
			orderedStops.forEach(item => {
				if (item.stop.type === "pickup") {
					const stopEmps = item.stop._isVirtualReturn ? item.stop._virtualEmps : (shipmentEmployees[item.stop.raw] ?? []);
					stopEmps.forEach(e => {
						const eName = (typeof e === "object" && e !== null) ? (e.name || "") : (e || "");
						if (eName && !returningNames.has(eName)) {
							returningNames.add(eName);
							returningEmployees.push(e);
						}
					});
				}
			});

			// Transit to return
			const lastSiteStop = orderedStops[orderedStops.length - 1]?.stop;
			if (lastSiteStop) {
				html += renderTransit(calcTransit(lastSiteStop.time, lastTimeISO));
			}

			// RETURN card
			html += renderReturnCard(lastTimeISO, accommodation, returningEmployees);

			html += `</div></div>`;

			if (ti < allTrips.length - 1) {
				html += `<div style="height:12px"></div>`;
			}
		});

		$container.find("#mfst-main").html(html);
	}

	function buildTrips(pr) {
		const tripMap = {};
		const soloStops = [];

		pr.stops.forEach(stop => {
			if (stop.type === "depot" || stop.type === "end") return;
			if (stop.tripId) {
				if (!tripMap[stop.tripId]) tripMap[stop.tripId] = [];
				tripMap[stop.tripId].push(stop);
			} else {
				soloStops.push(stop);
			}
		});

		const tripIds = Object.keys(tripMap);
		const allTrips = [];
		tripIds.forEach((tid, i) => {
			const tripStops = tripMap[tid];
			const name = tripStops.find(s => s.tripName)?.tripName || `Trip ${i + 1}`;
			allTrips.push({ id: tid, label: name, stops: tripStops });
		});
		if (soloStops.length > 0) {
			allTrips.push({ id: null, label: allTrips.length > 0 ? `Trip ${allTrips.length + 1} (Independent)` : "Trip 1", stops: soloStops });
		}
		if (allTrips.length === 0) {
			allTrips.push({ id: null, label: "Trip 1", stops: pr.stops.filter(s => s.type !== "depot" && s.type !== "end") });
		}
		return allTrips;
	}

	function renderDepartCard(time, accommodation, employees) {
		let empHtml = "";
		if (employees.length > 0) {
			empHtml = `<div class="mfst-stop-emp-section">
				<div class="mfst-depart-emp-header">
					<div class="mfst-stop-emp-label" style="color:var(--mfst-green)">
						<span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">groups</span>
						${employees.length} employee${employees.length !== 1 ? "s" : ""} boarding
					</div>
					<div class="mfst-depart-check-badge">
						<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle">fact_check</span>
						Tap name to check in
					</div>
				</div>
				<div class="mfst-stop-employees">${employees.map(n => empChipHtml(n, null, true)).join("")}</div>
			</div>`;
		}

		return `
			<div class="mfst-stop-card depart">
				<div class="mfst-stop-card-header">
					<div class="mfst-stop-card-left">
						<span class="mfst-stop-tag tag-depart">
							<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle">play_arrow</span>
							DEPART
						</span>
					</div>
					<div class="mfst-stop-card-time">
						<span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">schedule</span>
						${fmtTime(time)}
					</div>
				</div>
				<div class="mfst-stop-card-title">${accommodation}</div>
				${empHtml}
			</div>
		`;
	}

	function renderReturnCard(time, accommodation, employees) {
		let empHtml = "";
		if (employees.length > 0) {
			empHtml = `<div class="mfst-stop-emp-section">
				<div class="mfst-stop-emp-label" style="color:var(--mfst-text-muted)">
					<span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">directions_bus</span>
					Returning ${employees.length} employee${employees.length !== 1 ? "s" : ""}
				</div>
				<div class="mfst-stop-employees">${employees.map(n => empChipHtml(n)).join("")}</div>
			</div>`;
		}

		return `
			<div class="mfst-stop-card return-card">
				<div class="mfst-stop-card-header">
					<div class="mfst-stop-card-left">
						<span class="mfst-stop-tag tag-return">
							<span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle">keyboard_return</span>
							RETURN
						</span>
					</div>
					<div class="mfst-stop-card-time">
						<span class="material-symbols-outlined" style="font-size:16px;vertical-align:middle">schedule</span>
						${fmtTime(time)}
					</div>
				</div>
				<div class="mfst-stop-card-title">Return to ${accommodation}</div>
				${empHtml}
			</div>
		`;
	}

	function renderTransit(t) {
		const d = fmtDuration(t.travelDuration);
		if (!d) return "";
		return `
			<div class="mfst-transit">
				<div class="mfst-transit-line"></div>
				<span class="material-symbols-outlined mfst-transit-icon">arrow_downward</span>
				<span class="mfst-transit-label">${d} drive</span>
				<div class="mfst-transit-line"></div>
			</div>
		`;
	}

	function renderSkipped(skipped) {
		let html = `<div style="padding:20px 0"><div class="mfst-vehicle-card" style="border-color:var(--mfst-red);background:var(--mfst-red-dim)"><div class="mfst-vehicle-name" style="color:var(--mfst-red)"><span class="material-symbols-outlined" style="font-size:28px;vertical-align:middle;margin-right:8px">warning</span>Skipped Shipments (${skipped.length})</div></div>`;
		skipped.forEach(s => {
			const reasons = escHtml((s.reasons ?? []).map(r => r.code ?? r.exampleVehicleIndex ?? JSON.stringify(r)).join(", "));
			html += `
				<div class="mfst-stop-card" style="border-left-color:var(--mfst-red)">
					<div class="mfst-stop-card-title">${escHtml(s.label ?? "Unlabelled shipment")}</div>
					<div class="mfst-stop-card-shift">${reasons || "No reason provided"}</div>
				</div>
			`;
		});
		html += `</div>`;
		$container.find("#mfst-main").html(html);
	}

	// ── CHECK-IN MODAL LOGIC ──
	let currentCheckInEmpId = null;
	let currentCheckInEmpName = null;
	let tempAttendance = null;
	let tempQoa = null;
	let tempQoaFailReason = null;

	window._mfst_openCheckInModal = function(empId, empName) {
		currentCheckInEmpId = empId;
		currentCheckInEmpName = empName;

		const state = window.checkerState[empId] || {};
		tempAttendance = state.attendance || null;
		tempQoa = state.qoa || null;
		tempQoaFailReason = state.qoa_fail_reason || null;

		// Pre-fill the reason dropdown with any previously saved value
		$container.find("#mfst-qoaFailReasonSelect").val(tempQoaFailReason || "");
		$container.find("#mfst-qoaReasonError").hide();

		$container.find("#mfst-checkinEmpName").text(empName);
		updateCheckInUI();
		$container.find("#mfst-checkinModal").addClass("active");
	};

	function closeCheckInModal(force) {
		// If QOA = Fail and no reason selected, block dismiss unless forced
		if (!force && tempAttendance === "Present" && tempQoa === "Fail" && !tempQoaFailReason) {
			$container.find("#mfst-qoaReasonError").show();
			$container.find("#mfst-qoaReasonSection").css("animation", "none");
			requestAnimationFrame(() => {
				$container.find("#mfst-qoaReasonSection").css("animation", "mfst-shake 0.35s ease");
			});
			return;
		}
		// Reset transient state
		tempQoaFailReason = null;
		$container.find("#mfst-qoaFailReasonSelect").val("");
		$container.find("#mfst-qoaReasonError").hide();
		$container.find("#mfst-checkinModal").removeClass("active");
	}

	$container.on("click", "#mfst-btn-close-checkin", function() { closeCheckInModal(); });

	$container.on("click", "#mfst-btn-present", function() {
		tempAttendance = "Present";
		updateCheckInUI();
		autoSaveCheckIn();
	});
	$container.on("click", "#mfst-btn-absent", function() {
		tempAttendance = "Absent";
		tempQoa = null;
		updateCheckInUI();
		autoSaveCheckIn();
	});
	$container.on("click", "#mfst-btn-pass", function() {
		if (tempAttendance === "Absent") return;
		tempQoa = "Pass";
		updateCheckInUI();
		autoSaveCheckIn();
	});
	$container.on("click", "#mfst-btn-fail", function() {
		if (tempAttendance === "Absent") return;
		tempQoa = "Fail";
		updateCheckInUI();
		autoSaveCheckIn();
	});

	// Live update of QOA failure reason
	$container.on("change", "#mfst-qoaFailReasonSelect", function() {
		tempQoaFailReason = $(this).val() || null;
		if (tempQoaFailReason) {
			$container.find("#mfst-qoaReasonError").hide();
		}
	});

	// Save & Continue button inside the QOA reason section
	$container.on("click", "#mfst-btn-qoa-save", function() {
		autoSaveCheckIn();
	});

	function updateCheckInUI() {
		$container.find("#mfst-btn-present").attr("class", "mfst-toggle-btn" + (tempAttendance === "Present" ? " active-present" : ""));
		$container.find("#mfst-btn-absent").attr("class", "mfst-toggle-btn" + (tempAttendance === "Absent" ? " active-absent" : ""));
		const qoaDisabled = (tempAttendance === "Absent");
		$container.find("#mfst-btn-pass").attr("class", "mfst-toggle-btn" + (tempQoa === "Pass" ? " active-pass" : ""));
		$container.find("#mfst-btn-fail").attr("class", "mfst-toggle-btn" + (tempQoa === "Fail" ? " active-fail" : ""));
		$container.find("#mfst-btn-pass").css("opacity", qoaDisabled ? "0.4" : "1");
		$container.find("#mfst-btn-fail").css("opacity", qoaDisabled ? "0.4" : "1");

		// Show/hide the QOA Failure Reason section
		const showReason = (tempAttendance === "Present" && tempQoa === "Fail");
		if (showReason) {
			$container.find("#mfst-qoaReasonSection").show();
		} else {
			$container.find("#mfst-qoaReasonSection").hide();
			$container.find("#mfst-qoaReasonError").hide();
			// Clear reason when hidden so stale value can't carry over
			if (!showReason) {
				tempQoaFailReason = null;
				$container.find("#mfst-qoaFailReasonSelect").val("");
			}
		}
	}

	function autoSaveCheckIn() {
		const empId = currentCheckInEmpId;
		const empName = currentCheckInEmpName;
		const att = tempAttendance;
		const qoa = tempQoa;

		// If QOA = Fail, the dispatcher MUST select a reason before proceeding
		if (att === "Present" && qoa === "Fail" && !tempQoaFailReason) {
			$container.find("#mfst-qoaReasonError").show();
			$container.find("#mfst-qoaReasonSection").css("animation", "none");
			requestAnimationFrame(() => {
				$container.find("#mfst-qoaReasonSection").css("animation", "mfst-shake 0.35s ease");
			});
			return;
		}

		window.checkerState[empId] = window.checkerState[empId] || {};
		window.checkerState[empId].attendance = att;
		window.checkerState[empId].qoa = qoa;
		window.checkerState[empId].qoa_fail_reason = (att === "Present" && qoa === "Fail") ? tempQoaFailReason : null;

		if (activeView) {
			renderRoute(activeView);
		}

		if (att === "Absent") {
			setTimeout(() => {
				closeCheckInModal(true);
			}, 150);
		} else if (att === "Present" && qoa === "Fail") {
			setTimeout(() => {
				closeCheckInModal(true);
				openRamboPrompt(empId, empName, "qoa_fail");
			}, 150);
		} else if (att === "Present" && qoa === "Pass") {
			setTimeout(() => {
				closeCheckInModal(true);
			}, 150);
		}
	}

	// ── RAMBO PROMPT MODAL LOGIC ──
	let ramboPromptEmpId = null;
	let ramboPromptEmpName = null;

	function openRamboPrompt(empId, empName, reason) {
		ramboPromptEmpId = empId;
		ramboPromptEmpName = empName;
		$container.find("#mfst-ramboPromptEmpName").text(empName);
		if (reason === "qoa_fail") {
			$container.find("#mfst-ramboPromptTitle").text("Quality of Appearance Failed");
			$container.find("#mfst-ramboPromptReason").text(" failed the Quality of Appearance check.");
		} else {
			$container.find("#mfst-ramboPromptTitle").text("Employee Absent");
			$container.find("#mfst-ramboPromptReason").text(" is marked as Absent.");
		}
		$container.find("#mfst-ramboPromptModal").addClass("active");
	}

	function closeRamboPrompt() {
		$container.find("#mfst-ramboPromptModal").removeClass("active");
	}

	$container.on("click", "#mfst-btn-rambo-yes", function() {
		closeRamboPrompt();
		openReplacementModal(ramboPromptEmpId, ramboPromptEmpName);
	});

	$container.on("click", "#mfst-btn-rambo-no", function() {
		closeRamboPrompt();
		if (activeView) renderRoute(activeView);
	});

	$container.on("click", "#mfst-btn-close-rambo", closeRamboPrompt);

	// ── REPLACEMENT MODAL LOGIC ──
	let availableRelievers = [];

	function formatRelieverOption(r) {
		if (r.shift_name && r.shift_start_time && r.shift_end_time) {
			return r.employee_name + " - " + r.shift_name + " - " + r.shift_start_time + " to " + r.shift_end_time;
		}
		if (r.designation) {
			return r.employee_name + " (" + r.designation + ")";
		}
		return r.employee_name;
	}

	function populateRelieverSelect(relievers) {
		const sel = $container.find("#mfst-relieverSelect")[0];
		sel.innerHTML = "";

		if (relievers.length === 0) {
			const opt = document.createElement("option");
			opt.value = "";
			opt.textContent = "No available Rambo Relievers found for this time slot.";
			sel.appendChild(opt);
			sel.disabled = true;
			$container.find("#mfst-btn-confirm-replace").prop("disabled", true);
			return;
		}

		sel.disabled = false;
		const placeholder = document.createElement("option");
		placeholder.value = "";
		placeholder.textContent = "-- Select Reliever --";
		sel.appendChild(placeholder);

		for (const r of relievers) {
			const opt = document.createElement("option");
			opt.value = r.name;
			opt.textContent = formatRelieverOption(r);
			sel.appendChild(opt);
		}
		$container.find("#mfst-btn-confirm-replace").prop("disabled", false);
	}

	function findShiftForEmp(empId) {
		// Walk all shipment labels to find which shift/site this employee belongs to
		for (const [label, emps] of Object.entries(shipmentEmployees)) {
			const found = (emps || []).some(e => {
				const eid = (typeof e === "object" && e !== null) ? (e.id || e.name || "") : (e || "");
				return eid === empId;
			});
			if (found) {
				return {
					shift: shipmentShiftNames[label] || "",
					site: shipmentSiteLocations[label] || ""
				};
			}
		}
		return { shift: "", site: "" };
	}

	function openReplacementModal(empId, empName) {
		$container.find("#mfst-replaceOrigName").text(empName);
		const sel = $container.find("#mfst-relieverSelect")[0];
		sel.innerHTML = "";
		const loadingOpt = document.createElement("option");
		loadingOpt.value = "";
		loadingOpt.textContent = "Loading available relievers...";
		sel.appendChild(loadingOpt);
		$container.find("#mfst-btn-confirm-replace").prop("disabled", true).text("Confirm Replacement");
		$container.find("#mfst-replacementModal").addClass("active");

		// Resolve shift/site for this employee
		const empShiftInfo = findShiftForEmp(empId);
		// Store for use in confirm handler
		window._mfst_currentReplacementShift = empShiftInfo.shift;
		window._mfst_currentReplacementSite = empShiftInfo.site;

		const routes = ROUTE_DATA.response?.routes || [];
		const firstTime = routes[0]?.vehicleStartTime;
		let date = new Date().toISOString().split("T")[0];
		if (firstTime) {
			date = new Date(firstTime).toLocaleDateString("en-CA", { timeZone: "Asia/Kuwait" });
		}

		frappe.call({
			method: "one_fm.one_fm.page.transportation_schedule.transportation_schedule.get_available_rambo_relievers",
			args: { shift_name: empShiftInfo.shift, date: date },
			async: true,
			callback: function(r) {
				availableRelievers = r.message || [];
				populateRelieverSelect(availableRelievers);
			},
			error: function() {
				const errSel = $container.find("#mfst-relieverSelect")[0];
				errSel.innerHTML = "";
				const errOpt = document.createElement("option");
				errOpt.value = "";
				errOpt.textContent = "Error loading relievers.";
				errSel.appendChild(errOpt);
			}
		});
	}

	function closeReplacementModal() {
		$container.find("#mfst-replacementModal").removeClass("active");
		if (activeView) renderRoute(activeView);
	}

	$container.on("click", "#mfst-btn-close-replacement", closeReplacementModal);

	$container.on("click", "#mfst-btn-confirm-replace", function() {
		const selVal = $container.find("#mfst-relieverSelect").val();
		if (!selVal) return;

		const reliever = availableRelievers.find(r => r.name === selVal);
		if (!reliever) return;

		window.checkerState[currentCheckInEmpId] = window.checkerState[currentCheckInEmpId] || {};
		window.checkerState[currentCheckInEmpId].replacement = {
			id: reliever.name,
			name: reliever.employee_name,
			mobile: reliever.mobile
		};

		$container.find("#mfst-btn-confirm-replace").text("Processing...").prop("disabled", true);

		frappe.call({
			method: "one_fm.one_fm.page.transportation_schedule.transportation_schedule.process_rambo_replacement",
			args: {
				original_employee: currentCheckInEmpId,
				replacement_employee: reliever.name,
				shift_name: window._mfst_currentReplacementShift || "",
				site: window._mfst_currentReplacementSite || ""
			},
			async: true,
			callback: function(r) {
				$container.find("#mfst-btn-confirm-replace").text("Confirm Replacement");
				const msg = (r.message && r.message.message) ? r.message.message : "Replacement processed.";
				showToast(msg);
				closeReplacementModal();
			},
			error: function() {
				$container.find("#mfst-btn-confirm-replace").text("Confirm Replacement");
				showToast("Replacement saved, but server request failed.");
				closeReplacementModal();
			}
		});
	});
}


// ════════════════════════════════════════════════════════════════════════════
//  HTML SKELETON — Driver-Friendly Layout
// ════════════════════════════════════════════════════════════════════════════

function getManifestHTML() {
	return `
		<link rel="preconnect" href="https://fonts.googleapis.com">
		<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
		<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">

		<div class="mfst-wrapper">
			<!-- HEADER -->
			<div class="mfst-header">
				<div class="mfst-header-top">
					<div class="mfst-header-brand">
						<span class="material-symbols-outlined" style="font-size:24px">directions_bus</span>
						<span>Transportation Manifest</span>
					</div>
					<div class="mfst-header-actions">
						<button class="mfst-icon-btn" id="mfst-btn-help" title="Help">
							<span class="material-symbols-outlined">help_outline</span>
						</button>
						<button class="mfst-icon-btn" id="mfst-btn-print" title="Print">
							<span class="material-symbols-outlined">print</span>
						</button>
					</div>
				</div>
				<div class="mfst-header-info">
					<span class="material-symbols-outlined" style="font-size:16px;opacity:0.7">calendar_today</span>
					<span id="mfst-run-date">—</span>
					<span id="mfst-plan-title" style="opacity:0.7"></span>
				</div>
			</div>

			<!-- HELP PANEL -->
			<div class="mfst-help-panel" id="mfst-helpPanel">
				<div class="mfst-help-inner">
					<div class="mfst-help-title">
						<span class="material-symbols-outlined" style="font-size:20px;color:#f97316">lightbulb</span>
						Quick Guide
						<button class="mfst-help-close" id="mfst-btn-close-help"><span class="material-symbols-outlined" style="font-size:18px">close</span></button>
					</div>
					<div class="mfst-help-steps">
						<div class="mfst-help-step">
							<span class="mfst-help-num">1</span>
							<span><strong>Select a vehicle</strong> from the tabs above to see its route.</span>
						</div>
						<div class="mfst-help-step">
							<span class="mfst-help-num">2</span>
							<span><strong>Tap an employee name</strong> at the DEPART card to mark attendance.</span>
						</div>
						<div class="mfst-help-step">
							<span class="mfst-help-num">3</span>
							<span><strong>Tap the phone icon</strong> next to any name to call them.</span>
						</div>
						<div class="mfst-help-step">
							<span class="mfst-help-num">4</span>
							<span><strong>Bookmark this page</strong> — the URL is permanent.</span>
						</div>
					</div>
				</div>
			</div>

			<!-- VEHICLE TAB BAR -->
			<div class="mfst-tab-bar-wrapper">
				<div class="mfst-tab-bar" id="mfst-tab-bar"></div>
			</div>

			<!-- MAIN CONTENT -->
			<main class="mfst-main" id="mfst-main"></main>

			<!-- CHECK-IN MODAL -->
			<div class="mfst-modal-overlay" id="mfst-checkinModal">
				<div class="mfst-modal-content">
					<div class="mfst-modal-header">
						<div>
							<div class="mfst-modal-subtitle">Employee Check-In</div>
							<span id="mfst-checkinEmpName">Employee Name</span>
						</div>
						<button class="mfst-modal-close" id="mfst-btn-close-checkin"><span class="material-symbols-outlined">close</span></button>
					</div>
					<div class="mfst-checker-section">
						<div class="mfst-checker-label">
							<span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle;margin-right:4px">how_to_reg</span>
							Step 1: Is the employee here?
						</div>
						<div class="mfst-toggle-group">
							<button class="mfst-toggle-btn" id="mfst-btn-present">
								<span class="material-symbols-outlined" style="font-size:20px;vertical-align:middle;margin-right:6px">check_circle</span>
								Present
							</button>
							<button class="mfst-toggle-btn" id="mfst-btn-absent">
								<span class="material-symbols-outlined" style="font-size:20px;vertical-align:middle;margin-right:6px">cancel</span>
								Absent
							</button>
						</div>
					</div>
					<div class="mfst-checker-section">
						<div class="mfst-checker-label">
							<span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle;margin-right:4px">checkroom</span>
							Step 2: Is their appearance in order?
						</div>
						<div class="mfst-toggle-group" style="margin-bottom:0;">
							<button class="mfst-toggle-btn" id="mfst-btn-pass">
								<span class="material-symbols-outlined" style="font-size:20px;vertical-align:middle;margin-right:6px">thumb_up</span>
								Pass
							</button>
							<button class="mfst-toggle-btn" id="mfst-btn-fail">
								<span class="material-symbols-outlined" style="font-size:20px;vertical-align:middle;margin-right:6px">thumb_down</span>
								Fail
							</button>
						</div>
					</div>

					<!-- QOA FAILURE REASON — Step 3, only visible when QOA = Fail -->
					<div class="mfst-checker-section mfst-qoa-reason-section" id="mfst-qoaReasonSection" style="display:none;">
						<div class="mfst-checker-label">
							<span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle;margin-right:4px;color:#dc2626">report_problem</span>
							Step 3: Select the reason for failure
						</div>
						<select id="mfst-qoaFailReasonSelect" class="mfst-reliever-select mfst-qoa-reason-select">
							<option value="">-- Select Reason --</option>
							<option value="Grooming">Grooming</option>
							<option value="Uniform">Uniform</option>
						</select>
						<div class="mfst-qoa-reason-error" id="mfst-qoaReasonError" style="display:none;">
							<span class="material-symbols-outlined" style="font-size:15px;vertical-align:middle;margin-right:4px">error</span>
							Please select a QOA Failure Reason before continuing.
						</div>
						<button class="mfst-qoa-save-btn" id="mfst-btn-qoa-save">
							<span class="material-symbols-outlined" style="font-size:18px">check_circle</span>
							Save &amp; Continue
						</button>
					</div>
				</div>
			</div>

			<!-- RAMBO PROMPT MODAL -->
			<div class="mfst-modal-overlay" id="mfst-ramboPromptModal">
				<div class="mfst-modal-content">
					<div class="mfst-modal-header">
						<div>
							<div class="mfst-modal-subtitle">Replacement Needed?</div>
							<span id="mfst-ramboPromptTitle">Employee Absent</span>
						</div>
						<button class="mfst-modal-close" id="mfst-btn-close-rambo"><span class="material-symbols-outlined">close</span></button>
					</div>
					<div style="margin-bottom:16px; font-size:15px; color:var(--mfst-text-muted); line-height:1.6">
						<strong id="mfst-ramboPromptEmpName" style="color:var(--mfst-text)"></strong>
						<span id="mfst-ramboPromptReason"></span>
					</div>
					<div style="font-size:16px; font-weight:600; color:var(--mfst-text); margin-bottom:20px;">
						<span class="material-symbols-outlined" style="font-size:22px;vertical-align:middle;margin-right:6px;color:var(--mfst-accent)">person_search</span>
						Do you want to look for a Rambo Reliever?
					</div>
					<div style="display:flex; gap:10px;">
						<button class="mfst-rambo-btn mfst-rambo-btn-no" id="mfst-btn-rambo-no">
							<span class="material-symbols-outlined" style="font-size:20px">close</span>
							No, Skip
						</button>
						<button class="mfst-rambo-btn mfst-rambo-btn-yes" id="mfst-btn-rambo-yes">
							<span class="material-symbols-outlined" style="font-size:20px">person_search</span>
							Yes, Find Reliever
						</button>
					</div>
				</div>
			</div>

			<!-- REPLACEMENT MODAL -->
			<div class="mfst-modal-overlay" id="mfst-replacementModal">
				<div class="mfst-modal-content">
					<div class="mfst-modal-header">
						<div>
							<div class="mfst-modal-subtitle">Rambo Reliever</div>
							<span>Assign Replacement</span>
						</div>
						<button class="mfst-modal-close" id="mfst-btn-close-replacement"><span class="material-symbols-outlined">close</span></button>
					</div>
					<div style="margin-bottom:16px; font-size:15px; color:var(--mfst-text-muted)">
						<span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle;margin-right:4px;color:var(--mfst-red)">swap_horiz</span>
						Replacing: <strong id="mfst-replaceOrigName" style="color:var(--mfst-text)"></strong>
					</div>
					<div class="mfst-checker-label">
						<span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle;margin-right:4px">group</span>
						Select Available Reliever
					</div>
					<select id="mfst-relieverSelect" class="mfst-reliever-select">
						<option value="">Loading...</option>
					</select>
					<button class="mfst-rambo-btn mfst-rambo-btn-yes" id="mfst-btn-confirm-replace" style="width:100%;margin-top:14px;justify-content:center">
						<span class="material-symbols-outlined" style="font-size:20px">check_circle</span>
						Confirm Replacement
					</button>
				</div>
			</div>
		</div>
	`;
}


// ════════════════════════════════════════════════════════════════════════════
//  CSS — Driver-Friendly, Mobile-First Design
// ════════════════════════════════════════════════════════════════════════════

function getManifestCSS() {
	return `
		@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

		.mfst-wrapper {
			--mfst-accent: #f97316;
			--mfst-accent-dim: rgba(249, 115, 22, 0.12);
			--mfst-green: #16a34a;
			--mfst-green-dim: rgba(22, 163, 74, 0.10);
			--mfst-red: #dc2626;
			--mfst-red-dim: rgba(220, 38, 38, 0.08);
			--mfst-blue: #2563eb;
			--mfst-blue-dim: rgba(37, 99, 235, 0.08);
			--mfst-purple: #c2410c;
			--mfst-purple-dim: rgba(194, 65, 12, 0.06);
			--mfst-text: #111827;
			--mfst-text-muted: #6b7280;
			--mfst-text-dim: #9ca3af;
			--mfst-bg: #f3f4f6;
			--mfst-bg-card: #ffffff;
			--mfst-bg-raised: #f9fafb;
			--mfst-border: #e5e7eb;
			--mfst-font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

			background: var(--mfst-bg);
			color: var(--mfst-text);
			font-family: var(--mfst-font-body);
			font-size: 15px;
			min-height: 100vh;
			-webkit-font-smoothing: antialiased;
		}

		.mfst-wrapper .page-head { display: none; }

		/* ── HEADER ── */
		.mfst-header { background: linear-gradient(135deg, #ea580c 0%, #f97316 100%); color: #fff; padding: 14px 20px 12px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
		.mfst-header-top { display: flex; align-items: center; justify-content: space-between; }
		.mfst-header-brand { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; letter-spacing: -0.01em; }
		.mfst-header-actions { display: flex; gap: 6px; }
		.mfst-icon-btn { background: rgba(255,255,255,0.15); border: none; border-radius: 10px; padding: 8px; cursor: pointer; color: #fff; display: flex; align-items: center; justify-content: center; transition: background 0.15s; }
		.mfst-icon-btn:hover { background: rgba(255,255,255,0.25); }
		.mfst-icon-btn .material-symbols-outlined { font-size: 22px; }
		.mfst-header-info { display: flex; align-items: center; gap: 8px; margin-top: 6px; font-size: 13px; opacity: 0.9; font-weight: 500; }

		/* ── HELP PANEL ── */
		.mfst-help-panel { max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; background: #fffbeb; border-bottom: 2px solid #fbbf24; }
		.mfst-help-panel.active { max-height: 350px; }
		.mfst-help-inner { padding: 16px 20px; }
		.mfst-help-title { font-size: 15px; font-weight: 700; color: #92400e; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
		.mfst-help-close { background: none; border: none; cursor: pointer; color: #92400e; margin-left: auto; padding: 4px; border-radius: 6px; display: flex; }
		.mfst-help-close:hover { background: rgba(146, 64, 14, 0.1); }
		.mfst-help-steps { display: flex; flex-direction: column; gap: 8px; }
		.mfst-help-step { display: flex; align-items: flex-start; gap: 10px; font-size: 14px; color: #78350f; line-height: 1.5; }
		.mfst-help-num { flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%; background: #f97316; color: #fff; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; }

		/* ── VEHICLE TAB BAR ── */
		.mfst-tab-bar-wrapper { background: var(--mfst-bg-card); border-bottom: 1px solid var(--mfst-border); position: sticky; top: 62px; z-index: 99; }
		.mfst-tab-bar { display: flex; overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; padding: 0 8px; gap: 4px; }
		.mfst-tab-bar::-webkit-scrollbar { display: none; }
		.mfst-tab { display: flex; flex-direction: column; align-items: flex-start; padding: 12px 16px; border: none; background: none; cursor: pointer; border-bottom: 3px solid transparent; min-width: 140px; flex-shrink: 0; transition: all 0.15s; text-align: left; }
		.mfst-tab:hover { background: var(--mfst-bg); }
		.mfst-tab.active { border-bottom-color: var(--mfst-accent); background: var(--mfst-accent-dim); }
		.mfst-tab-name { font-family: var(--mfst-font-body); font-size: 14px; font-weight: 700; color: var(--mfst-text); white-space: nowrap; }
		.mfst-tab.active .mfst-tab-name { color: var(--mfst-accent); }
		.mfst-tab-plate { font-size: 11px; font-weight: 600; color: var(--mfst-text-muted); margin-top: 1px; }
		.mfst-tab-time { font-size: 11px; color: var(--mfst-text-dim); margin-top: 2px; white-space: nowrap; }

		/* ── MAIN ── */
		.mfst-main { padding: 16px 16px 80px; max-width: 800px; margin: 0 auto; }

		/* ── VEHICLE INFO CARD ── */
		.mfst-vehicle-card { background: var(--mfst-bg-card); border: 1px solid var(--mfst-border); border-radius: 16px; padding: 18px 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
		.mfst-vehicle-card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
		.mfst-vehicle-name { font-size: 22px; font-weight: 800; color: var(--mfst-text); display: flex; align-items: center; letter-spacing: -0.02em; }
		.mfst-vehicle-plate { font-size: 14px; font-weight: 700; color: var(--mfst-accent); background: var(--mfst-accent-dim); padding: 4px 12px; border-radius: 8px; margin-top: 6px; display: inline-block; letter-spacing: 0.05em; }
		.mfst-vehicle-card-right { text-align: right; }
		.mfst-vehicle-time-badge { font-size: 15px; font-weight: 700; color: var(--mfst-text); display: flex; align-items: center; gap: 6px; }
		.mfst-vehicle-trips { font-size: 13px; color: var(--mfst-text-muted); margin-top: 4px; }
		.mfst-vehicle-stats { display: flex; gap: 16px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--mfst-border); }
		.mfst-stat-box { text-align: center; min-width: 80px; }
		.mfst-stat-val { font-size: 18px; font-weight: 700; color: var(--mfst-text); }
		.mfst-stat-lbl { font-size: 11px; font-weight: 600; color: var(--mfst-text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }
		.mfst-vehicle-card-details { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--mfst-border); font-size: 14px; color: var(--mfst-text-muted); display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
		.mfst-info-icon { font-size: 16px; vertical-align: middle; }

		/* ── TRIP GROUP ── */
		.mfst-trip-group { border: 2px solid var(--mfst-blue); border-radius: 16px; margin-bottom: 16px; overflow: hidden; background: var(--mfst-bg-card); }
		.mfst-trip-group.return { border-color: var(--mfst-purple); }
		.mfst-trip-header { display: flex; align-items: center; gap: 10px; padding: 14px 20px; background: var(--mfst-blue-dim); border-bottom: 1px solid rgba(37,99,235,0.1); flex-wrap: wrap; }
		.mfst-trip-group.return .mfst-trip-header { background: var(--mfst-purple-dim); border-bottom-color: rgba(194,65,12,0.1); }
		.mfst-trip-header-icon { font-size: 20px; color: var(--mfst-blue); }
		.mfst-trip-group.return .mfst-trip-header-icon { color: var(--mfst-purple); }
		.mfst-trip-header-title { font-size: 16px; font-weight: 700; color: var(--mfst-blue); }
		.mfst-trip-group.return .mfst-trip-header-title { color: var(--mfst-purple); }
		.mfst-trip-header-meta { font-size: 12px; color: var(--mfst-text-dim); margin-left: auto; }
		.mfst-trip-body { padding: 12px 16px 16px; }

		/* ── STOP CARDS ── */
		.mfst-stop-card { background: var(--mfst-bg-card); border: 1px solid var(--mfst-border); border-left: 4px solid var(--mfst-border); border-radius: 12px; padding: 16px 18px; margin-bottom: 8px; transition: box-shadow 0.15s; }
		.mfst-stop-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
		.mfst-stop-card.pickup { border-left-color: var(--mfst-green); }
		.mfst-stop-card.dropoff { border-left-color: var(--mfst-accent); }
		.mfst-stop-card.depart { border-left-color: var(--mfst-green); background: linear-gradient(135deg, rgba(22,163,74,0.04) 0%, var(--mfst-bg-card) 100%); }
		.mfst-stop-card.return-card { border-left-color: var(--mfst-text-dim); background: var(--mfst-bg-raised); }

		.mfst-stop-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; gap: 8px; flex-wrap: wrap; }
		.mfst-stop-card-left { display: flex; gap: 6px; flex-wrap: wrap; }
		.mfst-stop-card-time { font-size: 16px; font-weight: 700; color: var(--mfst-text); display: flex; align-items: center; gap: 4px; white-space: nowrap; }
		.mfst-stop-card-title { font-size: 18px; font-weight: 700; color: var(--mfst-text); line-height: 1.3; }
		.mfst-stop-card-shift { font-size: 13px; color: var(--mfst-text-muted); margin-top: 2px; }

		/* Stop tags */
		.mfst-stop-tag { font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 4px 10px; border-radius: 6px; display: inline-flex; align-items: center; gap: 4px; }
		.tag-pickup { background: var(--mfst-green-dim); color: var(--mfst-green); }
		.tag-dropoff { background: var(--mfst-accent-dim); color: var(--mfst-accent); }
		.tag-depart { background: var(--mfst-green-dim); color: var(--mfst-green); }
		.tag-return { background: var(--mfst-bg); color: var(--mfst-text-dim); }
		.tag-stop { background: var(--mfst-bg); color: var(--mfst-text-dim); }

		/* Employee section in stop cards */
		.mfst-stop-emp-section { margin-top: 12px; }
		.mfst-stop-emp-label { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
		.mfst-depart-emp-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
		.mfst-depart-check-badge { font-size: 12px; font-weight: 600; color: var(--mfst-accent); background: var(--mfst-accent-dim); border: 1px solid rgba(249,115,22,0.2); padding: 4px 10px; border-radius: 6px; display: flex; align-items: center; gap: 4px; }

		/* ── EMPLOYEE CHIPS — Large & Tappable ── */
		.mfst-stop-employees { display: flex; flex-wrap: wrap; gap: 6px; }
		.mfst-emp-chip { font-family: var(--mfst-font-body); font-size: 14px; font-weight: 500; color: var(--mfst-text); background: var(--mfst-bg-raised); border: 1px solid var(--mfst-border); border-radius: 10px; padding: 10px 14px; min-height: 44px; display: inline-flex; align-items: center; gap: 8px; transition: all 0.15s; box-sizing: border-box; }
		.mfst-chip-name { flex: 1; }
		.mfst-chip-status-icon { font-size: 16px; }
		.mfst-emp-call-btn { color: var(--mfst-green); cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; transition: color 0.15s; padding: 2px; border-radius: 6px; }
		.mfst-emp-call-btn .material-symbols-outlined { font-size: 18px; }
		.mfst-emp-call-btn:hover { color: #15803d; background: var(--mfst-green-dim); }
		.mfst-emp-call-disabled { color: var(--mfst-text-dim) !important; opacity: 0.35; cursor: default; }
		.mfst-emp-chip.mfst-interactive { cursor: pointer; }
		.mfst-emp-chip.mfst-interactive:hover { border-color: var(--mfst-accent); background: var(--mfst-accent-dim); }
		.mfst-emp-chip.mfst-interactive:active { transform: scale(0.97); }
		.mfst-emp-chip.mfst-state-success { background: var(--mfst-green-dim); border-color: var(--mfst-green); }
		.mfst-emp-chip.mfst-state-success .mfst-chip-status-icon { color: var(--mfst-green); }
		.mfst-emp-chip.mfst-state-warning { background: rgba(245,158,11,0.10); border-color: #f59e0b; }
		.mfst-emp-chip.mfst-state-warning .mfst-chip-status-icon { color: #d97706; }
		.mfst-emp-chip.mfst-state-error { background: var(--mfst-red-dim); border-color: var(--mfst-red); text-decoration: line-through; }
		.mfst-emp-chip.mfst-state-error .mfst-chip-status-icon { color: var(--mfst-red); }
		.mfst-emp-chip.mfst-state-replacement { background: var(--mfst-blue-dim); border-color: var(--mfst-blue); }
		.mfst-emp-chip.mfst-state-replacement .mfst-chip-status-icon { color: var(--mfst-blue); }

		/* ── TRANSIT ── */
		.mfst-transit { display: flex; align-items: center; gap: 8px; padding: 6px 0; color: var(--mfst-text-dim); }
		.mfst-transit-line { flex: 1; height: 1px; background: var(--mfst-border); }
		.mfst-transit-icon { font-size: 16px; }
		.mfst-transit-label { font-size: 16px; font-weight: 700; white-space: nowrap; background: rgba(245,158,11,0.10); border: 1px solid rgba(245,158,11,0.25); padding: 3px 12px; border-radius: 100px; color: var(--mfst-text); }

		/* ── MODALS ── */
		.mfst-modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; opacity: 0; pointer-events: none; transition: opacity 0.2s; }
		.mfst-modal-overlay.active { opacity: 1; pointer-events: auto; }
		.mfst-modal-content { background: var(--mfst-bg-card); border-radius: 20px; width: 95%; max-width: 420px; padding: 24px; box-shadow: 0 25px 50px rgba(0,0,0,0.25); transform: scale(0.95); transition: transform 0.2s; }
		.mfst-modal-overlay.active .mfst-modal-content { transform: scale(1); }
		.mfst-modal-header { font-size: 20px; font-weight: 700; margin-bottom: 20px; color: var(--mfst-text); display: flex; justify-content: space-between; align-items: flex-start; }
		.mfst-modal-close { background: var(--mfst-bg); border: none; cursor: pointer; color: var(--mfst-text-muted); border-radius: 10px; padding: 8px; display: flex; }
		.mfst-modal-close:hover { background: var(--mfst-border); }
		.mfst-modal-subtitle { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--mfst-accent); margin-bottom: 4px; }
		.mfst-checker-section { margin-bottom: 8px; }
		.mfst-checker-label { font-size: 14px; font-weight: 600; color: var(--mfst-text-muted); margin-bottom: 10px; display: flex; align-items: center; }
		.mfst-toggle-group { display: flex; gap: 10px; margin-bottom: 20px; }
		.mfst-toggle-btn { flex: 1; padding: 16px; border: 2px solid var(--mfst-border); border-radius: 14px; background: transparent; color: var(--mfst-text); font-family: var(--mfst-font-body); font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; min-height: 54px; }
		.mfst-toggle-btn:hover { background: var(--mfst-bg); }
		.mfst-toggle-btn:active { transform: scale(0.97); }
		.mfst-toggle-btn.active-present, .mfst-toggle-btn.active-pass { background: var(--mfst-green); border-color: var(--mfst-green); color: #fff; }
		.mfst-toggle-btn.active-absent, .mfst-toggle-btn.active-fail { background: var(--mfst-red); border-color: var(--mfst-red); color: #fff; }

		/* ── QOA FAILURE REASON ── */
		.mfst-qoa-reason-section { border-top: 1px solid var(--mfst-border); padding-top: 16px; margin-top: 4px; }
		.mfst-qoa-reason-select { border-color: #dc2626 !important; }
		.mfst-qoa-reason-select:focus { border-color: #dc2626 !important; box-shadow: 0 0 0 3px rgba(220,38,38,0.15) !important; }
		.mfst-qoa-reason-error { margin-top: 8px; font-size: 13px; font-weight: 600; color: #dc2626; display: flex; align-items: center; background: rgba(220,38,38,0.07); border: 1px solid rgba(220,38,38,0.25); border-radius: 8px; padding: 8px 12px; }
		.mfst-qoa-save-btn { margin-top: 14px; width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; padding: 15px 20px; border: none; border-radius: 14px; background: var(--mfst-accent); color: #fff; font-family: var(--mfst-font-body); font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.2s; min-height: 52px; }
		.mfst-qoa-save-btn:hover { background: #ea580c; }
		.mfst-qoa-save-btn:active { transform: scale(0.97); }
		@keyframes mfst-shake { 0%,100% { transform: translateX(0); } 20%,60% { transform: translateX(-5px); } 40%,80% { transform: translateX(5px); } }

		/* ── RAMBO BUTTONS ── */
		.mfst-rambo-btn { flex: 1; display: inline-flex; align-items: center; justify-content: center; padding: 14px 20px; border-radius: 14px; font-family: var(--mfst-font-body); font-size: 16px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; gap: 8px; min-height: 52px; }
		.mfst-rambo-btn-no { background: var(--mfst-bg); color: var(--mfst-text-muted); }
		.mfst-rambo-btn-no:hover { background: var(--mfst-border); }
		.mfst-rambo-btn-yes { background: var(--mfst-accent); color: #fff; }
		.mfst-rambo-btn-yes:hover { background: #ea580c; }
		.mfst-rambo-btn-yes:active { transform: scale(0.97); }
		.mfst-rambo-btn-yes:disabled { opacity: 0.5; cursor: not-allowed; }
		.mfst-reliever-select { width: 100%; padding: 14px 16px; border: 2px solid var(--mfst-border); border-radius: 12px; font-family: var(--mfst-font-body); font-size: 15px; color: var(--mfst-text); background: var(--mfst-bg-card); cursor: pointer; }
		.mfst-reliever-select:focus { outline: none; border-color: var(--mfst-accent); box-shadow: 0 0 0 3px var(--mfst-accent-dim); }

		/* ── EMPTY STATE ── */
		.mfst-empty-state { text-align: center; padding: 60px 20px; color: var(--mfst-text-muted); }
		.mfst-empty-state h2 { font-size: 22px; font-weight: 700; margin-bottom: 8px; color: var(--mfst-text); }
		.mfst-empty-state p { font-size: 15px; line-height: 1.6; }

		/* ── DESKTOP (>768px) ── */
		@media (min-width: 768px) {
			.mfst-main { padding: 24px 32px 80px; }
			.mfst-help-steps { flex-direction: row; flex-wrap: wrap; gap: 16px; }
			.mfst-help-step { flex: 1; min-width: 200px; }
			.mfst-tab { min-width: 160px; }
		}

		/* ── PRINT ── */
		@media print {
			.mfst-header, .mfst-tab-bar-wrapper, .mfst-help-panel { display: none; }
			.mfst-main { padding: 20px; }
			.mfst-wrapper { background: white; color: black; }
			.mfst-stop-card, .mfst-vehicle-card, .mfst-trip-group { border-color: #ccc; background: white; box-shadow: none; }
			.mfst-emp-chip { border-color: #ccc; background: white; }
		}
	`;
}
