import frappe
from frappe import _
from frappe.query_builder.functions import Count

from helpdesk.api.dashboard import (
    HelpdeskDashboard,
    get_bar_chart_config,
    get_master_dashboard_data,
)
from helpdesk.utils import agent_only

# Fixed colors for the "Tickets by Status" chart. Any status not listed here
# falls back to gray.
STATUS_COLOR_GRAY = "#A6B1B9"
STATUS_COLORS = {
    "Pending Deployment": "#F8814F",  # Orange
    "On Hold": "#F8814F",  # Orange
    "Draft": STATUS_COLOR_GRAY,  # Gray
    "Closed": "#48BB74",  # Green
    "Resolved": "#48BB74",  # Green
    "Replied": "#318AD8",  # Blue
    "Open": "#F56B6B",  # Red
}


class OneFMHelpdeskDashboard(HelpdeskDashboard):
    """Extends the Helpdesk dashboard with a "Tickets by Status" trend chart.

    Kept in one_fm (instead of patching the vendored helpdesk app) so the
    customization survives helpdesk upgrades.
    """

    def get_trend_data(self):
        # Insert the status chart right after the ticket trend chart.
        return [
            self.get_ticket_trend_data(),
            self.get_ticket_status_data(),
            self.get_feedback_trend_data(),
        ]

    def get_ticket_status_data(self):
        base_cond = (self.ticket.creation > self.from_date) & (
            self.ticket.creation < self.to_date_next
        )
        if self.combined_cond:
            base_cond = base_cond & self.combined_cond

        query = (
            frappe.qb.from_(self.ticket)
            .select(
                self.ticket.status.as_("status"),
                Count(self.ticket.name).as_("count"),
            )
            .where(base_cond)
            .groupby(self.ticket.status)
            .orderby(Count(self.ticket.name), order=frappe.qb.desc)
        )

        result = query.run(as_dict=True)

        # Pivot into one series per status so each status bar gets its own color
        # and a matching legend entry (like the Ticket Trend chart). Each row
        # carries its count only for its own status column and 0 for the others
        # (not missing/undefined) so the axis tooltip's built-in zero-filter
        # hides the irrelevant statuses instead of showing "undefined".
        statuses = [row.status or _("Not Set") for row in result]
        series = [
            {
                "name": status,
                "type": "bar",
                "color": STATUS_COLORS.get(status, STATUS_COLOR_GRAY),
            }
            for status in statuses
        ]

        data = []
        for row in result:
            status = row.status or _("Not Set")
            data_row = {"status": status}
            for s in statuses:
                data_row[s] = row.count if s == status else 0
            data.append(data_row)

        return get_bar_chart_config(
            data,
            _("Tickets by Status"),
            _("Total tickets by status"),
            {
                "key": "status",
                "type": "category",
                "title": "Status",
                "timeGrain": "day",
                # Force every status label to render horizontally (the default
                # hides overlapping category labels).
                "echartOptions": {"axisLabel": {"interval": 0, "hideOverlap": False}},
            },
            _("Tickets"),
            series,
            stacked=True,
        )


@frappe.whitelist()
@agent_only
def get_dashboard_data(dashboard_type: str, filters: dict = None):
    """Override of ``helpdesk.api.dashboard.get_dashboard_data``.

    Mirrors the upstream permission and filter handling but instantiates the
    one_fm dashboard subclass so the trend charts include "Tickets by Status".
    """
    user = frappe.session.user
    is_manager = "Agent Manager" in frappe.get_roles(user)

    if not is_manager and (filters.get("agent") != user or filters.get("team")):
        frappe.throw(
            _("You are not allowed to view this dashboard data."),
            frappe.PermissionError,
        )
        return

    from_date = filters.get("from_date") if filters else None
    to_date = filters.get("to_date") if filters else None
    team = filters.get("team") if filters else None
    agent = filters.get("agent") if filters else None

    if agent == "@me":
        agent = frappe.session.user

    if not from_date:
        from_date = frappe.utils.add_days(frappe.utils.nowdate(), -30)
    if not to_date:
        to_date = frappe.utils.nowdate()

    _filters = frappe._dict(
        from_date=from_date,
        to_date=to_date,
        team=team,
        agent=agent,
    )

    dashboard = OneFMHelpdeskDashboard(_filters)

    if dashboard_type == "number_card":
        return dashboard.get_number_card_data()
    elif dashboard_type == "master":
        return get_master_dashboard_data(
            from_date, to_date, _filters.team, _filters.agent
        )
    elif dashboard_type == "trend":
        return dashboard.get_trend_data()
