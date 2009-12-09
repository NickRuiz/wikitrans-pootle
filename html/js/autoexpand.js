
/*
 * TODO: this code may have a better life if we migrate it to jQuery.
 */
$(document).ready(function() {
    // Pootle namespace
    $.pootle = {};
    // Set initial focus on page load
    var initialFocus = $(".translate-original-focus textarea");
    initialFocus.focus();
    $.pootle.focusedElement = initialFocus.get(0);

    // Update focus when appropriate
    $(".focusthis").focus(function(e) {
        $.pootle.focusedElement = e.target;
    });

    // Write TM results into the currently focused element
    $(".writetm").click(function() {
       var tmtext = $(".tm-translation", this).html();
       $($.pootle.focusedElement).replaceSelection(tmtext);
    });

    // Write special chars into the currently focused element
    $(".writespecial").click(function() {
       var specialtext = $(this).html();
       $($.pootle.focusedElement).replaceSelection(specialtext);
    });

});

function copyorigtranslation(elementNumber)
{
	var i = 0;
    var enelement = document.getElementById("orig-pure" + elementNumber + "-" + 0);
    var envalue = enelement.value.replace("\n", "\\n\n", "g").replace("\t", "\\t", "g");
	//no plurals
	var trelement = document.getElementById("areatrans" + elementNumber );
	if (trelement){
		trelement.value = envalue;
		trelement.focus();
		return;
	}

	//plurals
	trelement = document.getElementById("areatrans" + elementNumber + "-" + i );
    var enplelement = document.getElementById("orig-pure" + elementNumber + "-" + 1);
    var enplvalue = enplelement.value.replace("\n", "\\n\n", "g").replace("\t", "\\t", "g");
	while (trelement)
	{
		trelement.focus(); //it will go to the last one
		trelement.value = i == 0 ? envalue : enplvalue;
		i++;
		trelement = document.getElementById("areatrans" + elementNumber + "-" + i );
	}
}

