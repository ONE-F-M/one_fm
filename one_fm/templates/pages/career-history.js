// career-history JS here

document.getElementById('erfNumber').value = "987654321";
document.getElementById('applicantId').value = "12345";
document.getElementById('historyScore').value = "10";
document.getElementById('Promotions').value = "100$";
document.getElementById('Experience').value = "";
let numberofCompany= document.getElementById('numberofCompany');

function show(){
    var value = numberofCompany.options[numberofCompany.selectedIndex].value;
    console.log( value);
}
numberofCompany.onchange = show
