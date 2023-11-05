frappe.ready(function() {
    $('#submit').on('click', function(){
        // alert("Helooooooooooo");
        let answer_map = {};
        for(i=1;i<10;i++){
            console.log(i, $(`[name=${i}]:checked`).val())
            answer_map[i] = $(`[name=${i}]:checked`).val();
        }
        answer_map['10'] = $("textarea[name=10]").val();

        console.log(answer_map);
    })
})