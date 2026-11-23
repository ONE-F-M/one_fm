from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Request for Material",
		"RFM",
		("RFM Approver", "Assigning Warehouse Supervisor Upon Approval"),
	)
