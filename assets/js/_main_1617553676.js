$( document ).ready(function() {
    $("#submitQuery").on("click", function() {
      var domain = document.getElementById("domain").value;
      window.location.href = "/query/" + domain;
    });
});
