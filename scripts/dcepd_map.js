/* Applicant geography only. No individual coordinates or remote map services. */
(()=>{
const host=document.getElementById('tz-map'),node=document.getElementById('map-boundaries');
if(!host||!node)return;
const geo=JSON.parse(node.textContent),data=JSON.parse(document.getElementById('dashboard-data').textContent);
const counts=new Map(data.geography.map(r=>[r.location,r.applications]));
const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
svg.setAttribute('viewBox','0 0 820 820');svg.setAttribute('role','group');svg.setAttribute('aria-label','Tanzania regions coloured by published application count');
const title=document.createElementNS(ns,'title');title.textContent='Applicant residence by Tanzania region';svg.append(title);
// Equirectangular display adjusted to Tanzania's central latitude; source is EPSG:4326.
const project=([lon,lat])=>[35+(lon-29.5)*67.5*Math.cos(6.4*Math.PI/180),40+(-.9-lat)*67.5];
const bins=[{label:'5–9',max:9,color:'#d8ede7'},{label:'10–24',max:24,color:'#9acdbd'},{label:'25–49',max:49,color:'#4fa991'},{label:'50–99',max:99,color:'#167c70'},{label:'100+',max:Infinity,color:'#074a50'}];
let mapped=0,regions=0;
for(const f of geo.features){
 const name=f.properties.name,n=counts.get(name),known=Number.isInteger(n),path=document.createElementNS(ns,'path');
 const polys=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;
 const d=polys.flatMap(poly=>poly.map(ring=>ring.map((pt,i)=>{const [x,y]=project(pt);return (i?'L':'M')+x.toFixed(2)+','+y.toFixed(2)}).join('')+'Z')).join('');
 const label=name+': '+(known?n.toLocaleString()+' application records':'no separately published regional count (not zero)');
 path.setAttribute('d',d);path.setAttribute('fill',known?(bins.find(b=>n<=b.max)||bins.at(-1)).color:'#e2e5e5');path.setAttribute('fill-rule','evenodd');path.setAttribute('stroke','#557778');path.setAttribute('stroke-width','.65');path.setAttribute('tabindex','0');path.setAttribute('role','img');path.setAttribute('aria-label',label);
 const tip=document.createElementNS(ns,'title');tip.textContent=label;path.append(tip);
 const select=()=>{document.getElementById('map-selection').textContent=label};path.addEventListener('click',select);path.addEventListener('focus',select);path.addEventListener('mouseenter',select);svg.append(path);
 if(known){mapped+=n;regions++}
}
host.replaceChildren(svg);
const legend=document.getElementById('map-legend');for(const b of [...bins,{label:'No separately published count',color:'#e2e5e5'}]){const span=document.createElement('span'),swatch=document.createElement('i');swatch.className='swatch';swatch.style.background=b.color;span.append(swatch,document.createTextNode(b.label));legend.append(span)}
const names=new Set(geo.features.map(f=>f.properties.name));const off=data.geography.filter(r=>!names.has(r.location)).map(r=>r.location);
document.getElementById('map-coverage').textContent=`${mapped.toLocaleString()} applications mapped to ${regions} regions with published counts. Not assigned to regional polygons: ${off.join(', ')||'none'}. Grey also covers small counts withheld from the public output and regions without a separate application-form choice; it must not be interpreted as zero demand.`;
})();
