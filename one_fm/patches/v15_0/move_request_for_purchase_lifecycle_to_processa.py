from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Request for Purchase",
		"Request for Purchase",
		(
			"Assign RFP Owner on RFP Return to Draft",
			"Assign RFP to Purchase Officer",
			"Assign to Purchase Manager for Approval",
		),
	)
