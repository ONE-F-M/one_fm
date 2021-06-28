// career-history JS here

document.getElementById('erfNumber').value = "987654321";
document.getElementById('applicantId').value = "12345";
document.getElementById('historyScore').value = "10";
document.getElementById('Promotions').value = "100$";
document.getElementById('Experience').value = "";
let numberofCompany= document.getElementById('numberofCompany');

function show(){
    var valuee = numberofCompany.options[numberofCompany.selectedIndex].value;
    console.log(valuee);
}
numberofCompany.onchange = show();

// var df= document.getElementById("startDate").value;
// var dt = .value;  


function totelvalue(){
    var df= Number(document.getElementById("startDate"));
var dt = Number(document.getElementById('endDate'));   
var allMonths= dt.getMonth() - df.getMonth() + (12 * (dt.getFullYear() -     df.getFullYear()));
var allYears= dt.getFullYear() - df.getFullYear();
var partialMonths = dt.getMonth() - df.getMonth();
if (partialMonths < 0) {
allYears--;
partialMonths = partialMonths + 12;
}
var total = allYears + " years " + partialMonths + " months";
console.log(total); 
console.log({jaren: allYears, maanden: partialMonths});
}
console.log(totelvalue());