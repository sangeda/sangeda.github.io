#!/usr/bin/env python3
"""One-off conversion: pyshp, shapely and pyproj required. Source ZIP is not modified."""
import hashlib,io,json,sys,zipfile
from pathlib import Path
import shapefile
from shapely import make_valid
from shapely.geometry import shape,mapping,Polygon,MultiPolygon
from pyproj import CRS
source=Path(sys.argv[1]);dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
z=zipfile.ZipFile(source);bases=[n[:-4] for n in z.namelist() if n.endswith('.shp')]
assert len(bases)==1
base=bases[0];assert CRS.from_wkt(z.read(base+'.prj').decode()).equals(CRS.from_epsg(4326),ignore_axis_order=True)
r=shapefile.Reader(shp=io.BytesIO(z.read(base+'.shp')),shx=io.BytesIO(z.read(base+'.shx')),dbf=io.BytesIO(z.read(base+'.dbf')))
features=[];repairs=[]
for sr in r.iterShapeRecords():
 p=sr.record.as_dict();g=shape(sr.shape.__geo_interface__);oldarea=g.area
 if not g.is_valid:
  g=make_valid(g)
  if g.geom_type=='GeometryCollection':g=MultiPolygon([part for part in g.geoms if isinstance(part,Polygon)])
  repairs.append(dict(region=p['ADM1_EN'],relative_area_change=abs(g.area-oldarea)/oldarea))
 # Preserve every region and multipart island; tolerance is degrees, for display only.
 g=g.simplify(.004,preserve_topology=True)
 rounded=shape(json.loads(json.dumps(mapping(g)),parse_float=lambda x:round(float(x),5)))
 if rounded.is_valid and not rounded.is_empty:g=rounded
 assert g.is_valid and not g.is_empty and g.geom_type in ('Polygon','MultiPolygon')
 name=p['ADM1_EN'];name='Dar es Salaam' if name=='Dar-es-salaam' else name
 features.append(dict(type='Feature',properties=dict(name=name,source_name=p['ADM1_EN'],pcode=p['ADM1_PCODE']),geometry=mapping(g)))
assert len(features)==31 and len({f['properties']['pcode'] for f in features})==31
result=dict(type='FeatureCollection',features=features)
(dest/'tanzania-regions.geojson').write_text(json.dumps(result,separators=(',',':')))
manifest=dict(source_file=Path(base).name,source_zip_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),boundary_date='2018-10-19',coordinate_reference_system='EPSG:4326',regions=len(features),geometry_repairs=repairs,simplification_tolerance_degrees=.004,source_description='User-supplied shapefile; accompanying ArcGIS XML records OCHA FIS processing on 19 October 2018.',licence='Matching HDX COD-AB Tanzania dataset: Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO)',source_url='https://data.humdata.org/dataset/cod-ab-tza',name_crosswalk={'Dar-es-salaam':'Dar es Salaam'},use='Regional applicant counts; not individual locations. Historical boundary reference, not a claim of current legal boundaries.')
(dest/'provenance.json').write_text(json.dumps(manifest,indent=2))
print('Validated regions',len(features),'repairs',repairs,'GeoJSON bytes',(dest/'tanzania-regions.geojson').stat().st_size)
