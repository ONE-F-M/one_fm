frappe.ready(function() {

    var curr_url = window.location.href
    if (curr_url.startsWith('one-fm')) {
        window.location.replace('/homepage');
    } else {
        window.location.replace('/login');
    }

});