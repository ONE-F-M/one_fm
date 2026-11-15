from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Work Permit",
		"Work Permit",
		(
			"Work Permit - GR Manager",
			"Work Permit - GR Operator",
			"Work Permit-PRO",
		),
	)
