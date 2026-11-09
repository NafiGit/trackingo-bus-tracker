/* Trackingo Bus Tracker — front end.
 * The key lives only in this page's memory. It is never saved,
 * never put in a URL, and never logged. Live calls go through the
 * same-origin /api/live proxy as a POST with a JSON body.
 */
(function () {
  "use strict";

  var POLL_MS = 20000;
  var timer = null;
  var countdownTimer = null;
  var secondsLeft = 0;
  var currentKey = "";
  var mode = "idle"; // idle | live | demo

  var $ = function (id) { return document.getElementById(id); };
  var keyInput = $("key-input");
  var trackBtn = $("track-btn");
  var demoBtn = $("demo-btn");
  var stopBtn = $("stop-btn");
  var errorBox = $("error-box");
  var liveCard = $("live-card");
  var badge = $("mode-badge");

  function minutesBetween(scheduled, expected) {
    function mins(text) {
      if (!text) return null;
      var parts = text.trim().split(" ");
      if (parts.length < 2) return null;
      var hm = parts[0].split(":");
      var h = parseInt(hm[0], 10);
      var m = parseInt(hm[1], 10);
      if (isNaN(h) || isNaN(m)) return null;
      var mer = parts[1].toUpperCase();
      if (mer === "PM" && h !== 12) h += 12;
      if (mer === "AM" && h === 12) h = 0;
      return h * 60 + m;
    }
    var a = mins(scheduled);
    var b = mins(expected);
    if (a === null || b === null) return null;
    var d = b - a;
    if (d < -12 * 60) d += 24 * 60;
    if (d > 12 * 60) d -= 24 * 60;
    return d;
  }

  function asList(value) {
    if (Array.isArray(value)) return value;
    if (value && typeof value === "object") return Object.keys(value).map(function (k) { return value[k]; });
    return [];
  }

  function parseEta(data) {
    var status = data.current_status_details || {};
    var details = status.details || {};
    var latLong = status.lat_long || [null, null];
    var stops = asList(data.eta_map_data).map(function (stop) {
      if (!stop || typeof stop !== "object") return null;
      var scheduled = stop.scheduled_time || stop.schedule_time || "";
      var expected = stop.expected_time || stop.eta || "";
      return {
        name: stop.stop_name || stop.name || stop.location || "?",
        scheduled: scheduled,
        expected: expected,
        arrival: stop.arrival_time || "",
        departure: stop.departure_time || "",
        delayMin: minutesBetween(scheduled, expected),
        status: stop.status || ""
      };
    }).filter(Boolean);
    return {
      latitude: latLong[0],
      longitude: latLong[1],
      speed: details.speed,
      timestamp: details.timestamp,
      location: details.location,
      state: details.hstate || details.state,
      stops: stops
    };
  }

  function fmtDelay(min) {
    if (min === null || min === undefined) return "—";
    if (min <= 0) return "on time";
    return "+" + min + "m";
  }

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
  }

  function clearError() {
    errorBox.textContent = "";
    errorBox.classList.add("hidden");
  }

  function setBadge(text, cls) {
    badge.textContent = text;
    badge.className = "badge" + (cls ? " " + cls : "");
  }

  function render(parsed, isDemo) {
    liveCard.classList.remove("hidden");
    $("live-location").textContent = parsed.location || "?";
    var coords = (parsed.latitude !== null && parsed.latitude !== undefined)
      ? parsed.latitude + ", " + parsed.longitude
      : "—";
    var coordsEl = $("live-coords");
    coordsEl.textContent = "";
    coordsEl.appendChild(document.createTextNode(coords));
    if (parsed.latitude !== null && parsed.latitude !== undefined) {
      coordsEl.appendChild(document.createTextNode(" · "));
      var a = document.createElement("a");
      a.href = "https://www.google.com/maps?q=" + parsed.latitude + "," + parsed.longitude;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = "Open in Maps ↗";
      coordsEl.appendChild(a);
    }
    $("live-state").textContent = parsed.state || "—";
    $("live-speed").textContent = (parsed.speed === null || parsed.speed === undefined) ? "—" : parsed.speed + " km/h";
    $("live-time").textContent = parsed.timestamp || "—";

    var worst = null;
    var next = null;
    parsed.stops.forEach(function (s) {
      if (s.delayMin !== null && (worst === null || s.delayMin > worst)) worst = s.delayMin;
      if (!next && !s.arrival) next = s;
    });
    $("live-delay").textContent = worst === null ? "—" : fmtDelay(worst);
    $("live-next").textContent = next ? next.name + (next.expected ? " · " + next.expected : "") : "End of route";

    var body = $("stops-body");
    body.textContent = "";
    parsed.stops.forEach(function (s) {
      var tr = document.createElement("tr");
      if (next && s === next) tr.className = "next-stop";
      if (s.arrival) tr.className = "arrived";
      var cells = [
        s.name,
        s.scheduled || "—",
        s.expected || "—",
        fmtDelay(s.delayMin),
        s.arrival || "—"
      ];
      cells.forEach(function (text, i) {
        var td = document.createElement("td");
        td.textContent = text;
        if (i === 3 && s.delayMin !== null && s.delayMin > 0) td.className = "delay-bad";
        if (i === 3 && s.delayMin !== null && s.delayMin <= 0) td.className = "delay-ok";
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    $("last-updated").textContent = "Last updated " + new Date().toLocaleTimeString();
    if (isDemo) {
      $("countdown").textContent = "Demo data — fictional trip, no live polling";
    }
  }

  function renderJourney(journey) {
    var line = $("journey-line");
    if (!journey || typeof journey !== "object") { line.classList.add("hidden"); return; }
    var bits = [];
    ["operator_name", "operator", "service_name", "service", "route_name", "route"].forEach(function (k) {
      if (journey[k]) bits.push(journey[k]);
    });
    if (!bits.length) { line.classList.add("hidden"); return; }
    line.textContent = bits.join(" · ");
    line.classList.remove("hidden");
  }

  function fetchLive() {
    var payload = mode === "demo"
      ? null
      : { key: currentKey, mode: "eta" };
    var url = "/api/live" + (mode === "demo" ? "?demo=1" : "");
    var opts = payload
      ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }
      : {};
    return fetch(url, opts).then(function (resp) {
      return resp.json().then(function (data) {
        if (!resp.ok) throw new Error(data.error || ("HTTP " + resp.status));
        return data;
      });
    });
  }

  function poll() {
    fetchLive().then(function (data) {
      clearError();
      render(parseEta(data.eta_map || {}), !!data.demo);
      if (mode === "live" && data.journey) renderJourney(data.journey);
      $("countdown").textContent = "Refreshing in 20s";
      secondsLeft = 20;
    }).catch(function (err) {
      showError(err.message || "Could not fetch the bus.");
      $("countdown").textContent = "Retrying in 20s";
      secondsLeft = 20;
    });
  }

  function startCountdown() {
    clearInterval(countdownTimer);
    secondsLeft = 20;
    countdownTimer = setInterval(function () {
      secondsLeft -= 1;
      if (secondsLeft <= 0) secondsLeft = 20;
      if (mode !== "demo") {
        $("countdown").textContent = "Refreshing in " + secondsLeft + "s";
      }
    }, 1000);
  }

  function startTracking(nextMode, key) {
    stopTracking(true);
    mode = nextMode;
    currentKey = key || "";
    setBadge(nextMode === "demo" ? "DEMO — fictional data" : "● LIVE", nextMode === "demo" ? "demo" : "live");
    stopBtn.disabled = false;
    trackBtn.disabled = nextMode === "live";
    if (nextMode === "live") {
      // Journey details once, for the operator / service line.
      fetch("/api/live", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: currentKey, mode: "journey" })
      }).then(function (r) { return r.json(); })
        .then(function (d) { if (d.journey) renderJourney(d.journey); })
        .catch(function () { /* journey is a bonus, not a blocker */ });
      timer = setInterval(poll, POLL_MS);
      startCountdown();
    }
    poll();
    document.getElementById("tracker").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function stopTracking(keepCard) {
    clearInterval(timer);
    clearInterval(countdownTimer);
    timer = null;
    countdownTimer = null;
    mode = "idle";
    currentKey = "";
    setBadge("Idle", "");
    stopBtn.disabled = true;
    trackBtn.disabled = false;
    if (!keepCard) {
      liveCard.classList.add("hidden");
      $("journey-line").classList.add("hidden");
    }
    $("countdown").textContent = "Polls every 20s, like the tracker page";
  }

  trackBtn.addEventListener("click", function () {
    var key = keyInput.value.trim();
    if (!key) { showError("Paste your Trackingo key first — or hit Demo to see it work with example data."); return; }
    clearError();
    startTracking("live", key);
  });

  demoBtn.addEventListener("click", function () {
    clearError();
    startTracking("demo", "");
  });

  document.getElementById("hero-demo").addEventListener("click", function () {
    clearError();
    startTracking("demo", "");
  });

  stopBtn.addEventListener("click", function () { stopTracking(false); });

  keyInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") trackBtn.click();
  });
})();
