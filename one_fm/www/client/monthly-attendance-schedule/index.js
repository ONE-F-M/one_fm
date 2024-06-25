frappe.ready(function () {
    fetch_data()

});



const fetch_data = () => {
    frappe.call({
        method: 'one_fm.www.client.monthly-attendance-schedule.index.get_client_roster',
        args:{
            route_hash: new URLSearchParams(window.location.search).get("id")
        },
        type: "GET",
        callback: function(r){
            if(r && r.status_code == 200){
                const options = {
                    columns: r.data.columns,
                    data: r.data.data
                }
                const datatable = new DataTable('#datatable', options);
                datatable.getColumns();

            } else {
                const container = document.getElementById("datatable");
                container.innerHTML = `${r.message}`;
            }
        }
    });
}


