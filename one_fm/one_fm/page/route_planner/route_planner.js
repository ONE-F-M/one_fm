/**
 * Route Planner — Frappe Page Loader
 *
 * Loads the Vite-bundled Vue app (from one_fm/public/dist/route_planner/)
 * and mounts it inside the Frappe Page wrapper.
 */
frappe.pages["route-planner"].on_page_load = function (wrapper) {
	// Skip make_app_page entirely — mount Vue app directly into the wrapper
	// to avoid Frappe's page-head, page-body padding, and layout constraints.

	// Hide the Frappe page-head (breadcrumbs + title bar)
	$(wrapper).find(".page-head").hide();

	// Create a full-height mount point
	const mountEl = document.createElement("div");
	mountEl.id = "route-planner-app";
	mountEl.style.height = "calc(100vh - var(--navbar-height, 60px))";
	mountEl.style.overflow = "hidden";
	wrapper.appendChild(mountEl);

	// Cache-busting: use Frappe's boot version or timestamp
	const v = (frappe.boot && frappe.boot.build_version) || Date.now();

	// Load bundled CSS
	const cssPath = `/assets/one_fm/dist/route_planner/style.css?v=${v}`;
	if (!document.querySelector(`link[href^="/assets/one_fm/dist/route_planner/style.css"]`)) {
		const link = document.createElement("link");
		link.rel = "stylesheet";
		link.href = cssPath;
		document.head.appendChild(link);
	}

	// Load bundled JS and mount
	const jsPath = `/assets/one_fm/dist/route_planner/index.js?v=${v}`;
	const script = document.createElement("script");
	script.src = jsPath;
	script.onload = function () {
		if (window.RoutePlanner && window.RoutePlanner.mount) {
			window.RoutePlanner.mount(mountEl);
		} else {
			console.error("RoutePlanner bundle loaded but mount function not found");
		}
	};
	script.onerror = function () {
		mountEl.innerHTML = `
			<div style="display:flex;align-items:center;justify-content:center;height:100%;flex-direction:column;gap:12px">
				<div style="font-size:16px;color:#666">Failed to load Route Planner</div>
				<div style="font-size:13px;color:#999">
					Run <code>cd apps/one_fm/route_planner && yarn build</code> to build the frontend
				</div>
			</div>
		`;
	};
	document.head.appendChild(script);
};