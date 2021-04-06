function returnDomain(inputStr) {
  var res = "";
  try {
    var raw_domain = inputStr.toLowerCase();
    raw_domain = raw_domain.replace("%3a%2f%2f", "://");
    if (raw_domain.indexOf("://") == -1) {
      raw_domain = `http://${raw_domain}`;
    }
    var tmp = new URL(raw_domain);
    if (tmp) {
      res = `/query/${tmp.hostname}`;
    }
  } catch (e) {
    console.log("Failed to work out domain: ", e);
  }
  return res;
}

if (window.location.pathname == "/query" && window.location.search.indexOf("domain") != -1) {
  try {
    var urlParams = new URLSearchParams(window.location.search);
    var tmp = returnDomain(urlParams.get("domain"));
    if (tmp) {
      window.location.href = tmp;
    }
  } catch (e) {
    console.log("Failed to rewrite URL: ", e);
  }
}

function toggleMenu(evt) {
  var targetStr = evt.currentTarget.attributes.getNamedItem("data-bs-target").value;
  var target = document.getElementById(targetStr.replace("#", ""));
  if (target.className.indexOf("show") != -1) {
    target.classList.remove("show");
  } else {
    target.classList.add("show");
  }
}

try {
  var navBars = document.getElementsByClassName("navbar-toggler");
  for (var i = 0; i < navBars.length; i++) {
    navBars[i].addEventListener("click", toggleMenu, false);
  }
} catch (e) {
  console.log("Unable to setup menu:", e);
}


function domainSubmit(evt) {
  var targetStr = evt.currentTarget.attributes.getNamedItem("data-target").value;
  var target = document.getElementById(targetStr.replace("#", ""));
  var tmp = returnDomain(target.value);
  if (tmp) {
    window.location.href = tmp;
  }
  evt.preventDefault();
}

try {
  var domainSubmits = document.getElementsByClassName("domain-submit");
  for (var i = 0; i < domainSubmits.length; i++) {
    domainSubmits[i].addEventListener("click", domainSubmit, false);
  }
} catch (e) {
  console.log("Unable to setup domain submit button:", e);
}

try {
  var domainInputs = document.getElementsByClassName("domain-input");
  for (var i = 0; i < domainInputs.length; i++) {
    domainInputs[i].addEventListener("keyup", function(event) {
      // Number 13 is the "Enter" key on the keyboard
      if (event.keyCode === 13) {
        // Cancel the default action, if needed
        event.preventDefault();
        // Trigger the button element with a click
        var targetStr = event.currentTarget.attributes.getNamedItem("data-target").value;
        var target = document.getElementById(targetStr.replace("#", ""));
        document.getElementById(target).click();
      }
    });
  }
} catch (e) {
  console.log("Unable to setup domain input listener:", e);
}
