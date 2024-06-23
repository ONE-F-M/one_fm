// import "one_fm.public.js.datatable.js";

frappe.ready(function () {
    fetch_data()



});



const fetch_data = () => {
    frappe.call({
		method: 'one_fm.www.client.client-roster.index.get_client_roster',
		callback: function(r) {
			if(r && r.status_code == 200){
                const options = {
                    columns: r.data.columns,
                    data: r.data.data
                }
                const datatable = new DataTable('#datatable', options);
            }
		}
	});
}

// $(document).ready(function() {
//     var table = $('#example').DataTable( {
//         lengthChange: false,
//         buttons: [ 'copy', 'excel', 'pdf', 'colvis' ]
//     } );

//     table.buttons().container()
//         .appendTo( '#example_wrapper .col-md-6:eq(0)' );
// } );