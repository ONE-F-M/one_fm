// import DataTable from "frappe-datatable";

frappe.ready(function () {
    fetch_data()




});



const fetch_data = () => {
    frappe.call({
		method: 'one_fm.www.client.client-roster.index.get_client_roster',
        args:{
            route_hash: new URLSearchParams(window.location.search).get("id")
        },
		callback: function(r){
			if(r && r.status_code == 200){
                const options = {
                    columns: r.data.columns,
                    data: r.data.data
                }
                console.log(options)
                // const options = {
                //     columns: ['Name', 'Position', 'Salary'],
                //     data: [
                //         ['John Doe', 'DevOps Engineer', '$12300'],
                //         ['Mary Jane', 'UX Design', '$14000'],
                //     ]
                // }
                
                const datatable = new DataTable('#datatable', options);
                datatable.getColumns();

            }
		}
	});
}

