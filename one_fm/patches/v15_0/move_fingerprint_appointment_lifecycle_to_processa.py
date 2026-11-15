from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Fingerprint Appointment",
		"Fingerprint Appointment",
		(
			"Action Fingerprint Appointment - PRO",
			"Action Fingerprint Appointment - Supervisor",
			"Action Fingerprint Appointment - Transportation Supervisor",
			"Confirm Site Pickup for Fingerprint Appointment - GR Operator",
		),
	)
