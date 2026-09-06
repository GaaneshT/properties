"""Conservative floor navigation raster from native floor zones and object footprints."""
import json, math
from pathlib import Path
from mathutils import Vector
from connect_house_floor import connected_floor

def inside(x,y,polygon):
    hit=False
    for i,(ax,ay) in enumerate(polygon):
        bx,by=polygon[i-1]
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:hit=not hit
    return hit

def hull(points):
    points=sorted(set(points))
    if len(points)<3:return points
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for p in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]

def write_navigation(scene,repo,destination):
    floors=json.loads((repo.parent/'Carissa_Park_Native/data/rooms.json').read_text())
    polygons=[[(x,-y) for x,y in room['model_polygon']] for room in floors if room['id'] not in {'AC_LEDGE','BIN'}]
    origin=[min(x for p in polygons for x,y in p)-.2,min(y for p in polygons for x,y in p)-.2]
    end=[max(x for p in polygons for x,y in p)+.2,max(y for p in polygons for x,y in p)+.2]
    cell=.065;width=math.ceil((end[0]-origin[0])/cell);height=math.ceil((end[1]-origin[1])/cell)
    raw=[bytearray(width) for _ in range(height)]
    for z in range(height):
        for x in range(width):
            px=origin[0]+(x+.5)*cell;pz=origin[1]+(z+.5)*cell
            raw[z][x]=any(inside(px,pz,p) for p in polygons)
    blockers=0
    for obj in scene.objects:
        if obj.type not in {'MESH','CURVE'} or obj.hide_render:continue
        if any(c.name.startswith(('EXTERIOR_GENERIC_CONTEXT','PRESENTATION_','REFERENCE_','OPTION_','ARCH_CURTAINS')) for c in obj.users_collection):continue
        if any(term in obj.name.lower() for term in ['curtain','rug','grout','joint_','skirt','leaf','stem','downlight','art_']):continue
        points=[obj.matrix_world @ Vector(p) for p in obj.bound_box]
        lo=min(p.z for p in points);hi=max(p.z for p in points)
        if hi<.22 or lo>1.65:continue
        polygon=hull([(float(p.x),float(-p.y)) for p in points])
        if len(polygon)<3:continue
        xmin=max(0,int((min(x for x,z in polygon)-origin[0])/cell));xmax=min(width-1,math.ceil((max(x for x,z in polygon)-origin[0])/cell))
        zmin=max(0,int((min(z for x,z in polygon)-origin[1])/cell));zmax=min(height-1,math.ceil((max(z for x,z in polygon)-origin[1])/cell))
        for z in range(zmin,zmax+1):
            for x in range(xmin,xmax+1):
                if raw[z][x] and inside(origin[0]+(x+.5)*cell,origin[1]+(z+.5)*cell,polygon):raw[z][x]=0
        blockers+=1
    # A small body radius prevents wall penetration; nearby blocked cells include the outside boundary.
    radius=.13;pad=math.ceil(radius/cell)
    offsets=[(x,z) for z in range(-pad,pad+1) for x in range(-pad,pad+1) if x*x+z*z<=(radius/cell)**2]
    rows=[]
    for z in range(height):
        rows.append(''.join('1' if raw[z][x] and all(0<=x+dx<width and 0<=z+dz<height and raw[z+dz][x+dx] for dx,dz in offsets) else '0' for x in range(width)))
    rows=connected_floor(rows)
    data=dict(origin=origin,cell=cell,width=width,height=height,rows=rows,eyeHeight=1.62,bodyRadius=radius,blockerCount=blockers,connectedFloorOnly=True,
              note='Conservative navigation approximation of the concept; floor zones and native object bounds, no site dimensions inferred.')
    destination.write_text(json.dumps(data,separators=(',',':')))
    print(f'WALK_GRID: {width}x{height}, {sum(r.count("1") for r in rows)} walkable cells, {blockers} obstacle footprints')
