frappe.ready(function () {

  // Setup year filter. Show last 3 years
  let $year_select_field = $('select[data-fieldname="year"]');
  for(i=0; i<3; i++){
    year = moment().subtract(i,'year').format("YYYY");
    $year_select_field.append(`<option value="${year}">${year}</option>`);
  }
  
  $('select[data-fieldname="month"]').val(moment().month() + 1); // month + 1 because zero based indexing

  $('select[data-fieldname="year"]').on('change', function(){
    $('#monthly-datatable').hide();
    $('.summary-placeholder').show();
    get_monthly_data();
  })

  $('select[data-fieldname="month"]').on('change', function(){
    $('#monthly-datatable').hide();
    $('.summary-placeholder').show();
    get_monthly_data();
  })

  get_monthly_data();
});

function get_monthly_data(){
  let {get_query_params, get_query_string} = frappe.utils;

  let id = get_query_params(get_query_string(window.location.search)).id;
  let year = $('select[data-fieldname="year"]').val();
  let month = $('select[data-fieldname="month"]').val()

  frappe.call({
    method: "one_fm.www.client.monthly_attendance_summary.index.get_monthly_data",
    type: "GET",
    args: {"id": id, "month": month, "year": year},
    callback: function(r) { render_table(r) },
    
  });
}  


function render_table(res){
  $('.summary-placeholder').hide();
  $('#monthly-datatable').show();
  let {columns, data} = res.message;

  const datatable = new DataTable('#monthly-datatable', {
    serialNoColumn: true,
    inlineFilters: true,
    language: frappe.boot.lang,
    layout: "fluid",
    direction: frappe.utils.is_rtl() ? "rtl" : "ltr",
    columns: columns,
    noDataMessage : "No data found!",
    isFilterShown: true,
    clusterize: false,
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