from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Residency",
		"MOI",
		(
			"Residency - GR Operator",
			"Residency - PRO",
		),
	)
