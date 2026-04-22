function sync_matrix(frm) {
    let source_objects = (frm.doc.interview_question || []).filter(function(row) {
        return !!row.questions;
    });
    
    let source_questions = source_objects.map(function(row) { return row.questions; });
    
    let target_matrix = frm.doc.interview_matrix || [];
    // Reuse existing matrix rows by question so row identities and typed data are preserved
    let matrix_map = {};
    target_matrix.forEach(function(row) {
        if (row.question && !matrix_map[row.question]) {
            matrix_map[row.question] = row;
        }
    });

    // Skip updates if the matrix is already strictly in sync
    let is_consistent = target_matrix.length === source_objects.length && source_objects.every(function(s_row, index) {
        let t_row = target_matrix[index];
        if (!t_row) return false;
        return t_row.question === s_row.questions && t_row.category === s_row.category && t_row.weight === s_row.weight;
    });

    if (is_consistent) {
        frm.refresh_field("interview_matrix");
        return;
    }

    // Remove only rows that no longer exist in the source question list
    target_matrix
        .filter(function(row) {
            return row.question && source_questions.indexOf(row.question) === -1;
        })
        .forEach(function(row) {
            frappe.model.clear_doc(row.doctype, row.name);
        });

    // Build the matrix in source order, reusing existing rows and updating metadata where possible
    let next_matrix = source_objects.map(function(s_row) {
        let existing_row = matrix_map[s_row.questions];
        if (existing_row) {
            if (existing_row.category !== s_row.category) {
                frappe.model.set_value(existing_row.doctype, existing_row.name, 'category', s_row.category);
            }
            if (existing_row.weight !== s_row.weight) {
                frappe.model.set_value(existing_row.doctype, existing_row.name, 'weight', s_row.weight);
            }
            return existing_row;
        }
        
        let new_row = frm.add_child("interview_matrix");
        frappe.model.set_value(new_row.doctype, new_row.name, 'question', s_row.questions);
        frappe.model.set_value(new_row.doctype, new_row.name, 'category', s_row.category);
        frappe.model.set_value(new_row.doctype, new_row.name, 'weight', s_row.weight);
        return new_row;
    });
    
    frm.doc.interview_matrix = next_matrix;
    frm.doc.interview_matrix.forEach(function(row, index) {
        frappe.model.set_value(row.doctype, row.name, 'idx', index + 1);
    });
    
    frm.refresh_field("interview_matrix");
}

frappe.ui.form.on('Interview Round', {
    refresh: function(frm) {
        frm.add_custom_button('Sync Matrix', () => sync_matrix(frm), 'Options');
    },
    validate: function(frm) {
        sync_matrix(frm);
    }
});

frappe.ui.form.on('Interview Questions', {
    questions: function(frm, cdt, cdn) {
        sync_matrix(frm);
    }
});
