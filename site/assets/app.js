// MASLD-Bench site: shared nav highlight + leaderboard renderer (no build step).
(function () {
  var page = document.body.dataset.page || "";
  document.querySelectorAll("nav.site a").forEach(function (a) {
    if (a.dataset.page === page) a.classList.add("on");
  });
})();

var FAMILY_ORDER = ["MB-20xx", "MB-85xx", "MB-86xx", "MB-87xx", "MB-88xx", "MB-89xx", "other"];

function familyOf(task) {
  for (var i = 0; i < FAMILY_ORDER.length; i++) {
    var f = FAMILY_ORDER[i];
    if (f !== "other" && task.indexOf(f.replace("xx", "")) === 0) return f;
  }
  var m = /^(MB-\d)xx/.exec(task) || /^(MB-\d)xx/.exec(task);
  return "other";
}

var state = { sortKey: null, sortDesc: true, family: "all", metric: "all", query: "" };

function fmt(v, digits) {
  if (v === null || v === undefined) return "—";
  if (Math.abs(v) >= 10000) return v.toExponential(2);
  return Number(v).toFixed(digits === undefined ? 3 : digits);
}

function renderTable() {
  var data = window.MASLD_DATA;
  if (!data) return;
  var fam = data.families || {};
  var rows = data.leaderboard.slice();
  var tbody = document.getElementById("lb-body");
  var count = document.getElementById("lb-count");
  if (!tbody) return;

  if (state.family !== "all") rows = rows.filter(function (r) { return familyOf(r.task) === state.family; });
  if (state.metric !== "all") rows = rows.filter(function (r) { return r.metric === state.metric; });
  if (state.query) {
    var q = state.query.toLowerCase();
    rows = rows.filter(function (r) {
      return r.model.toLowerCase().indexOf(q) >= 0 || r.task.toLowerCase().indexOf(q) >= 0;
    });
  }
  if (state.sortKey) {
    var k = state.sortKey, d = state.sortDesc ? -1 : 1;
    rows.sort(function (a, b) {
      var x = a[k], y = b[k];
      if (x === null && y === null) return 0;
      if (x === null) return 1; if (y === null) return -1;
      if (typeof x === "string") return x.localeCompare(y) * d;
      return (x - y) * d;
    });
  }
  count.textContent = rows.length + " of " + data.leaderboard.length + " rows";
  tbody.innerHTML = rows.map(function (r) {
    var fam = familyOf(r.task);
    var metricLabel = r.metric === "accuracy" ? "acc" : "MAE";
    var cell = r.metric === "accuracy"
      ? (r.value === null ? "—" : (r.value * 100).toFixed(1) + "%")
      : fmt(r.value, 2);
    return "<tr>" +
      "<td class='mono'>" + r.model + "</td>" +
      "<td class='mono'>" + r.task + "</td>" +
      "<td><span class='badge'>" + fam + "</span></td>" +
      "<td>" + metricLabel + "</td>" +
      "<td class='num'><b>" + cell + "</b></td>" +
      "<td class='num'>" + fmt(r.ci_lo, r.metric === "accuracy" ? 3 : 2) + " – " + fmt(r.ci_hi, r.metric === "accuracy" ? 3 : 2) + "</td>" +
      "<td class='num'>" + fmt(r.validity, 2) + "</td>" +
      "<td class='num'>" + fmt(r.rho, 2) + "</td>" +
      "<td class='num'>" + r.n + "</td>" +
      "</tr>";
  }).join("");
}

document.addEventListener("DOMContentLoaded", function () {
  var chips = document.getElementById("family-chips");
  var data = window.MASLD_DATA;
  if (chips && data) {
    var fams = Object.keys(data.families || {});
    var mk = function (label, key) {
      var b = document.createElement("button");
      b.className = "badge" + (key === state.family ? " acc" : "");
      b.textContent = label;
      b.style.cursor = "pointer";
      b.onclick = function () {
        state.family = key;
        chips.querySelectorAll("button").forEach(function (x) { x.classList.remove("acc"); });
        b.classList.add("acc");
        renderTable();
      };
      chips.appendChild(b);
    };
    mk("All families", "all");
    fams.forEach(function (f) { mk(f, f); });
  }
  var metric = document.getElementById("metric-filter");
  if (metric) metric.onchange = function () { state.metric = metric.value; renderTable(); };
  var search = document.getElementById("model-search");
  if (search) search.oninput = function () { state.query = search.value; renderTable(); };
  document.querySelectorAll("th[data-key]").forEach(function (th) {
    th.onclick = function () {
      var k = th.dataset.key;
      if (state.sortKey === k) state.sortDesc = !state.sortDesc;
      else { state.sortKey = k; state.sortDesc = true; }
      document.querySelectorAll("th").forEach(function (x) { x.classList.remove("sorted", "desc"); });
      th.classList.add("sorted");
      if (state.sortDesc) th.classList.add("desc");
      renderTable();
    };
  });
  renderTable();
});
