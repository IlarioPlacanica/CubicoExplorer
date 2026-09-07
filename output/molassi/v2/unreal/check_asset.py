import bpy, os, json, struct
from mathutils import Vector
out=os.path.dirname(os.path.abspath(__file__))
c=bpy.data.collections['MOLASSI_UNREAL']; root=bpy.data.objects['MOLASSI_UNREAL_ROOT']
triangles=0; meshes=[]
for o in c.objects:
    if o.type=='MESH':
        o.data.calc_loop_triangles(); triangles+=len(o.data.loop_triangles); meshes.append(o)
assert root['sporgenza_aggetti_m']==1.0
assert root['quota_fascia_pietra']==3.2 and root['quota_inizio_residenziale']==6.0
assert root['piani_residenziali']==8
assert all(i.packed_file for i in bpy.data.images if i.name in ['laterizio.png','pietra_grigia.png','tegole.png','ringhiera_RGBA.png'])
assert len(meshes)==14
with open(os.path.join(out,'Molassi_Unreal.glb'),'rb') as f:
    magic,version,length=struct.unpack('<III',f.read(12)); size,kind=struct.unpack('<II',f.read(8)); gltf=json.loads(f.read(size))
rail=[m for m in gltf['materials'] if m['name'].startswith('Ringhiera mascherata')][0]
assert rail.get('alphaMode')=='MASK',rail
assert all('normalTexture' in m for m in gltf['materials'] if m['name'] in ['Laterizio.001','Pietra grigia continua.001','Tegole 2.001'])
stats={'triangoli':triangles,'mesh_materiali':len(meshes),'piani_residenziali':8,'aggetto_m':1,'pietra_fino_a_m':3.2,'basamento_fino_a_m':6,'blend_MB':round(os.path.getsize(bpy.data.filepath)/1e6,2),'fbx_MB':round(os.path.getsize(os.path.join(out,'Molassi_Unreal.fbx'))/1e6,2),'glb_MB':round(os.path.getsize(os.path.join(out,'Molassi_Unreal.glb'))/1e6,2),'ringhiere_alpha_mode':rail['alphaMode'],'texture_materiali':[{'name':m['name'],'normal_map':'normalTexture' in m} for m in gltf['materials']]}
with open(os.path.join(out,'verifica_unreal.json'),'w') as f:json.dump(stats,f,indent=2)
print('ASSET_VERIFICATO',json.dumps(stats))
# Check interchange scale by round-tripping the FBX in an empty scene.
original_points=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
expected=[max(p[i] for p in original_points)-min(p[i] for p in original_points) for i in range(3)]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(out,'Molassi_Unreal.fbx'))
points=[o.matrix_world@Vector(v) for o in bpy.context.scene.objects if o.type=='MESH' for v in o.bound_box]
actual=[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]
assert all(abs(a-b)<.01 for a,b in zip(actual,expected)),(actual,expected)
print('FBX_SCALA_VERIFICATA',actual)
