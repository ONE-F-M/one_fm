from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Roster Employee Actions",
		None,
		(
			"Roster Employee Actions - Site Supervisor",
			"Roster Employee Actions - Project Manager",
		),
	)
