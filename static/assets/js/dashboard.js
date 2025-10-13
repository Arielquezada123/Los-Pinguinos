(function () {
  var canvas = document.getElementById('Chart1');
  if (!canvas || typeof Chart === 'undefined') return;
  var ctx = canvas.getContext('2d');
  var labels = canvas.dataset.labels ? JSON.parse(canvas.dataset.labels) : [];
  var values = canvas.dataset.values ? JSON.parse(canvas.dataset.values) : [];
  new Chart(ctx, {
    type: 'line',
    data: { labels: labels, datasets: [{ label: 'Uso de Agua (m³)', backgroundColor: 'rgba(37,99,235,0.1)', borderColor: '#2563eb', data: values, pointBackgroundColor: '#2563eb', pointHoverBackgroundColor: '#1d4ed8', pointBorderColor: '#1e2a3a', pointHoverBorderColor: '#2563eb', pointHoverBorderWidth: 3, borderWidth: 3, pointRadius: 6, pointHoverRadius: 8, fill: true }] },
    options: { plugins: { legend: { display: false }, tooltip: { backgroundColor: '#1e2a3a', titleColor: '#e0e8f0', bodyColor: '#e0e8f0', borderColor: '#2a3441', borderWidth: 1 } }, responsive: true, maintainAspectRatio: false, scales: { y: { grid: { display: true, drawTicks: false, drawBorder: false, color: 'rgba(42,52,65,0.3)' }, ticks: { padding: 35, suggestedMax: 1200, suggestedMin: 500, color: '#a0aec0' } }, x: { grid: { drawBorder: false, color: 'rgba(42,52,65,0.3)' }, ticks: { padding: 20, color: '#a0aec0' } } } }
  });
})();

