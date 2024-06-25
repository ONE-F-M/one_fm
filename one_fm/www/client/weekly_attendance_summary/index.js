frappe.ready(function () {
  let {get_query_params, get_query_string} = frappe.utils;
  let id = get_query_params(get_query_string(window.location.search)).id
  frappe.call({
    method: "one_fm.www.client.weekly_attendance_summary.index.get_weekly_data",
    type: "GET",
    args: {"id": id},
    callback: function(r) { render_table(r) },
  });

  function render_table(res){
    let {columns, data} = res.message;

    const datatable = new DataTable('#weekly-datatable', {
      serialNoColumn: true,
      inlineFilters: true,
      language: frappe.boot.lang,
      layout: "fixed",
      direction: frappe.utils.is_rtl() ? "rtl" : "ltr",
      columns: columns,
      noDataMessage : "No data found!",
      isFilterShown: true,
      data: data,
      events: {
        onSwitchColumn(column) {
          datatable.columnmanager.toggleFilter(1)
        },
        onSortColumn(column) {
          datatable.columnmanager.toggleFilter(1)
        }
    }
    });
    datatable.columnmanager.toggleFilter(1);

    window.datatable = datatable;
  }
});

