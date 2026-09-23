(function () {
  'use strict';

  var root = document.getElementById('analytics-dashboard');
  if (!root) return;

  var tabs = Array.prototype.slice.call(root.querySelectorAll('[data-analytics-tab]'));
  var panels = Array.prototype.slice.call(root.querySelectorAll('.analytics-tab-panel'));
  var validIds = tabs.map(function (tab) { return tab.dataset.analyticsTab; });

  function activate(id, focus) {
    if (validIds.indexOf(id) < 0) id = 'resumen';
    tabs.forEach(function (tab) {
      if (tab.dataset.analyticsTab === id) tab.setAttribute('aria-current', 'page');
      else tab.removeAttribute('aria-current');
      if (focus && tab.dataset.analyticsTab === id) tab.focus();
    });
    panels.forEach(function (panel) { panel.hidden = panel.id !== id; });
  }

  if (tabs.length && panels.length) {
    activate(location.hash.substring(1));
    function showTab(id, focus) {
      if (location.hash !== '#' + id) history.pushState(null, '', '#' + id);
      activate(id, focus);
    }
    tabs.forEach(function (tab, index) {
      tab.addEventListener('click', function (event) {
        event.preventDefault();
        showTab(tab.dataset.analyticsTab);
      });
      tab.addEventListener('keydown', function (event) {
        var target;
        if (event.key === 'ArrowRight') target = tabs[(index + 1) % tabs.length];
        else if (event.key === 'ArrowLeft') target = tabs[(index + tabs.length - 1) % tabs.length];
        else if (event.key === 'Home') target = tabs[0];
        else if (event.key === 'End') target = tabs[tabs.length - 1];
        if (!target) return;
        event.preventDefault();
        showTab(target.dataset.analyticsTab, true);
      });
    });
    root.querySelectorAll('[data-jump-tab]').forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
        showTab(link.dataset.jumpTab);
        root.querySelector('.analytics-tabs').scrollIntoView({ block: 'start' });
      });
    });
    window.addEventListener('hashchange', function () { activate(location.hash.substring(1)); });
    window.addEventListener('popstate', function () { activate(location.hash.substring(1)); });
  }

  root.querySelectorAll('[data-analytics-table]').forEach(function (table) {
    var name = table.dataset.analyticsTable;
    var body = table.tBodies[0];
    if (!body) return;
    var rows = Array.prototype.slice.call(body.rows).filter(function (row) {
      return !row.classList.contains('analytics-empty-row');
    });
    var search = root.querySelector('[data-table-search="' + name + '"]');
    var empty = root.querySelector('[data-empty-for="' + name + '"]');
    var collator = new Intl.Collator('es', { sensitivity: 'base', numeric: true });

    function applySearch() {
      if (!search) return;
      var query = search.value.trim().toLocaleLowerCase('es');
      var visible = 0;
      rows.forEach(function (row) {
        var searchable = Array.prototype.slice.call(row.cells, 0, 2)
          .map(function (cell) { return cell.textContent; }).join(' ');
        var matched = !query || searchable.toLocaleLowerCase('es').indexOf(query) !== -1;
        row.hidden = !matched;
        if (matched) visible += 1;
      });
      if (empty) empty.hidden = visible > 0 || rows.length === 0;
    }
    if (search) search.addEventListener('input', applySearch);

    Array.prototype.slice.call(table.tHead.rows[0].cells).forEach(function (header, column) {
      var button = header.querySelector('[data-sort]');
      if (!button) return;
      button.addEventListener('click', function () {
        var ascending = header.getAttribute('aria-sort') !== 'ascending';
        Array.prototype.slice.call(table.tHead.rows[0].cells).forEach(function (cell) {
          cell.removeAttribute('aria-sort');
        });
        header.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
        rows.sort(function (a, b) {
          var left = a.cells[column].dataset.sortValue || a.cells[column].textContent.trim();
          var right = b.cells[column].dataset.sortValue || b.cells[column].textContent.trim();
          var result = button.dataset.sort === 'number'
            ? (Number(left) || 0) - (Number(right) || 0)
            : collator.compare(left, right);
          return ascending ? result : -result;
        });
        rows.forEach(function (row) { body.appendChild(row); });
      });
    });
  });

  var svg = root.querySelector('[data-trend-chart]');
  var chartRows = Array.prototype.slice.call(root.querySelectorAll('[data-chart-row]'));
  if (!svg || !chartRows.length) return;
  var invoiceLine = svg.querySelector('.analytics-series-invoice');
  var paymentLine = svg.querySelector('.analytics-series-payment');
  if (!invoiceLine || !paymentLine) return;
  var invoicePoints = invoiceLine.points;
  var paymentPoints = paymentLine.points;
  if (!invoicePoints || !paymentPoints || !invoicePoints.numberOfItems) return;
  var count = Math.min(chartRows.length, invoicePoints.numberOfItems, paymentPoints.numberOfItems);
  var crosshair = svg.querySelector('.analytics-chart-crosshair');
  var invoiceDot = svg.querySelector('.analytics-chart-dot-invoice');
  var paymentDot = svg.querySelector('.analytics-chart-dot-payment');
  var dayLabel = root.querySelector('[data-chart-day]');
  var invoiceLabel = root.querySelector('[data-chart-invoice]');
  var paymentLabel = root.querySelector('[data-chart-payment]');
  var money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 2 });
  var selectedIndex = -1;

  function show(index) {
    if (index < 0 || index >= count) return;
    selectedIndex = index;
    var invoice = invoicePoints.getItem(index);
    var payment = paymentPoints.getItem(index);
    var row = chartRows[index];
    crosshair.setAttribute('x1', invoice.x);
    crosshair.setAttribute('x2', invoice.x);
    invoiceDot.setAttribute('cx', invoice.x);
    invoiceDot.setAttribute('cy', invoice.y);
    paymentDot.setAttribute('cx', payment.x);
    paymentDot.setAttribute('cy', payment.y);
    crosshair.removeAttribute('hidden');
    invoiceDot.removeAttribute('hidden');
    paymentDot.removeAttribute('hidden');
    dayLabel.textContent = row.dataset.day;
    invoiceLabel.textContent = money.format(Number(row.dataset.invoice) || 0);
    paymentLabel.textContent = money.format(Number(row.dataset.payment) || 0);
  }

  function svgX(clientX) {
    var point = svg.createSVGPoint();
    point.x = clientX;
    point.y = 0;
    var matrix = svg.getScreenCTM();
    return matrix ? point.matrixTransform(matrix.inverse()).x : null;
  }
  svg.addEventListener('pointermove', function (event) {
    var x = svgX(event.clientX);
    if (x === null) return;
    var nearest = 0;
    var distance = Infinity;
    for (var i = 0; i < count; i += 1) {
      var next = Math.abs(invoicePoints.getItem(i).x - x);
      if (next < distance) { distance = next; nearest = i; }
    }
    show(nearest);
  });
  svg.addEventListener('keydown', function (event) {
    var target = null;
    if (event.key === 'ArrowRight') target = Math.min(count - 1, selectedIndex + 1);
    else if (event.key === 'ArrowLeft') target = Math.max(0, selectedIndex - 1);
    else if (event.key === 'Home') target = 0;
    else if (event.key === 'End') target = count - 1;
    if (target === null) return;
    event.preventDefault();
    show(target);
  });
})();
