def get_hd_ticket_properties():
	return [
		{
			"doctype_or_field": "DocType",
			"doc_type": "HD Ticket",
			"field_name": None,
			"property": "field_order",
			"property_type": "Data",
			"value": "[\"subject_section\", \"subject\", \"custom_is_external\", \"custom_project\", \"custom_external_customer\", \"custom_project_manager\", \"custom_project_manager_name\", \"raised_by\", \"status\", \"priority\", \"status_category\", \"cb00\", \"custom_ticket_category\", \"custom_reference_doctype\", \"custom_process\", \"custom_process_owner\", \"ticket_type\", \"agent_group\", \"summary\", \"ticket_split_from\", \"custom_bug_buster\", \"sb_details\", \"description\", \"template\", \"key\", \"sla_tab\", \"service_level_section\", \"sla\", \"response_by\", \"raised_outside_working_hours\", \"cb\", \"agreement_status\", \"resolution_by\", \"service_level_agreement_creation\", \"on_hold_since\", \"total_hold_time\", \"response_tab\", \"response\", \"first_response_time\", \"first_responded_on\", \"first_response_failed_by\", \"column_break_26\", \"avg_response_time\", \"last_agent_response\", \"last_customer_response\", \"resolution_tab\", \"section_break_19\", \"resolution_details\", \"custom_time_of_call\", \"custom_sub_contractor_dispatch_time\", \"column_break1\", \"opening_date\", \"opening_time\", \"resolution_date\", \"planning_prompts_count\", \"execution_prompt_count\", \"resolution_time\", \"user_resolution_time\", \"resolution_failed_by\", \"reference_tab\", \"additional_info\", \"contact\", \"customer\", \"email_account\", \"custom_dev_ticket\", \"custom_github_issue_url\", \"custom_pivotal_tracker\", \"column_break_16\", \"via_customer_portal\", \"attachment\", \"content_type\", \"split_and_merge_section\", \"is_merged\", \"merged_with\", \"feedback_tab\", \"customer_feedback_section\", \"feedback_rating\", \"feedback\", \"feedback_extra\", \"development_feedback_sb\", \"developer_feedback\", \"column_break_banio\", \"development_process_owner_remark\"]",
		},
		{
			"doctype_or_field": "DocField",
			"doc_type": "HD Ticket",
			"field_name": "agent_group",
			"property": "hidden",
			"property_type": "Check",
			"value": "1",
		},
	]
