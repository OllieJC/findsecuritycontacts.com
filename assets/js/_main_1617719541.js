if (window.location.pathname == "/query" && window.location.search.indexOf("domain") != -1) {
  try {
    var urlParams = new URLSearchParams(window.location.search);
    var raw_domain = urlParams.get("domain").toLowerCase();
    raw_domain = raw_domain.replace("%3a%2f%2f", "://");
    if (raw_domain.indexOf("://") == -1) {
      raw_domain = `http://${raw_domain}`;
    }
    var tmp = new URL(raw_domain);
    if (tmp) {
      window.location.href = `/query/${tmp.hostname}`;
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
