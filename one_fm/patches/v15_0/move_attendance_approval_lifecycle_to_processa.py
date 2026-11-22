from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Attendance Approval",
		"Attendance Amendment",
		("Assign to Site Supervisor", "Assign Attendance Amendment to Project Manager"),
	)
