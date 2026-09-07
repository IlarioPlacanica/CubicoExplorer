import bpy, math, os, json
from mathutils import Vector

OUT = os.path.dirname(os.path.abspath(__file__))
SRC = r'C:\Users\Ilario Placanica\Documents\Molassi\TEXTURE'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
asset=bpy.data.collections.new('Molassi_Edificio_46x15m')
scene.collection.children.link(asset)

def move(obj):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    asset.objects.link(obj)
    return obj

def mat(name, color, metallic=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=.72; bs.inputs['Metallic'].default_value=metallic
    return m

brick=mat('Laterizio fianco ricostruito',(.36,.105,.065))
stone=mat('Cornici e solette',(.55,.52,.44))
metal=mat('Ringhiere antracite',(.09,.12,.13),.65)
glass=mat('Vetro vani scala',(.19,.27,.29),.25)
roof=mat('Copertura in cotto',(.31,.105,.045))
nt=roof.node_tree; bs=nt.nodes.get('Principled BSDF')
tex=nt.nodes.new('ShaderNodeTexBrick'); tex.inputs['Color1'].default_value=(.39,.13,.055,1); tex.inputs['Color2'].default_value=(.22,.065,.025,1); tex.inputs['Mortar'].default_value=(.12,.07,.035,1)
tex.inputs['Scale'].default_value=1; tex.inputs['Brick Width'].default_value=.32; tex.inputs['Row Height'].default_value=.44; tex.inputs['Mortar Size'].default_value=.016
coord=nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(coord.outputs['Object'],tex.inputs['Vector']); nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
bump=nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.35; bump.inputs['Distance'].default_value=.035; nt.links.new(tex.outputs['Fac'],bump.inputs['Height']); nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])

def photo(name, fn):
    m=mat(name,(.5,.5,.5)); n=m.node_tree.nodes.new('ShaderNodeTexImage')
    n.image=bpy.data.images.load(os.path.join(SRC,fn)); n.image.pack(); n.extension='EXTEND'
    m.node_tree.links.new(n.outputs['Color'],m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    return m
front=photo('Fronte - otto livelli', 'fronte.png')
side=photo('Facciata destra - otto livelli','FacciataDx.png')
rear=photo('Retro fotografico','retro.png')

def mesh(name, verts, faces, material, uvs=None):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); asset.objects.link(ob); me.materials.append(material)
    if uvs:
        layer=me.uv_layers.new(name='UVMap')
        for poly,coords in zip(me.polygons,uvs):
            for li,uv in zip(poly.loop_indices,coords): layer.data[li].uv=uv
    return ob

def box(name, loc, scale, material):
    x,y,z=loc; a,b,c=[s/2 for s in scale]
    verts=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
    return mesh(name,verts,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material)

def wall(name,a,b,z0,z1,material,u0,u1,v0,v1):
    return mesh(name,[(a[0],a[1],z0),(b[0],b[1],z0),(b[0],b[1],z1),(a[0],a[1],z1)],[(0,1,2,3)],material,[[(u0,v0),(u1,v0),(u1,v1),(u0,v1)]])

# Footprint: front y=0, rear y=10; 12m-wide right wing extends to y=15.
poly=[(0,0),(46,0),(46,15),(34,15),(34,10),(0,10)]
mesh('Volume chiuso a L',[(x,y,z) for z in (0,30) for x,y in poly],[(5,4,3,2,1,0),(6,7,8,9,10,11)]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)],brick)

# Remap the six/seven source residential rows to eight actual rows, retaining ground + mezzanine.
def facade(name,a,b,material,crop,rows):
    u0,u1,vbottom,vbase,vtop=crop
    wall(name+' basamento',a,b,0,6,material,u0,u1,vbottom,vbase)
    for i in range(8):
        src=([0,1,2,2,3,3,4,5] if rows==6 else [0,1,2,3,3,4,5,6])[i]
        va=vbase+(vtop-vbase)*src/rows; vb=vbase+(vtop-vbase)*(src+1)/rows
        wall(name+' piano '+str(i+1),a,b,6+3*i,9+3*i,material,u0,u1,va,vb)

facade('Fronte',(0,-.015),(46,-.015),front,(.015,.986,.055,.345,.90),6)
facade('Destra',(46.015,0),(46.015,15),side,(.045,.953,.068,.301,.919),7)
# Back source includes 8 residential floors above a smaller base.
wall('Retro testata',(46,15.015),(34,15.015),0,30,rear,.028,.218,.012,.895)
wall('Retro arretrato',(34,10.015),(0,10.015),0,30,rear,.218,.984,.012,.895)
wall('Sinistra ricostruita',(-.015,10),(-.015,0),0,30,brick,0,1,0,1)

def balcony(name,x,y,z,width,depth,direction=1):
    box(name+' soletta',(x,y+direction*depth/2,z),(width,depth,.16),stone)
    fy=y+direction*depth
    box(name+' corrimano',(x,fy,z+1.04),(width,.055,.055),metal)
    for j in range(int(width/.22)+1):
        xx=x-width/2+j*width/int(width/.22)
        box(name+' montante',(xx,fy,z+.56),(.026,.026,.95),metal)
    for xx in (x-width/2,x+width/2):
        box(name+' ritorno',(xx,y+direction*depth/2,z+1.04),(.04,depth,.04),metal)
        box(name+' attacco',(xx,y,z+.56),(.03,.03,.95),metal)

for floor in range(8):
    z=6+floor*3+.25
    for j,t in enumerate((.050,.273,.343,.590,.663,.951)):
        balcony('Fronte balcone %d %d'%(floor,j),46*t,-.025,z,1.55,.55,-1)
    # Rear image balcony columns, evaluated in reverse world-X order.
    for j,u in enumerate((.25,.318,.405,.572,.651,.733,.902,.955)):
        x=34*(.984-u)/(.984-.218)
        if 0<x<34: balcony('Retro balcone %d %d'%(floor,j),x,10.04,3.3+floor*3.3,2.35,.85)
    # Windows on the 5m return inferred from aerial reference.
    box('Rientranza finestra '+str(floor),(33.97,12.2,7.3+3*floor),(.04,1.3,1.6),glass)

# Two projecting glazed stair towers with mapped original facades.
for j,(ua,ub) in enumerate(((.448,.54),(.768,.866))):
    xa=34*(.984-ub)/.766; xb=34*(.984-ua)/.766
    xc=(xa+xb)/2; w=xb-xa
    box('Vano scala '+str(j),(xc,10.85,16),(w,1.7,32),glass)
    wall('Vetrata scala '+str(j),(xb,11.71),(xa,11.71),0,32,rear,ua,ub,.014,.951)
    for k in range(9):
        box('Fascia scala',(xc,10.85,1+k*3.35),(w+.05,1.76,.20),stone)
    box('Copertura piana vano scala',(xc,10.85,32.15),(w+.35,2.1,.30),stone)

# Hip roof following the L outline; shared ridge branches toward the right wing.
e=[(-.35,-.35,30.15),(46.35,-.35,30.15),(46.35,15.35,30.15),(33.65,15.35,30.15),(33.65,10.35,30.15),(-.35,10.35,30.15)]
v=e+[(5,5,33),(40,5,33),(40,9.5,33)]
mesh('Tetto a padiglione a L',v,[(0,1,7,6),(5,0,6),(5,6,7,4),(4,7,8,3),(3,8,2),(2,8,7,1)],roof)
for i,a in enumerate(poly):
    b=poly[(i+1)%6]; mid=((a[0]+b[0])/2,(a[1]+b[1])/2,30.02)
    box('Cornicione',mid,(abs(a[0]-b[0])+.36 if a[0]!=b[0] else .36,abs(a[1]-b[1])+.36 if a[1]!=b[1] else .36,.25),stone)
for x in (4,10,17,25,32,40):
    box('Comignolo',(x,4.5,33.15),(.55,.7,1.2),stone)
    box('Cappello comignolo',(x,4.5,33.79),(.73,.87,.12),roof)

# Join by material to provide a practical low draw-call context asset.
for material in list(bpy.data.materials):
    obs=[o for o in asset.objects if o.type=='MESH' and len(o.data.materials)==1 and o.data.materials[0]==material]
    if not obs: continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]; bpy.ops.object.join(); obs[0].name='Molassi | '+material.name
root=bpy.data.objects.new('MOLASSI_ASSET',None); asset.objects.link(root)
root['dimensioni']='46m fronte; 15m profondita massima; gronda 30m; colmo 33m stimato'
root['rientranza']='Testata destra 12m; arretramento retro 5m'
root['piani_residenziali']=8
root['note']='Asset di contesto da immagini; lato sinistro e dettagli non documentati ricostruiti. Basamento fronte 6m stimato. Texture fronte/fianco rimappate su 8 livelli.'
for o in list(asset.objects):
    if o!=root:o.parent=root
root.asset_mark()

# Studio is separated from the reusable collection.
studio=bpy.data.collections.new('Anteprima - non esportare'); scene.collection.children.link(studio)
def studio_move(ob):
    for c in list(ob.users_collection):c.objects.unlink(ob)
    studio.objects.link(ob)
bpy.ops.object.camera_add(); camera=bpy.context.object; studio_move(camera); scene.camera=camera
camera.data.type='ORTHO'; camera.data.ortho_scale=66
def aim(loc):
    camera.location=loc; camera.rotation_euler=(Vector((23,6,15))-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.light_add(type='AREA',location=(12,-20,65)); key=bpy.context.object; studio_move(key); key.data.energy=4500; key.data.shape='DISK'; key.data.size=40
bpy.ops.object.light_add(type='SUN',location=(0,0,50)); sun=bpy.context.object; studio_move(sun); sun.rotation_euler=(.4,-.5,-.4); sun.data.energy=2
scene.world=bpy.data.worlds.new('Studio'); scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.45,.5,.6,1); scene.world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.render.resolution_x=1400; scene.render.resolution_y=1050; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
aim((85,-74,64))
bpy.ops.object.select_all(action='DESELECT')
for o in asset.objects:o.select_set(True)
bpy.context.view_layer.objects.active=root
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=75
            area.spaces.active.region_3d.view_location=(23,7,15)
            area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'Molassi_Edificio_Asset.blend'))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'Molassi_Edificio_Asset.glb'),use_selection=True,export_apply=True)
scene.render.filepath=os.path.join(OUT,'anteprima_fronte.png'); bpy.ops.render.render(write_still=True)
aim((88,80,66)); scene.render.filepath=os.path.join(OUT,'anteprima_retro.png'); bpy.ops.render.render(write_still=True)
stats={'mesh_objects':len([o for o in asset.objects if o.type=='MESH']),'polygons':sum(len(o.data.polygons) for o in asset.objects if o.type=='MESH'),'packed_images':[im.name for im in bpy.data.images if im.packed_file]}
with open(os.path.join(OUT,'verifica.json'),'w') as f:json.dump(stats,f,indent=2)
print('ASSET_COMPLETE',stats)
