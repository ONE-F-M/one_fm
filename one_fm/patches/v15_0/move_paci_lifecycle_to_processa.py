from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"PACI",
		"PACI",
		(
			"Action PACI",
			"PACI-PRO",
		),
	)
