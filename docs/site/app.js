async function fetchText(url){
  const r = await fetch(url, {cache: 'no-store'});
  if(!r.ok) throw new Error(`fetch ${url} -> ${r.status}`);
  return await r.text();
}

function parseCSV(text){
  // Minimal CSV parser (assumes no embedded newlines, standard quoting is rare in our outputs)
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(',');
  const rows = [];
  for(let i=1;i<lines.length;i++){
    const cols = lines[i].split(',');
    const obj = {};
    headers.forEach((h, idx) => obj[h] = cols[idx]);
    rows.push(obj);
  }
  return {headers, rows};
}

function toNum(x){
  const v = Number(x);
  return Number.isFinite(v) ? v : null;
}

function fmt(n){
  if(n === null || n === undefined) return '';
  return new Intl.NumberFormat('en-US', {maximumFractionDigits: 0}).format(n);
}

function buildTable(el, headers, rows){
  const cols = [
    'year','fees_ada','inflow_fees_plus_reserves_ada','withdrawals_ada','treasury_delta_ada'
  ];
  const display = {
    year: 'Year',
    fees_ada: 'Fees (ADA)',
    inflow_fees_plus_reserves_ada: 'Est. Inflow (ADA)',
    withdrawals_ada: 'Withdrawals (ADA)',
    treasury_delta_ada: 'Treasury Δ (ADA)',
  };

  const thead = document.createElement('thead');
  const trh = document.createElement('tr');
  cols.forEach(c => {
    const th = document.createElement('th');
    th.textContent = display[c] || c;
    trh.appendChild(th);
  });
  thead.appendChild(trh);

  const tbody = document.createElement('tbody');
  rows.forEach(r => {
    const tr = document.createElement('tr');
    cols.forEach(c => {
      const td = document.createElement('td');
      if(c === 'year') td.textContent = r[c];
      else td.textContent = fmt(toNum(r[c]));
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  el.innerHTML = '';
  el.appendChild(thead);
  el.appendChild(tbody);
}

function plotYearly(rows){
  const year = rows.map(r => toNum(r.year));
  const fees = rows.map(r => toNum(r.fees_ada));
  const inflow = rows.map(r => toNum(r.inflow_fees_plus_reserves_ada));
  const delta = rows.map(r => toNum(r.treasury_delta_ada));
  const withdrawals = rows.map(r => toNum(r.withdrawals_ada));

  const layout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    margin: {l: 60, r: 20, t: 20, b: 50},
    xaxis: {title: 'Year', gridcolor: '#233044', color: '#9fb0c0'},
    yaxis: {title: 'ADA', gridcolor: '#233044', color: '#9fb0c0'},
    legend: {orientation: 'h', y: -0.25, font: {color:'#9fb0c0'}},
    font: {color: '#e6edf3'},
  };

  const data = [
    {x: year, y: fees, name: 'Fees', mode: 'lines+markers'},
    {x: year, y: inflow, name: 'Est. inflow', mode: 'lines+markers'},
    {x: year, y: withdrawals, name: 'Withdrawals', mode: 'lines+markers'},
    {x: year, y: delta, name: 'Treasury Δ', mode: 'lines+markers'},
  ];

  Plotly.newPlot('chart_yearly', data, layout, {displayModeBar: false, responsive: true});

  const layout2 = {
    ...layout,
    yaxis: {title:'ADA', gridcolor: '#233044', color: '#9fb0c0'},
  };
  const data2 = [
    {x: year, y: fees, name: 'Fees', type: 'bar'},
    {x: year, y: withdrawals, name: 'Withdrawals', type: 'bar'},
  ];
  Plotly.newPlot('chart_fees_withdrawals', data2, layout2, {displayModeBar: false, responsive: true});
}

async function main(){
  const status = document.getElementById('status');
  try{
    // GitHub Pages root will be /docs; this file is /docs/site.
    const csvText = await fetchText('../outputs/year_treasury_fees.csv');
    const {headers, rows} = parseCSV(csvText);

    // compute withdrawals column in-browser if not present
    const enriched = rows.map(r => {
      const mir = toNum(r.mir_treasury_payments_ada) || 0;
      const conway = toNum(r.conway_enacted_withdrawals_ada) || 0;
      r.withdrawals_ada = String(mir + conway);
      return r;
    });

    const years = enriched.map(r => r.year).filter(Boolean);
    status.textContent = `Loaded ${enriched.length} rows (years ${years[0]}–${years[years.length-1]}).`;

    plotYearly(enriched);
    buildTable(document.getElementById('table'), headers, enriched);
  }catch(e){
    status.textContent = `No data yet. Generate outputs/year_treasury_fees.csv first. (${e.message})`;
  }
}

main();
