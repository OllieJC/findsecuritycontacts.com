$( document ).ready(function() {
  if (window.location.pathname == "/query") {
    $("#submitQuery").on("click", function() {
      var domain = document.getElementById("domain").value;
      window.location.href = "/query/" + domain;
    });

    var input = document.getElementById("domain");

    // Execute a function when the user releases a key on the keyboard
    input.addEventListener("keyup", function(event) {
      // Number 13 is the "Enter" key on the keyboard
      if (event.keyCode === 13) {
        // Cancel the default action, if needed
        event.preventDefault();
        // Trigger the button element with a click
        document.getElementById("submitQuery").click();
      }
    });
  }
});
