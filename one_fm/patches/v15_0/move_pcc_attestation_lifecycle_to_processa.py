from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"PCC Attestation",
		"PCC Attestation",
		(
			"PCC Attestation-GRO",
			"PCC Attestation-PRO",
		),
	)
