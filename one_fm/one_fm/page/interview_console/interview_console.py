import frappe
from frappe.utils import getdate, nowdate

ALLOWED_ROLES = {"System Manager", "HR Manager", "Interviewer", "HR User", "Recruiter", "Senior Recruiter"}

def _check_console_access():
    """Check if the current user has at least one allowed role."""
    if not ALLOWED_ROLES.intersection(set(frappe.get_roles())):
        frappe.throw("You are not permitted to access this console.", frappe.PermissionError)

def get_valid_fields():
    meta = frappe.get_meta('Job Applicant')
    return [df.fieldname for df in meta.fields]

def _ensure_skill_exists(skill_name):
    """Create a Skill document if it doesn't exist, return the skill name."""
    if not skill_name:
        skill_name = "General"
    # Truncate to max 140 chars (Frappe Link field limit)
    skill_name = skill_name[:140]
    if not frappe.db.exists("Skill", skill_name):
        try:
            frappe.get_doc({
                "doctype": "Skill",
                "skill_name": skill_name
            }).insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            pass
    return skill_name

@frappe.whitelist()
def get_applicant_data(applicant):
    """
    Returns age, remarks, score, status, and dynamic interview matrix.
    """
    _check_console_access()
    valid_fields = get_valid_fields()
    res = {"age": "--", "height": "", "remarks": "", "score": 0, "status": "Open", "matrix": []}
    
    # Fetch Applicant details
    applicant_doc = frappe.get_doc('Job Applicant', applicant)
    designation = applicant_doc.designation
    nationality = applicant_doc.get('one_fm_nationality')

    # Height
    res["height"] = applicant_doc.get('one_fm_height') or ""

    # Discovery for DOB (Updated with user's specific fields)
    found_dob = next((f for f in ['one_fm_date_of_birth', 'date_of_birth', 'dob', 'birth_date', 'custom_date_of_birth'] if f in valid_fields), None)
    if found_dob:
        dob = applicant_doc.get(found_dob)
        if dob:
            today = getdate(nowdate())
            birthday = getdate(dob)
            res["age"] = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            
    # Discovery for Remarks
    found_remarks = next((f for f in ['interview_remarks', 'remarks', 'custom_remarks', 'notes'] if f in valid_fields), None)
    if found_remarks:
        res["remarks"] = applicant_doc.get(found_remarks) or ""
        
    # Fetch score from Interview document (where save_interview_data stores it)
    interview_score = frappe.db.get_value("Interview", {
        "job_applicant": applicant,
        "docstatus": ["<", 2]
    }, "total_interview_score") or 0
    res["score"] = interview_score
        
    # Standard Status
    res["status"] = applicant_doc.status or "Open"
    
    # Custom Status Override
    for custom_field in ['workflow_state', 'one_fm_applicant_status']:
        if custom_field in valid_fields:
            custom_status = applicant_doc.get(custom_field)
            if custom_status in ["Accepted", "Job Offer Issued", "Shortlisted", "Hired", "Hold", "Rejected"]:
                res["status"] = custom_status
            
    # Fetch Dynamic Matrix from Interview Round
    # Lookup priority: designation + nationality → designation only → round_name
    
    applicant_designation = applicant_doc.get('designation') or applicant_doc.get('one_fm_designation')
    
    matrix_data = []
    
    if applicant_designation:
        interview_round = None
        # Only filter by nationality if the custom field exists on Interview Round
        round_meta = frappe.get_meta("Interview Round")
        has_nationality = round_meta.has_field("one_fm_nationality")
        if nationality and has_nationality:
            interview_round = frappe.db.get_value("Interview Round", {
                "designation": applicant_designation,
                "one_fm_nationality": nationality
            }, "name")
        
        if not interview_round:
            interview_round = frappe.db.get_value("Interview Round", {
                "designation": applicant_designation
            }, "name")
            
        if not interview_round:
            interview_round = frappe.db.get_value("Interview Round", {
                "round_name": applicant_designation
            }, "name")

        if interview_round:
            round_doc = frappe.get_doc("Interview Round", interview_round)
            if round_doc.get("interview_question"):
                for q in round_doc.interview_question:
                    matrix_data.append({
                        "category": q.get("category") or "General",
                        "category_weight": q.get("category_weight") or "",
                        "question": q.questions,
                        "weight": q.weight or 0,
                        "ratings": [
                            q.answer_5 or "Excellent",
                            q.answer_4 or "Good",
                            q.answer_3 or "Average",
                            q.answer_2 or "Poor",
                            q.answer_1 or "Very Poor"
                        ]
                    })
    
    res["matrix"] = matrix_data
    res["interview_round"] = interview_round if applicant_designation else None
    
    # Check for Job Offers
    try:
        offers = frappe.get_all('Job Offer', filters={'job_applicant': applicant, 'docstatus': ['<', 2]}, fields=['name'])
        res["job_offers"] = len(offers)
        if len(offers) == 1:
            res["job_offer_id"] = offers[0].name
    except Exception:
        res["job_offers"] = 0
        
    return res

@frappe.whitelist()
def save_interview_data(applicant, score, remarks, status, scores_detail=None, interview_round=None, height=None):
    """
    Saves interview results by creating/updating an Interview document.
    Also updates Job Applicant status.
    
    Args:
        scores_detail: JSON string of [{question, category, score, weight}, ...]
        interview_round: Name of the Interview Round used
    """
    import json
    from frappe.utils import nowdate, nowtime
    _check_console_access()
    
    valid_fields = get_valid_fields()
    
    # --- 1. Update Job Applicant Status ---
    doc = frappe.get_doc("Job Applicant", applicant)

    # Check if a Workflow is active on Job Applicant
    has_workflow = frappe.get_all("Workflow", filters={"document_type": "Job Applicant", "is_active": 1}, limit=1)

    if status == "Shortlisted":
        doc.one_fm_applicant_status = "Shortlisted"
    elif has_workflow:
        # Update workflow_state to avoid read-only status conflicts
        doc.workflow_state = status
    else:
        doc.status = status

    # Save height if provided
    if height:
        doc.one_fm_height = float(height)
    doc.save(ignore_permissions=True)
    
    # --- 2. Map console status to Interview status ---
    interview_status_map = {
        "Accepted": "Cleared",
        "Shortlisted": "Cleared",
        "Rejected": "Rejected",
        "Hold": "Under Review",
    }
    interview_status = interview_status_map.get(status, "Under Review" if int(score or 0) > 0 else "Pending")
    
    # --- 3. Parse scores detail for later use ---
    parsed_details = []
    if scores_detail:
        try:
            parsed_details = json.loads(scores_detail) if isinstance(scores_detail, str) else scores_detail
        except Exception:
            pass
    
    # --- 4. Find or Create Interview (interview_summary left blank) ---
    existing_interview = frappe.db.get_value("Interview", {
        "job_applicant": applicant,
        "interview_round": interview_round,
        "docstatus": ["<", 2]
    }, "name") if interview_round else None
    
    if not existing_interview:
        existing_interview = frappe.db.get_value("Interview", {
            "job_applicant": applicant,
            "docstatus": ["<", 2]
        }, "name")
    
    if existing_interview:
        interview_doc = frappe.get_doc("Interview", existing_interview)
        
        if interview_doc.docstatus == 1:
            frappe.db.set_value("Interview", existing_interview, {
                "status": interview_status,
                "interview_summary": "",
                "interview_round": interview_round or interview_doc.interview_round
            }, update_modified=True)
        else:
            interview_doc.status = interview_status
            interview_doc.interview_summary = ""
            if interview_round:
                interview_doc.interview_round = interview_round
            interview_doc.save(ignore_permissions=True)
            interview_doc.submit()
    else:
        interview_doc = frappe.new_doc("Interview")
        interview_doc.interview_round = interview_round or ""
        interview_doc.job_applicant = applicant
        interview_doc.designation = doc.designation
        interview_doc.status = interview_status
        interview_doc.scheduled_on = nowdate()
        interview_doc.from_time = nowtime()
        interview_doc.to_time = nowtime()
        
        if interview_round:
            try:
                round_doc = frappe.get_doc("Interview Round", interview_round)
                for interviewer in round_doc.interviewers:
                    interview_doc.append("interview_details", {
                        "interviewer": interviewer.user
                    })
            except Exception:
                pass
        
        interview_doc.insert(ignore_permissions=True)
        interview_doc.submit()
    # --- 6. Auto-create/update Interview Feedback ---
    interview_name = existing_interview or interview_doc.name
    feedback_result = ""
    if status in ["Accepted", "Shortlisted"]:
        feedback_result = "Cleared"
    elif status == "Rejected":
        feedback_result = "Rejected"
    
    # avg_rating will be calculated from category averages after building skill_rows
    
    # Build per-category average scores for skill circles
    category_scores = {}
    for d in parsed_details:
        cat = d.get("category", "General")
        q_score = float(d.get("score", 0))
        if cat not in category_scores:
            category_scores[cat] = {"total": 0, "count": 0}
        category_scores[cat]["total"] += q_score
        category_scores[cat]["count"] += 1
    
    # Convert to list of {skill, rating} for skill_assessment
    skill_rows = []
    for cat, data in category_scores.items():
        cat_avg = data["total"] / data["count"] if data["count"] > 0 else 0
        cat_rating = cat_avg / 5.0  # Convert 0-5 score to 0-1 rating
        skill_name = _ensure_skill_exists(cat)
        skill_rows.append({"skill": skill_name, "rating": min(max(cat_rating, 0), 1)})
    
    # Calculate avg_rating from category averages (matches Feedback Summary circles)
    if skill_rows:
        avg_rating = sum(r["rating"] for r in skill_rows) / len(skill_rows)
    else:
        avg_rating = float(score or 0) / 100.0
    avg_rating = min(max(avg_rating, 0), 1)
    
    existing_feedback = frappe.db.get_value("Interview Feedback", {
        "interview": interview_name,
        "interviewer": frappe.session.user,
        "docstatus": ["<", 2]
    }, "name")
    
    if existing_feedback:
        fb_doc = frappe.get_doc("Interview Feedback", existing_feedback)
        if fb_doc.docstatus == 1:
            # Update submitted feedback in-place: update skill ratings and average
            # Delete old skill_assessment rows and insert new ones
            frappe.db.sql("DELETE FROM `tabSkill Assessment` WHERE parent=%s", existing_feedback)
            for idx, row in enumerate(skill_rows, 1):
                frappe.get_doc({
                    "doctype": "Skill Assessment",
                    "parent": existing_feedback,
                    "parenttype": "Interview Feedback",
                    "parentfield": "skill_assessment",
                    "idx": idx,
                    "skill": row["skill"],
                    "rating": row["rating"]
                }).db_insert()
            # Update evaluation criteria
            frappe.db.sql("DELETE FROM `tabInterview Evaluation Detail` WHERE parent=%s", existing_feedback)
            for idx, d in enumerate(parsed_details, 1):
                frappe.get_doc({
                    "doctype": "Interview Evaluation Detail",
                    "parent": existing_feedback,
                    "parenttype": "Interview Feedback",
                    "parentfield": "custom_evaluation_criteria",
                    "idx": idx,
                    "category": d.get("category", "General"),
                    "question": d.get("question", ""),
                    "weight": float(d.get("weight", 0)),
                    "rating": int(d.get("score", 0)),
                    "max_rating": 5
                }).db_insert()
            # Update average_rating and result
            frappe.db.set_value("Interview Feedback", existing_feedback, {
                "average_rating": avg_rating,
                "result": feedback_result,
                "custom_remarks": remarks or ""
            }, update_modified=True)
        else:
            fb_doc.result = feedback_result
            fb_doc.feedback = ""
            fb_doc.custom_remarks = remarks or ""
            fb_doc.skill_assessment = []
            for row in skill_rows:
                fb_doc.append("skill_assessment", row)
            # Populate structured child table
            fb_doc.custom_evaluation_criteria = []
            for d in parsed_details:
                fb_doc.append("custom_evaluation_criteria", {
                    "category": d.get("category", "General"),
                    "question": d.get("question", ""),
                    "weight": float(d.get("weight", 0)),
                    "rating": int(d.get("score", 0)),
                    "max_rating": 5
                })
            fb_doc.save(ignore_permissions=True)
            fb_doc.submit()
            # Force average_rating from console score
            fb_doc.db_set("average_rating", avg_rating)
    
    if not existing_feedback:
        fb = frappe.new_doc("Interview Feedback")
        fb.interview = interview_name
        fb.interview_round = interview_round or ""
        fb.job_applicant = applicant
        fb.interviewer = frappe.session.user
        fb.result = feedback_result
        fb.feedback = ""
        fb.custom_remarks = remarks or ""
        for row in skill_rows:
            fb.append("skill_assessment", row)
        # Populate structured child table
        for d in parsed_details:
            fb.append("custom_evaluation_criteria", {
                "category": d.get("category", "General"),
                "question": d.get("question", ""),
                "weight": float(d.get("weight", 0)),
                "rating": int(d.get("score", 0)),
                "max_rating": 5
            })
        fb.insert(ignore_permissions=True)
        fb.submit()
        # Force average_rating from console score
        fb.db_set("average_rating", avg_rating)
    
    # --- 7. Update Interview doc's average_rating so the Feedback tab shows correct stars ---
    frappe.db.set_value("Interview", interview_name, {
        "average_rating": avg_rating,
        "total_interview_score": float(score or 0),
    }, update_modified=False)
    
    frappe.db.commit()
    return "Success"

@frappe.whitelist()
def clear_interview_data(applicant):
    """
    Cancels and deletes Interview Feedback and Interview documents for the applicant.
    Called when the Reset button is clicked in the Interview Console.
    """
    _check_console_access()
    # Delete feedbacks first (child reference)
    feedbacks = frappe.get_all("Interview Feedback", filters={
        "job_applicant": applicant, "docstatus": ["<", 2]
    }, fields=["name", "docstatus"])
    for fb in feedbacks:
        if fb.docstatus == 1:
            frappe.get_doc("Interview Feedback", fb.name).cancel()
        frappe.delete_doc("Interview Feedback", fb.name, force=True, ignore_permissions=True)
    
    # Delete interviews
    interviews = frappe.get_all("Interview", filters={
        "job_applicant": applicant, "docstatus": ["<", 2]
    }, fields=["name", "docstatus"])
    for iv in interviews:
        if iv.docstatus == 1:
            frappe.get_doc("Interview", iv.name).cancel()
        frappe.delete_doc("Interview", iv.name, force=True, ignore_permissions=True)
    
    # Reset Job Applicant status to Open
    doc = frappe.get_doc("Job Applicant", applicant)
    doc.status = "Open"
    doc.save(ignore_permissions=True)

    frappe.db.commit()
    return "Success"

@frappe.whitelist()
def get_applicant_list(hiring_method=None, start=0, page_length=200):
    """
    Returns the list of applicants with discovered score fields.
    Optionally filtered by hiring method (e.g., 'Bulk Recruitment').
    Supports pagination via start and page_length.
    """
    _check_console_access()
    valid_fields = get_valid_fields()
    # Fields that are guaranteed to exist
    fields = ['name', 'applicant_name', 'status', 'job_title', 'designation']
    
    for custom_field in ['workflow_state', 'one_fm_applicant_status']:
        if custom_field in valid_fields:
            fields.append(custom_field)

    filters = {}
    if hiring_method and 'one_fm_hiring_method' in valid_fields:
        filters['one_fm_hiring_method'] = hiring_method
            
    applicants = frappe.get_all('Job Applicant', fields=fields, filters=filters,
                                limit_start=int(start), limit_page_length=int(page_length),
                                order_by='creation desc')
    
    # Batch-fetch interview scores to avoid N+1 queries
    applicant_names = [app.name for app in applicants]
    interview_scores_map = {}
    if applicant_names:
        interview_rows = frappe.get_all(
            "Interview",
            filters={"job_applicant": ["in", applicant_names], "docstatus": ["<", 2]},
            fields=["job_applicant", "total_interview_score"],
        )
        for row in interview_rows:
            key = row.get("job_applicant")
            if key and key not in interview_scores_map:
                interview_scores_map[key] = row.get("total_interview_score") or 0

    # Resolve Job Opening title, apply batched scores, and override status
    for app in applicants:
        if app.get('job_title'):
            opening_title = frappe.db.get_value('Job Opening', app.job_title, 'job_title')
            app['job_opening_title'] = opening_title or app.job_title

        app['interview_score'] = interview_scores_map.get(app.name, 0)

        for custom_field in ['workflow_state', 'one_fm_applicant_status']:
            if app.get(custom_field) in ["Accepted", "Job Offer Issued", "Shortlisted", "Hired", "Hold", "Rejected"]:
                app['status'] = app[custom_field]
                
    return applicants


