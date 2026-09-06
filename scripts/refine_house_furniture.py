"""Small presentation refinements to copied textile meshes; no architecture or placements change."""
import math

def refine_furniture(scene):
    changed=[]
    for obj in scene.objects:
        if obj.type!='MESH':continue
        cloth=any(part in obj.name for part in ['Duvet_with_drape','Foot_throw_woven'])
        cushion=any(part in obj.name for part in ['Pillow_soft_volume','Pillow_linen_accent','Sofa_decorative_pillow','Sofa_loose_back','Sofa_separate_seat'])
        if not cloth and not cushion:continue
        obj.data=obj.data.copy()
        vertices=obj.data.vertices
        xmin=min(v.co.x for v in vertices);xmax=max(v.co.x for v in vertices)
        ymin=min(v.co.y for v in vertices);ymax=max(v.co.y for v in vertices)
        phase=sum(ord(c) for c in obj.name)*.113
        for vertex in vertices:
            x=vertex.co.x;y=vertex.co.y;z=vertex.co.z
            if cloth:
                # Both overlapping cloth layers use the same continuous displacement field.
                # Independent waves can push the duvet through the foot throw.
                wave=.009*math.sin(30*x+4*math.sin(6*y))+.004*math.sin(22*y+8*x)+.002*math.sin(50*x-25*y)
                vertex.co.z+=wave
            else:
                # Millimetre-scale fabric compression leaves welt seams and silhouettes intact.
                ripple=.0032*math.sin(43*x+19*y+phase)*math.sin(31*z+11*y)+.0017*math.sin(79*x-29*y+17*z)
                vertex.co+=vertex.normal*ripple
        obj.data.update()
        obj['web_furniture_refinement']='Subtle drape folds and upholstery compression; original placement and dimensions retained within 20 mm'
        changed.append(obj.name)
    return changed
