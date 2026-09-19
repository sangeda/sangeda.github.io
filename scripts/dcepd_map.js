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
// Ordered Viridis colours: increasing count moves from purple through blue/green to yellow.
// Count boundaries stay readable; additional bands are added when the largest count grows.
const mappedValues=geo.features.map(f=>counts.get(f.properties.name)).filter(n=>Number.isInteger(n)&&n>=0);
const maximum=Math.max(...mappedValues,5), minimum=Math.min(...mappedValues,5);
const edges=[0,1,5];
for(let power=1;edges.at(-1)<=maximum;power*=10){
 for(const factor of [10,25,50]){const edge=factor*power;if(edge>edges.at(-1))edges.push(edge)}
}
const active=edges.filter((edge,i)=>edge<=maximum || (i>0&&edges[i-1]<=maximum)).filter(edge=>edge>=(minimum>=5?5:0));
const palette=['#440154','#482878','#3e4989','#31688e','#26828e','#1f9e89','#35b779','#6ece58','#b5de2b','#fde725'];
const colourAt=t=>{
 const p=t*(palette.length-1),a=Math.floor(p),b=Math.min(a+1,palette.length-1),weight=p-a;
 const channel=(hex,start)=>parseInt(hex.slice(start,start+2),16);
 return '#'+[1,3,5].map(start=>Math.round(channel(palette[a],start)*(1-weight)+channel(palette[b],start)*weight).toString(16).padStart(2,'0')).join('');
};
const bins=active.slice(0,-1).map((lower,i)=>({
 label:lower===active[i+1]-1?lower.toLocaleString():lower.toLocaleString()+'–'+(active[i+1]-1).toLocaleString(),
 max:active[i+1]-1,
 color:colourAt(i/Math.max(active.length-2,1))
}));
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
document.getElementById('map-coverage').textContent=`${mapped.toLocaleString()} applications mapped to ${regions} regions with published counts. Not assigned to regional polygons: ${off.join(', ')||'none'}. The colour scale expands with the largest regional count; compare counts and legend ranges across snapshots. Grey also covers small counts withheld from the public output and regions without a separate application-form choice; it must not be interpreted as zero demand.`;
})();
