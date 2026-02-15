export async function fetchText(url){
  const r = await fetch(url, {cache:'no-store'});
  if(!r.ok) throw new Error(`fetch ${url} -> ${r.status}`);
  return await r.text();
}

export function parseCSV(text){
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(',');
  const rows=[];
  for(let i=1;i<lines.length;i++){
    const cols = lines[i].split(',');
    const obj={};
    headers.forEach((h,idx)=>obj[h]=cols[idx]);
    rows.push(obj);
  }
  return {headers, rows};
}

export function toNum(x){
  const v=Number(x);
  return Number.isFinite(v)?v:null;
}

export function fmtAda(n){
  if(n===null||n===undefined) return '—';
  const abs=Math.abs(n);
  if(abs>=1e9) return `₳${(n/1e9).toFixed(2)}B`;
  if(abs>=1e6) return `₳${(n/1e6).toFixed(2)}M`;
  if(abs>=1e3) return `₳${(n/1e3).toFixed(1)}K`;
  return `₳${n.toFixed(2)}`;
}

export function fmt(n){
  if(n===null||n===undefined) return '—';
  return new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(n);
}

export function renderTable(el, rows, columns, maxRows=50){
  if(!el) return;
  if(!rows || rows.length===0){ el.innerHTML=''; return; }
  const cols = columns || Object.keys(rows[0]);
  const thead = `<thead><tr>${cols.map(c=>`<th>${c}</th>`).join('')}</tr></thead>`;
  const body = rows.slice(0,maxRows).map(r=>`<tr>${cols.map(c=>`<td>${r[c]??''}</td>`).join('')}</tr>`).join('');
  el.innerHTML = thead + `<tbody>${body}</tbody>`;
}
