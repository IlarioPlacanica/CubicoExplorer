import bpy, os, math, json, struct
from mathutils import Vector
from collections import defaultdict

OUT=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene; S.unit_settings.system='METRIC'
C=bpy.data.collections.new('MOLASSI_FOTOGRAFICO'); S.collection.children.link(C)
data=defaultdict(lambda:[[],[],[]]); mats={}; imgs={}
for key,fn in [('front','fronte_fotografico.png'),('side','destra_fotografica.png'),('rear','retro_residenziale.png'),('base','retro_basamento.png'),('roof','tegole.png'),('rail','ringhiera_RGBA.png')]:
    im=bpy.data.images.load(os.path.join(OUT,'textures',fn)); im.pack(); imgs[key]=im

def material(name,key=None,color=(.45,.45,.45),rough=.7,metal=0,factor=(1,1,1)):
    m=bpy.data.materials.new(name); m.use_nodes=True; n=m.node_tree.nodes; l=m.node_tree.links; p=n.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    if key:
        t=n.new('ShaderNodeTexImage'); t.image=imgs[key]; t.extension='REPEAT' if key in ('rail','roof') else 'EXTEND'
        if factor!=(1,1,1):
            mix=n.new('ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=1; mix.inputs[2].default_value=(*factor,1); l.new(t.outputs['Color'],mix.inputs[1]); l.new(mix.outputs[0],p.inputs['Base Color'])
        else:l.new(t.outputs['Color'],p.inputs['Base Color'])
        if key=='rail':
            clip=n.new('ShaderNodeMath'); clip.operation='GREATER_THAN'; clip.inputs[1].default_value=.5; l.new(t.outputs['Alpha'],clip.inputs[0]); l.new(clip.outputs[0],p.inputs['Alpha'])
    mats[name]=m; return m

# Sample only unobstructed material patches. This is color analysis, not raster editing.
def meanpatch(key,x0,x1,y0,y1):
    im=imgs[key]; w,h=im.size; pix=im.pixels[:]; total=[0,0,0]; n=0
    for y in range(int(y0*h),int(y1*h),max(1,int(h/80))):
        for x in range(int(x0*w),int(x1*w),max(1,int(w/250))):
            i=4*(y*w+x)
            for c in range(3):total[c]+=pix[i+c]
            n+=1
    return [v/n for v in total]
brickmeans=[meanpatch('front',.008,.017,.4,.95),meanpatch('side',.008,.025,.4,.92),meanpatch('rear',.035,.05,.3,.85)]
graymeans=[meanpatch('front',.16,.25,.025,.12),meanpatch('side',.015,.06,.025,.105),meanpatch('base',.19,.21,.045,.12)]
def factors(samples):
    target=[min(row[i] for row in samples) for i in range(3)]
    return [tuple(max(.55,min(1,target[i]/max(.001,row[i]))) for i in range(3)) for row in samples]
bf=factors(brickmeans); gf=factors(graymeans)
material('Fronte foto','front',factor=bf[0]); material('Destra foto','side',factor=bf[1]); material('Retro foto','rear',factor=bf[2])
material('Basamento fronte','front',factor=gf[0]); material('Basamento destra','side',factor=gf[1]); material('Basamento retro','base',factor=gf[2])
material('Copertura foto','roof'); material('Ringhiere MASK','rail',rough=.45,metal=.65)
material('Cornici',color=(.43,.42,.36)); material('Metallo',color=(.18,.21,.22),rough=.4,metal=.65)

def face(group,mat,vs,uv):
    d=data[(group,mat)]; off=len(d[0]); d[0].extend([tuple(v) for v in vs]); d[1].append(tuple(range(off,off+len(vs)))); d[2].append(uv)
def box(group,mat,loc,size):
    x,y,z=loc; a,b,c=[s/2 for s in size]
    vs=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
    for ids in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:face(group,mat,[vs[i] for i in ids],[(0,0),(1,0),(1,1),(0,1)])

def interp(x,anchors):
    for (a,u),(b,v) in zip(anchors,anchors[1:]):
        if a-1e-6<=x<=b+1e-6:return u+(v-u)*(x-a)/(b-a)
    return anchors[0][1] if x<anchors[0][0] else anchors[-1][1]

FX=[(0,0),(2.3,54/1555),(3.2,102/1555),(10.5,329/1555),(12.56,396/1555),(15.78,504/1555),(17.9,583/1555),(25.2,819/1555),(27.04,893/1555),(30.36,1006/1555),(32.8,1093/1555),(42.8,1449/1555),(43.78,1500/1555),(46,1)]
SX=[(0,0),(4.1,210/887),(10.8,678/887),(15,1)]
# Each actual model floor uses a full source row. Repeat middle rows only.
FRONT_ROWS=[0,1,2,2,3,3,4,5]
SIDE_ROWS=[0,1,2,3,3,4,5,6]
# Source image row boundaries measured on the accepted six-row front elevation.
FRONT_Y=[674,558,448,339,229,120,0]
SIDE_Y=[1370,1184,998,812,626,440,254,62]

class Elevation:
    def __init__(self,name,o,t,n,length,kind):self.name=name; self.o=Vector((*o,0));self.t=Vector((*t,0));self.n=Vector((*n,0));self.length=length;self.kind=kind
    def pt(self,s,z,d=0):return self.o+self.t*s+Vector((0,0,z))+self.n*d
    def u(self,s):
        if self.kind=='front':return interp(s,FX)
        if self.kind=='side':return interp(s,SX)
        if self.kind=='wing':return .028+s/12*(.218-.028)
        return .218+s/34*(.984-.218)
    def mapping(self,s,z,k=None,base=False):
        u=self.u(s)
        if self.kind=='front':
            if base:return (s/46,interp(z,[(0,0),(3.2,1-823/1012),(6,1-674/1012)]))
            idx=FRONT_ROWS[k]; f=(z-(6+3*k))/3; return (u,1-(FRONT_Y[idx]+(FRONT_Y[idx+1]-FRONT_Y[idx])*f)/1012)
        if self.kind=='side':
            if base:return (s/15,interp(z,[(0,0),(3.2,1-1552/1774),(6,1-1370/1774)]))
            idx=SIDE_ROWS[k]; f=(z-(6+3*k))/3; return(u,1-(SIDE_Y[idx]+(SIDE_Y[idx+1]-SIDE_Y[idx])*f)/1774)
        if base:
            # New edited rear base, occupying the same six physical metres.
            u2=s/12*.214 if self.kind=='wing' else .214+s/34*(1-.214)
            return(u2,.032+z/6*(.188-.032))
        return(u,.126+(z-6)/24*(.896-.126))
    def panel(self,a,b,z0,z1,d=0,k=None,base=False,group=None):
        mat=('Basamento fronte' if self.kind=='front' else 'Basamento destra' if self.kind=='side' else 'Basamento retro') if base else ('Fronte foto' if self.kind=='front' else 'Destra foto' if self.kind=='side' else 'Retro foto')
        # Split at horizontal registration anchors so interpolation really matches the photo columns.
        cuts=[a]+([x for x,u in FX if a<x<b] if self.kind=='front' and not base else [])+[b]
        for aa,bb in zip(cuts,cuts[1:]):
            face(group or self.name,mat,[self.pt(aa,z0,d),self.pt(bb,z0,d),self.pt(bb,z1,d),self.pt(aa,z1,d)],[self.mapping(aa,z0,k,base),self.mapping(bb,z0,k,base),self.mapping(bb,z1,k,base),self.mapping(aa,z1,k,base)])

F=Elevation('Fronte',(0,0),(1,0),(0,-1),46,'front')
R=Elevation('Destra',(46,0),(0,1),(1,0),15,'side')
W=Elevation('Retro testata',(46,15),(-1,0),(0,1),12,'wing')
B=Elevation('Retro arretrato',(34,10),(-1,0),(0,1),34,'rear')
groups=[(3.2,10.5),(17.9,25.2),(32.8,42.8)]

for e in (F,R,W,B):
    for za,zb in [(0,3.2),(3.2,6)]:e.panel(0,e.length,za,zb,base=True)
    for k in range(8):
        z=6+3*k
        if e==F:
            for a,b in [(0,3.2),(10.5,17.9),(25.2,32.8),(42.8,46)]:e.panel(a,b,z,z+3,k=k)
            for i,(a,b) in enumerate(groups):e.panel(a,b,max(z,6.35),min(z+3,29.72),d=1,k=k,group='Aggetto fronte '+str(i+1))
        elif e==R:
            e.panel(0,4.1,z,z+3,k=k);e.panel(10.8,15,z,z+3,k=k)
            e.panel(4.1,10.8,max(z,6.35),min(z+3,29.72),d=1,k=k,group='Aggetto destra')
        else:e.panel(0,e.length,z,z+3,k=k)

for e,gs in [(F,groups),(R,[(4.1,10.8)])]:
    for i,(a,b) in enumerate(gs):
        e.panel(a,b,6,6.35,k=0); e.panel(a,b,29.72,30,k=7)
        for k in range(8):
            lo=max(6+3*k,6.35);hi=min(9+3*k,29.72)
            for ss in (a,b):
                # Dedicated return projection; never collapse a perpendicular face to a UV line.
                if e==F:
                    va=F.mapping(0,lo,k)[1];vb=F.mapping(0,hi,k)[1];u0,u1=.215,.239;mat='Fronte foto'
                else:
                    va=R.mapping(0,lo,k)[1];vb=R.mapping(0,hi,k)[1];u0,u1=.055,.12;mat='Destra foto'
                pts=[e.pt(ss,lo),e.pt(ss,lo,1),e.pt(ss,hi,1),e.pt(ss,hi)];uvs=[(u0,va),(u1,va),(u1,vb),(u0,vb)]
                if ss==b:pts.reverse();uvs.reverse()
                face('Fianchi aggetti',mat,pts,uvs)
        for z,mat in [(6.35,'Cornici'),(29.72,'Metallo')]:
            pts=[e.pt(a,z),e.pt(b,z),e.pt(b,z,1),e.pt(a,z,1)];uvs=[(0,0),(1,0),(1,1),(0,1)]
            if z>20:pts.reverse();uvs.reverse()
            face('Chiusure aggetti',mat,pts,uvs)

# Unphotographed return/left wall: project a clean brick strip with correct vertical scale.
for name,x,y0,y1 in [('Rientranza',34,10,15),('Sinistra',0,0,10)]:
    for k in range(8):
        z=6+3*k; v0=.126+k*(.896-.126)/8;v1=.126+(k+1)*(.896-.126)/8
        # Split long walls to maintain the source brick scale while keeping all UVs inside 0..1.
        steps=int((y1-y0)/1)
        for j in range(steps):
            a=y0+j*(y1-y0)/steps;b=y0+(j+1)*(y1-y0)/steps
            face(name,'Retro foto',[(x,a,z+3),(x,b,z+3),(x,b,z),(x,a,z)],[(.032,v1),(.075,v1),(.075,v0),(.032,v0)])
    face(name,'Basamento retro',[(x,y0,6),(x,y1,6),(x,y1,0),(x,y0,0)],[(.192,.188),(.211,.188),(.211,.032),(.192,.032)])

def balcony(e,s,z,w,depth):
    p=e.pt(s,z,depth/2)
    size=(w,depth,.14) if abs(e.t.x)>.5 else (depth,w,.14)
    box('Balconi solette','Cornici',p,size)
    for a,b,d0,d1 in [(s-w/2,s+w/2,depth,depth),(s-w/2,s-w/2,0,depth),(s+w/2,s+w/2,depth,0)]:
        length=math.hypot(b-a,d1-d0)
        face('Balconi ringhiere','Ringhiere MASK',[e.pt(a,z+.08,d0),e.pt(b,z+.08,d1),e.pt(b,z+1.04,d1),e.pt(a,z+1.04,d0)],[(0,0),(length,0),(length,1),(0,1)])

for k in range(8):
    z=6+3*k
    for s in (2.3,12.56,15.78,27.04,30.36,43.78):balcony(F,s,z+.30,1.65,.65)
    for u in (.25,.318,.405,.572,.651,.733,.902,.955):
        s=(u-.218)/(.984-.218)*34
        balcony(B,s,z+.18,2.35,.90)

# Stair tower faces use the matching strips of the original rear photo, without a tiny tiled grid.
for i,(ua,ub) in enumerate(((.448,.54),(.768,.866))):
    s0=(ua-.218)/.766*34;s1=(ub-.218)/.766*34;xc=34-(s0+s1)/2;w=s1-s0
    pp=[(xc-w/2,10),(xc+w/2,10),(xc+w/2,11.1),(xc+w/2-.30,11.65),(xc-w/2+.30,11.65),(xc-w/2,11.1)]
    for j in range(1,len(pp)):
        a=pp[j];b=pp[(j+1)%len(pp)]
        if j==3:uu0,uu1=ua,ub
        else:uu0,uu1=(ua,ua+.016) if j>3 else (ub-.016,ub)
        face('Vano scala '+str(i+1),'Retro foto',[(*a,6),(*b,6),(*b,31.8),(*a,31.8)],[(uu0,.126),(uu1,.126),(uu1,.952),(uu0,.952)])
        face('Vano scala '+str(i+1),'Basamento retro',[(*a,0),(*b,0),(*b,6),(*a,6)],[(.192,.032),(.211,.032),(.211,.188),(.192,.188)])
    box('Coronamento vani scala','Cornici',(xc,10.85,31.94),(w+.24,2.05,.25))

v=[(-.38,-.38,30.16),(46.38,-.38,30.16),(46.38,15.38,30.16),(33.62,15.38,30.16),(33.62,10.38,30.16),(-.38,10.38,30.16),(5,5,33),(40,5,33),(40,9.5,33)]
for ids in [(0,1,7,6),(5,0,6),(5,6,7,4),(4,7,8,3),(3,8,2),(2,8,7,1)]:
    pts=[Vector(v[i]) for i in ids];n=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
    if n.z<0:n=-n
    up=(Vector((0,0,1))-n*n.z).normalized();cross=up.cross(n).normalized()
    face('Copertura','Copertura foto',pts,[((p-pts[0]).dot(cross)/3.12,(p-pts[0]).dot(up)/4.32) for p in pts])
foot=[(0,0),(46,0),(46,15),(34,15),(34,10),(0,10)]
face('Fondo','Cornici',[(x,y,0) for x,y in reversed(foot)],[(x/46,y/15) for x,y in reversed(foot)])
for i,(x,y) in enumerate(foot):
    a,b=foot[(i+1)%len(foot)];box('Cornicioni','Cornici',((x+a)/2,(y+b)/2,30),(max(.25,abs(x-a)),max(.25,abs(y-b)),.22))
for x in (4,10,17,25,32,40):
    box('Comignoli','Cornici',(x,4.5,33.15),(.5,.65,1.1));box('Comignoli','Metallo',(x,4.5,33.73),(.7,.82,.10))

root=bpy.data.objects.new('MOLASSI_FOTO_ROOT',None);C.objects.link(root)
root['larghezza_m']=46;root['profondita_m']=15;root['gronda_m']=30;root['piani_residenziali']=8;root['aggetto_m']=1
root['gruppi_frontali']=3;root['colonne_per_gruppo']='2, 2, 3';root['gruppi_destra']=1;root['rientranza']='12 x 5 m'
root['UV']='Proiezione ortografica per prospetto e fasce di piano; UV foto 0..1; ripetizioni solo per materiali di copertura e ringhiere.'
root['texture_note']='Fronte e destra da immagini editate; retro residenziale conserva gli 8 piani originali. Adattamento dei piani eseguito nelle UV, senza accettare il quarto gruppo generato.'
for (name,mat),(vs,fs,uvs) in data.items():
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mats[mat]);me.update()
    ob=bpy.data.objects.new(name+' | '+mat,me);C.objects.link(ob);ob.parent=root
    layer=me.uv_layers.new(name='UV_Proiezione_Facciata')
    for poly,coords in zip(me.polygons,uvs):
        for li,co in zip(poly.loop_indices,coords):layer.data[li].uv=co
C.asset_mark()
bpy.ops.object.select_all(action='DESELECT')
for ob in C.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=root
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.shading.type='MATERIAL';a.spaces.active.region_3d.view_location=(23,7,15);a.spaces.active.region_3d.view_distance=75
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'Molassi_Fotografico.blend'))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'Molassi_Fotografico.glb'),use_selection=True,export_apply=True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT,'Molassi_Fotografico.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
tris=0;uv_bad=0;uv_degenerate=0
for ob in C.objects:
    if ob.type!='MESH':continue
    me=ob.data;me.calc_loop_triangles();tris+=len(me.loop_triangles)
    if ob.data.materials[0].name in ('Fronte foto','Destra foto','Retro foto','Basamento fronte','Basamento destra','Basamento retro'):
        for poly in me.polygons:
            pts=[me.uv_layers.active.data[i].uv for i in poly.loop_indices]
            if any(min(p)<-1e-6 or max(p)>1.000001 for p in pts):uv_bad+=1
            area=abs(sum(pts[i].x*pts[(i+1)%len(pts)].y-pts[(i+1)%len(pts)].x*pts[i].y for i in range(len(pts))))/2
            if area<1e-9:uv_degenerate+=1
assert uv_bad==0 and uv_degenerate==0,(uv_bad,uv_degenerate)
assert len([o for o in C.objects if o.name.startswith('Aggetto fronte ')])==3
assert len([o for o in C.objects if o.name.startswith('Aggetto destra')])==1
stats={'triangoli':tris,'materiali':len(mats),'mesh':len([o for o in C.objects if o.type=='MESH']),'UV_foto_fuori_0_1':uv_bad,'UV_degeneri':uv_degenerate,'gruppi_fronte':3,'gruppi_destra':1,'aggetto_m':1,'piani_residenziali':8,'correzione_colore_laterizio':bf,'correzione_colore_basamento':gf,'texture':{k:list(im.size) for k,im in imgs.items()},'blend_MB':round(os.path.getsize(bpy.data.filepath)/1e6,2)}
with open(os.path.join(OUT,'verifica_fotografico.json'),'w') as f:json.dump(stats,f,indent=2)
print('FOTO_ASSET_OK',stats)
