(function(){const box=()=>document.querySelector("#exclude-flagged");let data=null;
const esc=t=>String(t).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function render(){const d=data;const ex=!!(box()&&box().checked);const r=d.reporting;const label=ex?" (excluding flagged)":"";let cards;
if(r){const fys=r.fiscal_years.slice(-10).map(x=>({k:x.fiscal_year.replace(/^FY/,"")+(x.partial?"*":""),n:ex?x.publications_excluding_flagged:x.publications}));
const partialNote=r.fiscal_years.some(x=>x.partial)?`<p class="table-note">* Current fiscal year, to date.</p>`:"";
const max=Math.max(...fys.map(x=>x.n),1);
const bars=fys.map(x=>`<div class="mini-bar-row"><span>${esc(x.k)}</span><i style="width:${100*x.n/max}%"></i><strong>${x.n}</strong></div>`).join("");
const qs=r.quarters.map(x=>`<tr><td title="${esc(x.period_start)} to ${esc(x.period_end)}">${esc(x.fiscal_year.replace(/^FY/,""))} ${esc(x.fiscal_quarter)}${x.partial?"*":""}</td><td>${ex?x.published_excluding_flagged:x.published}</td><td>${(ex?x.added_excluding_flagged:x.added)??"—"}</td></tr>`).join("");
const note=`<p class="table-note">Q1 Jul–Sep, Q2 Oct–Dec, Q3 Jan–Mar, Q4 Apr–Jun.${r.quarters.some(x=>x.partial)?" * To date.":""}${r.quarters.some(x=>x.added===null)&&r.added_date_note?" — "+esc(r.added_date_note):""}</p>`;
const topics=r.top_topics.slice(0,10).map(x=>`<li><span>${esc(x.topic)}</span><strong>${x.publications}</strong></li>`).join("");
cards=`<article class="observatory-card"><h3>Output by fiscal year${label}</h3><div class="mini-bars fy">${bars}</div>${partialNote}</article><article class="observatory-card"><h3>Latest fiscal quarters${label}</h3><table><thead><tr><th>Quarter</th><th>Published</th><th>Added to OpenAlex</th></tr></thead><tbody>${qs}</tbody></table>${note}</article><article class="observatory-card"><h3>Leading OpenAlex topics, ${esc(r.topics_fiscal_year)}</h3><ol class="topic-rank">${topics}</ol></article>`;}
else{const annualAll=ex&&d.annual_excluding_flagged?d.annual_excluding_flagged:d.annual;const quartersAll=ex&&d.quarters_excluding_flagged?d.quarters_excluding_flagged:d.quarters;
const recent=annualAll.filter(x=>x.publication_year>=2016).slice(-10);const max=Math.max(...recent.map(x=>x.publications),1);
const annual=recent.map(x=>`<div class="mini-bar-row"><span>${x.publication_year}</span><i style="width:${100*x.publications/max}%"></i><strong>${x.publications}</strong></div>`).join("");
const qs=quartersAll.slice(-8).reverse().map(x=>`<tr><td>${esc(x.fiscal_year)}</td><td>${esc(x.fiscal_quarter)}</td><td>${esc(x.period_end)}</td><td>${x.publications}</td></tr>`).join("");
const topics=d.top_topics.slice(0,10).map(x=>`<li><span>${esc(x.topic)}</span><strong>${x.publications}</strong></li>`).join("");
cards=`<article class="observatory-card"><h3>Recent annual output${label}</h3><div class="mini-bars">${annual}</div></article><article class="observatory-card"><h3>Latest fiscal quarters${label}</h3><table><thead><tr><th>FY</th><th>Quarter</th><th>Ends</th><th>Works</th></tr></thead><tbody>${qs}</tbody></table></article><article class="observatory-card"><h3>Leading OpenAlex topics</h3><ol class="topic-rank">${topics}</ol></article>`;}
document.querySelector("#muhas-summary").innerHTML=cards;}
fetch("data/summary.json").then(r=>r.json()).then(d=>{data=d;render();if(box())box().addEventListener("change",render);}).catch(()=>{document.querySelector("#muhas-summary").textContent="Summary data are temporarily unavailable.";});})();