/* Minimal dashboard: Treasury amount (on-chain) + Catalyst (off-chain) */

async function fetchText(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`fetch ${url} -> ${r.status}`);
  return await r.text();
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(',');
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',');
    const obj = {};
    headers.forEach((h, idx) => (obj[h] = cols[idx]));
    rows.push(obj);
  }
  return { headers, rows };
}

function toNum(x) {
  const v = Number(x);
  return Number.isFinite(v) ? v : null;
}

function fmt(n) {
  if (n === null || n === undefined) return '';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n);
}

function buildTable(el, cols, display, rows) {
  const thead = document.createElement('thead');
  const trh = document.createElement('tr');
  cols.forEach((c) => {
    const th = document.createElement('th');
    th.textContent = display[c] || c;
    trh.appendChild(th);
  });
  thead.appendChild(trh);

  const tbody = document.createElement('tbody');
  rows.forEach((r) => {
    const tr = document.createElement('tr');
    cols.forEach((c) => {
      const td = document.createElement('td');
      const raw = c === 'name' || c === 'username' ? r[c] : toNum(r[c]);
      td.textContent = typeof raw === 'number' ? fmt(raw) : (raw || '');
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  el.innerHTML = '';
  el.appendChild(thead);
  el.appendChild(tbody);
}

async function main() {
  const status = document.getElementById('status');

  // Status (optional)
  try {
    const meta = JSON.parse(await fetchText('outputs/status.json'));
    status.innerHTML = `<strong>${meta.network_name || 'unknown'}</strong> · tip: ${meta.tip_time || 'unknown'} · generated: ${meta.generated_at_utc || 'unknown'}`;
  } catch (e) {
    status.textContent = 'No status.json yet.';
  }

  // Treasury amount chart
  try {
    const epochText = await fetchText('outputs/epoch_treasury_fees.csv');
    const { rows } = parseCSV(epochText);
    const x = rows.map((r) => toNum(r.epoch_no));
    const y = rows.map((r) => toNum(r.treasury_end_ada));
    const rsv = rows.map((r) => toNum(r.reserves_start_ada));

    Plotly.newPlot('chart_treasury', [
      { x, y, name: 'Treasury (ADA)', mode: 'lines', line: { color: '#34d399', width: 2 } },
      // Reserves are much larger; put on secondary axis so both are readable.
      { x, y: rsv, name: 'Reserves (ADA)', mode: 'lines', yaxis: 'y2', line: { color: '#60a5fa', width: 2 } },
    ], {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      margin: { l: 70, r: 70, t: 10, b: 50 },
      xaxis: { title: 'Epoch', gridcolor: '#233044', color: '#9fb0c0' },
      yaxis: { title: 'Treasury (ADA)', gridcolor: '#233044', color: '#9fb0c0' },
      yaxis2: { title: 'Reserves (ADA)', overlaying: 'y', side: 'right', gridcolor: 'rgba(0,0,0,0)', color: '#9fb0c0' },
      legend: { orientation: 'h', y: -0.22, font: { color: '#9fb0c0', size: 11 } },
      font: { color: '#e6edf3' },
    }, { displayModeBar: false, responsive: true });
  } catch (e) {
    // leave blank
  }

  // Catalyst summary + table
  try {
    const sum = JSON.parse(await fetchText('outputs/offchain/catalyst/summary.json'));
    const el = document.getElementById('catalyst-summary');
    const c = sum.counts || {};
    const t = sum.totals_usd || {};
    el.innerHTML = `proposers: ${fmt(c.proposers_total)} · funded: ${fmt(c.proposers_with_funded_projects)} · completed: ${fmt(c.proposers_with_completed_projects)}<br>` +
      `distributed (USD): ${fmt(t.distributed_usd)} · remaining (USD): ${fmt(t.remaining_usd)} · requested (USD): ${fmt(t.requested_usd)}<br>` +
      `scraped: ${sum.generated_at_utc || 'unknown'}`;

    const topText = await fetchText('outputs/offchain/catalyst/top_recipients.csv');
    const top = parseCSV(topText).rows;
    buildTable(
      document.getElementById('table-catalyst-top'),
      ['name', 'username', 'total_distributed_usd', 'funded_projects', 'completed_projects'],
      {
        name: 'Name',
        username: 'Handle',
        total_distributed_usd: 'Distributed (USD)',
        funded_projects: 'Funded',
        completed_projects: 'Completed',
      },
      top
    );
  } catch (e) {
    const el = document.getElementById('catalyst-summary');
    if (el) el.textContent = 'No Catalyst data published yet.';
  }
}

main();
