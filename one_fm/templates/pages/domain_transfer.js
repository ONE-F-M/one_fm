frappe.ready(function() {

    var curr_url = window.location.href
    if (curr_url.startsWith('http://one-fm') && location.pathname!='/homepage') {
        window.location.replace('/homepage');
    }

    if (!curr_url.startsWith('http://one-fm')) {
        window.location.replace('/login');
    }

});