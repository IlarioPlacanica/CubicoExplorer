import bpy, math, os, random, json, sys
from mathutils import Vector
from collections import defaultdict

TEX_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),'textures')
REALTIME='--realtime' in sys.argv
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'unreal') if REALTIME else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT,exist_ok=True)
random.seed(47)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene; S.unit_settings.system='METRIC'; S.unit_settings.scale_length=1
C=bpy.data.collections.new('MOLASSI_V2_DETTAGLIATO'); S.collection.children.link(C)
D=defaultdict(lambda: [[],[],[]]); MAT={}

def material(name,color,rough=.65,metal=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    MAT[name]=m; return m

def noise(m,scale,amount=.1,bumpdist=.005):
    n=m.node_tree.nodes; l=m.node_tree.links; p=n.get('Principled BSDF'); t=n.new('ShaderNodeTexNoise'); t.inputs['Scale'].default_value=scale; t.inputs['Detail'].default_value=3
    co=n.new('ShaderNodeTexCoord'); l.new(co.outputs['Object'],t.inputs['Vector'])
    b=n.new('ShaderNodeBump'); b.inputs['Strength'].default_value=amount; b.inputs['Distance'].default_value=bumpdist; l.new(t.outputs['Fac'],b.inputs['Height']); l.new(b.outputs['Normal'],p.inputs['Normal'])

def bitmap(name,fn,size,rough):
    m=material(name,(.5,.5,.5),rough); n=m.node_tree.nodes; l=m.node_tree.links; p=n.get('Principled BSDF')
    im=bpy.data.images.load(os.path.join(TEX_DIR,fn)); im.pack()
    co=n.new('ShaderNodeTexCoord'); mp=n.new('ShaderNodeVectorMath'); mp.operation='MULTIPLY'; mp.inputs[1].default_value=(1/size[0],1/size[1],1)
    tex=n.new('ShaderNodeTexImage'); tex.image=im; tex.extension='REPEAT'; l.new(co.outputs['UV'],mp.inputs[0]); l.new(mp.outputs[0],tex.inputs['Vector']); l.new(tex.outputs['Color'],p.inputs['Base Color'])
    # Broad weathering variation remains procedural and responds to real illumination.
    nt=n.new('ShaderNodeTexNoise'); nt.inputs['Scale'].default_value=.85; nt.inputs['Detail'].default_value=4; l.new(co.outputs['Object'],nt.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position=.18; ramp.color_ramp.elements[0].color=(.48,.45,.42,1); ramp.color_ramp.elements[1].position=.8; ramp.color_ramp.elements[1].color=(1,1,1,1); l.new(nt.outputs['Fac'],ramp.inputs[0])
    mix=n.new('ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=.45; l.new(tex.outputs['Color'],mix.inputs[1]); l.new(ramp.outputs['Color'],mix.inputs[2]); l.new(mix.outputs[0],p.inputs['Base Color'])
    b=n.new('ShaderNodeBump'); b.inputs['Strength'].default_value=.28; b.inputs['Distance'].default_value=.012 if name=='Laterizio' else .002; l.new(tex.outputs['Color'],b.inputs['Height']); l.new(b.outputs['Normal'],p.inputs['Normal'])
    return m

bitmap('Laterizio','laterizio.png',(2.08,1.575),.79)
bitmap('Pietra grigia continua','pietra_grigia.png',(1.8,1.8),.48)
for name,col,r,met in [('Intonaco',(.58,.54,.45),.87,0),('Calcestruzzo',(.49,.47,.40),.8,0),('Alluminio',(.58,.64,.65),.3,.75),('Pannelli azzurri',(.32,.43,.47),.46,.28),('Ferro verniciato',(.065,.09,.10),.36,.72),('Serramenti bronzo',(.13,.085,.049),.35,.45),('Guarnizioni',(.013,.016,.018),.85,0),('Interni scuri',(.045,.040,.032),.95,0),('Tenda avorio',(.61,.58,.48),.97,0),('Tenda grigia',(.27,.30,.29),.96,0),('Tenda verde',(.04,.18,.125),.88,0),('Tapparella cotto',(.36,.135,.062),.68,0),('Tapparella avorio',(.63,.56,.41),.71,0),('Tapparella marrone',(.14,.077,.035),.74,0),('Zinco',(.28,.31,.32),.4,.7),('Terra vaso',(.065,.035,.015),1,0),('Vaso',(.34,.12,.065),.8,0),('Foglie',(.08,.16,.045),.83,0),('Insegna rossa',(.38,.015,.008),.4,0)]:
    m=material(name,col,r,met)
    if name in ('Intonaco','Calcestruzzo','Pannelli azzurri'): noise(m,95,.22,.008)
for i in range(6):
    m=material('Vetro '+str(i),(.78+i*.022,.85+i*.014,.88+i*.014),.045+i*.012,0)
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Transmission Weight'].default_value=.94; p.inputs['IOR'].default_value=1.46
for i in range(8):
    m=material('Tegole '+str(i),(.22+i*.017,.065+i*.008,.026+i*.003),.77)
    noise(m,110,.38,.006)

TEX_SIZES={'Laterizio':(2.08,1.575),'Pietra grigia continua':(1.8,1.8),'Tegole 2':(3.12,4.32)}
if REALTIME:
    import shutil
    os.makedirs(os.path.join(OUT,'textures'),exist_ok=True)
    S.render.engine='CYCLES'; S.cycles.samples=1
    # Bake surface relief to tangent-space normal maps using Blender's material baker.
    for name,fn in [('Laterizio','laterizio.png'),('Pietra grigia continua','pietra_grigia.png'),('Tegole 2','tegole.png')]:
        m=material(name,(.5,.5,.5),.74 if name!='Pietra grigia continua' else .48)
        n=m.node_tree.nodes; l=m.node_tree.links; bs=n.get('Principled BSDF')
        src=bpy.data.images.load(os.path.join(TEX_DIR,fn),check_existing=True); src.pack(); shutil.copy2(os.path.join(TEX_DIR,fn),os.path.join(OUT,'textures',fn))
        t=n.new('ShaderNodeTexImage'); t.image=src; l.new(t.outputs['Color'],bs.inputs['Base Color'])
        b=n.new('ShaderNodeBump'); b.inputs['Strength'].default_value=.4; b.inputs['Distance'].default_value=.028 if name=='Tegole 2' else .006; l.new(t.outputs['Color'],b.inputs['Height']); l.new(b.outputs['Normal'],bs.inputs['Normal'])
        normal_path=os.path.join(OUT,'textures',fn.replace('.png','_Normal.png'))
        cached=os.path.exists(normal_path)
        normal=bpy.data.images.load(normal_path,check_existing=True) if cached else bpy.data.images.new(fn.replace('.png','_Normal'),width=1024,height=1024); normal.colorspace_settings.name='Non-Color'
        target=n.new('ShaderNodeTexImage'); target.image=normal; n.active=target
        bpy.ops.mesh.primitive_plane_add(size=2); temp=bpy.context.object; temp.scale=(TEX_SIZES[name][0]/2,TEX_SIZES[name][1]/2,1); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); temp.data.materials.append(m)
        if not cached:
            S.render.bake.use_clear=True; S.render.bake.margin=8; bpy.ops.object.bake(type='NORMAL')
            normal.filepath_raw=normal_path; normal.file_format='PNG'; normal.save()
        normal.pack()
        bpy.data.objects.remove(temp,do_unlink=True)
        nm=n.new('ShaderNodeNormalMap'); l.new(target.outputs['Color'],nm.inputs['Color']); l.new(nm.outputs['Normal'],bs.inputs['Normal']); n.remove(b)
    # Bake a repeating railing card from simple geometry, keeping alpha rather than thousands of posts.
    rm=material('Railing bake',(.05,.065,.075),.4,.6); bs=rm.node_tree.nodes.get('Principled BSDF'); bs.inputs['Emission Color'].default_value=(.035,.045,.052,1); bs.inputs['Emission Strength'].default_value=1
    tempobs=[]
    for x in [i/7 for i in range(8)]:
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,.5,0)); ob=bpy.context.object; ob.dimensions=(.012,1,.01); ob.data.materials.append(rm); tempobs.append(ob)
    for y in (.035,.97):
        bpy.ops.mesh.primitive_cube_add(size=1,location=(.5,y,0)); ob=bpy.context.object; ob.dimensions=(1,.018,.01); ob.data.materials.append(rm); tempobs.append(ob)
    bpy.ops.object.camera_add(location=(.5,.5,2)); ob=bpy.context.object; ob.data.type='ORTHO'; ob.data.ortho_scale=1; S.camera=ob; tempobs.append(ob)
    S.render.resolution_x=512; S.render.resolution_y=512; S.render.resolution_percentage=100; S.render.film_transparent=True; S.render.image_settings.file_format='PNG'; S.render.image_settings.color_mode='RGBA'; S.view_settings.view_transform='Standard'; S.cycles.samples=4
    S.render.filepath=os.path.join(OUT,'textures','ringhiera_RGBA.png')
    if not os.path.exists(S.render.filepath):bpy.ops.render.render(write_still=True)
    for ob in tempobs:bpy.data.objects.remove(ob,do_unlink=True)
    S.render.film_transparent=False
    m=material('Ringhiera mascherata',(.05,.065,.075),.4,.6); n=m.node_tree.nodes; l=m.node_tree.links; t=n.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(S.render.filepath); t.image.pack(); bs=n.get('Principled BSDF'); l.new(t.outputs['Color'],bs.inputs['Base Color']); clip=n.new('ShaderNodeMath'); clip.operation='GREATER_THAN'; clip.inputs[1].default_value=.5; l.new(t.outputs['Alpha'],clip.inputs[0]); l.new(clip.outputs[0],bs.inputs['Alpha'])
    MAT['Vetro 0'].node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=0
    MAT['Vetro 0'].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.08,.13,.16,1)
    MAT['Vetro 0'].node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.65

def face(group,mat,verts,uv=None):
    d=D[(group,mat)]; off=len(d[0]); d[0].extend([tuple(v) for v in verts]); d[1].append(tuple(range(off,off+len(verts))))
    if uv is None:
        a=Vector(verts[1])-Vector(verts[0]); b=Vector(verts[-1])-Vector(verts[0]); norm=a.cross(b)
        if abs(norm.z)>abs(norm.x)+abs(norm.y): uv=[(v[0],v[1]) for v in verts]
        elif abs(norm.y)>=abs(norm.x): uv=[(v[0],v[2]) for v in verts]
        else: uv=[(v[1],v[2]) for v in verts]
    d[2].append(uv)

def box(group,mat,loc,size):
    x,y,z=loc; a,b,c=[v/2 for v in size]
    v=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
    for f in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:face(group,mat,[v[j] for j in f])

class Facade:
    def __init__(self,name,origin,tangent,normal,length):self.name=name; self.o=Vector((*origin,0)); self.t=Vector((*tangent,0)); self.n=Vector((*normal,0)); self.length=length
    def pt(self,s,z,d=0):return self.o+self.t*s+Vector((0,0,z))+self.n*d
    def panel(self,mat,a,b,z0,z1,d=0,group='Murature'):
        if b<=a or z1<=z0:return
        face(group,mat,[self.pt(a,z0,d),self.pt(b,z0,d),self.pt(b,z1,d),self.pt(a,z1,d)],[(a,z0),(b,z0),(b,z1),(a,z1)])
    def cub(self,mat,s,z,w,h,depth,d=0,group='Serramenti'):
        if REALTIME and group in ('Serramenti','Guide tapparelle','Reticolo vetrocemento','Traversi facciata','Profili scanalati'):
            self.panel(mat,s-w/2,s+w/2,z-h/2,z+h/2,d+depth/2,group)
            return
        p=self.pt(s,z,d); size=(w,depth,h) if abs(self.t.x)>.5 else (depth,w,h); box(group,mat,p,size)
    def wall(self,a,b,z0,z1,mat,openings):
        cur=a
        for x0,x1,lo,hi in sorted(openings):
            self.panel(mat,cur,x0,z0,z1); self.panel(mat,x0,x1,z0,lo); self.panel(mat,x0,x1,hi,z1)
            for p,q in [((x0,lo),(x1,lo)),((x1,lo),(x1,hi)),((x1,hi),(x0,hi)),((x0,hi),(x0,lo))]:
                face('Spallette',mat,[self.pt(*p),self.pt(*q),self.pt(*q,-.25),self.pt(*p,-.25)])
            cur=x1
        self.panel(mat,cur,b,z0,z1)

F=Facade('Fronte',(0,0),(1,0),(0,-1),46)
R=Facade('Destra',(46,0),(0,1),(1,0),15)
PROJECTION=1.0
FB=Facade('Fronte volumi aggettanti',(0,-PROJECTION),(1,0),(0,-1),46)
RB=Facade('Destra volume aggettante',(46+PROJECTION,0),(0,1),(1,0),15)
B=Facade('Retro arretrato',(34,10),(-1,0),(0,1),34)
W=Facade('Retro testata',(46,15),(-1,0),(0,1),12)
N=Facade('Rientranza',(34,15),(0,-1),(-1,0),5)
L=Facade('Sinistra',(0,10),(0,-1),(-1,0),10)
faces=[F,R,W,N,B,L]

def rod(group,mat,p,q,r=.02,sides=8):
    p=Vector(p); q=Vector(q); z=(q-p).normalized(); helper=Vector((0,0,1)) if abs(z.z)<.9 else Vector((1,0,0)); u=z.cross(helper).normalized(); v=z.cross(u)
    rings=[[c+r*(math.cos(2*math.pi*i/sides)*u+math.sin(2*math.pi*i/sides)*v) for i in range(sides)] for c in (p,q)]
    for i in range(sides):j=(i+1)%sides; face(group,mat,[rings[0][i],rings[0][j],rings[1][j],rings[1][i]])
    face(group,mat,list(reversed(rings[0]))); face(group,mat,rings[1])

def curtain(f,s,z,w,h,variant):
    if REALTIME:
        f.panel('Tenda avorio',s-w/2,s+w/2,z,z+h,-.38,'Tende interne')
        return
    mat='Tenda grigia' if variant%3==0 else 'Tenda avorio'
    # Two folded curtains leaving a variable central opening.
    gap=w*(.15+.05*(variant%4)); width=(w-gap)/2
    for start in (s-w/2,s+gap/2):
        for k in range(16):
            a=start+width*k/16; b=start+width*(k+1)/16
            da=-.37+.035*math.sin(k*math.pi/2); db=-.37+.035*math.sin((k+1)*math.pi/2)
            face('Tende interne',mat,[f.pt(a,z,da),f.pt(b,z,db),f.pt(b,z+h,db),f.pt(a,z+h,da)])

def window(f,s,z,w,h,style='bronzo',shutter=0,seed=0):
    frm='Serramenti bronzo' if style=='bronzo' else 'Alluminio'
    f.panel('Interni scuri',s-w/2,s+w/2,z,z+h,-.48,'Interni')
    curtain(f,s,z,w,h,seed)
    f.panel('Vetro '+str(seed%6),s-w/2+.06,s+w/2-.06,z+.06,z+h-.06,-.19,'Vetri')
    for ss in (s-w/2+.035,s+w/2-.035):
        f.cub('Guarnizioni',ss,z+h/2,.09,h,.09,-.20)
        f.cub(frm,ss,z+h/2,.055,h,.075,-.15)
    for zz in (z+.03,z+h-.03):f.cub(frm,s,zz,w,.06,.075,-.15)
    count=3 if w>2 else 2
    for k in range(1,count):f.cub(frm,s-w/2+w*k/count,z+h/2,.047,h,.085,-.145)
    f.cub(frm,s,z+h*.28,w,.028,.07,-.14)
    f.cub('Calcestruzzo',s,z-.045,w+.20,.09,.44,-.01,'Davanzali')
    if shutter>0:
        sh=h*shutter; sm=('Tapparella cotto','Tapparella avorio','Tapparella marrone')[seed%3]
        if REALTIME:f.panel(sm,s-w/2+.04,s+w/2-.04,z+h-sh,z+h,-.08,'Tapparelle leggere')
        for k in range(0 if REALTIME else max(1,int(sh/.047))):
            zz=z+h-.024-k*.047
            f.cub(sm,s,zz,w-.08,.042,.035,-.08,'Tapparelle a stecche')
        for ss in (s-w/2+.055,s+w/2-.055):f.cub('Alluminio',ss,z+h/2,.025,h,.04,-.065,'Guide tapparelle')
    # Small opening handle on the middle stile.
    if not REALTIME:f.cub(frm,s-w/2+w/count+.055,z+h*.45,.022,.14,.04,-.09,'Maniglie')

def balcony(f,s,z,w,depth,seed):
    f.cub('Calcestruzzo',s,z,w+.16,.19,depth+.22,depth/2-.03,'Balconi solette')
    f.cub('Intonaco',s,z+.065,w+.2,.075,.075,depth+.035,'Balconi bordi')
    for d0,d1,a,b in [(depth,depth,s-w/2,s+w/2),(0,depth,s-w/2,s-w/2),(depth,0,s+w/2,s+w/2)]:
        p=f.pt(a,z+1.12,d0); q=f.pt(b,z+1.12,d1)
        if not REALTIME:
            rod('Ringhiere','Ferro verniciato',p,q,.027)
            rod('Ringhiere','Ferro verniciato',f.pt(a,z+.24,d0),f.pt(b,z+.24,d1),.014)
        if REALTIME:
            length=(q-p).length
            face('Ringhiere leggere','Ringhiera mascherata',[f.pt(a,z+.21,d0),f.pt(b,z+.21,d1),f.pt(b,z+1.12,d1),f.pt(a,z+1.12,d0)],[(0,0),(length,0),(length,1),(0,1)])
        n=max(2,int((q-p).length/.14))
        if REALTIME:continue
        for i in range(n+1):
            ss=a+(b-a)*i/n; dd=d0+(d1-d0)*i/n
            rod('Ringhiere','Ferro verniciato',f.pt(ss,z+.21,dd),f.pt(ss,z+1.12,dd),.011,6)
    if not REALTIME and seed%7==0:
        f.cub('Vaso',s+.25,z+.28,.62,.30,.22,depth-.15,'Fioriere')
        f.cub('Terra vaso',s+.25,z+.435,.55,.025,.17,depth-.15,'Fioriere')
        for k in range(12):
            ss=s+.04+random.random()*.44; dd=depth-.22+random.random()*.14
            p=f.pt(ss,z+.44,dd); q=f.pt(ss+.06,z+.65+random.random()*.15,dd)
            rod('Vegetazione','Foglie',p,q,.015,5)
            for j in range(3):
                r=q+Vector((random.uniform(-.10,.10),random.uniform(-.1,.1),-.04*j)); face('Vegetazione','Foglie',[q,r+Vector((.035,0,0)),r+Vector((0,.05,0))])

# A single consistent base datum around the full perimeter: stone 0..3.2, glazed/stone 3.2..6.
for f in faces:
    ground=[]
    if f==F: centers=[3.4,16,28,42]
    elif f==R:centers=[4,8,12]
    elif f==B:centers=[3,12,20,30]
    elif f==W:centers=[4.6,7.5]
    else:centers=[]
    for s in centers:ground.append((s-1.05,s+1.05,.12,2.75))
    f.wall(0,f.length,0,3.2,'Pietra grigia continua',ground)
    for j,s in enumerate(centers):
        window(f,s,.12,2.1,2.63,'aluminum',0,j)
        if f in (F,R):f.cub('Insegna rossa',s,2.92,2.25,.32,.12,.08,'Insegne')
    upper=[]
    n=max(1,int(f.length/2.6)); step=f.length/n
    for j in range(n):upper.append((j*step+.11,(j+1)*step-.11,3.38,5.83))
    f.wall(0,f.length,3.2,6,'Pietra grigia continua',upper)
    for j,(a,b,lo,hi) in enumerate(upper):window(f,(a+b)/2,lo,b-a,hi-lo,'aluminum',0,j+2)
    f.cub('Zinco',f.length/2,3.23,f.length,.09,.16,.025,'Fasce basamento')
    f.cub('Calcestruzzo',f.length/2,6.015,f.length,.12,.21,.02,'Fasce basamento')
    # Stone slab joints, continuous height throughout all elevations.
    for zz in (.85,1.65,2.45):f.cub('Guarnizioni',f.length/2,zz,f.length,.005,.007,.003,'Giunti pietra')
    for j in range(1,int(f.length/1.25)):
        s=j*1.25
        if all(not(a<s<b) for a,b,lo,hi in ground):f.cub('Guarnizioni',s,1.6,.005,3.2,.006,.003,'Giunti pietra')

front_bal=[2.3,12.56,15.78,27.04,30.36,43.78]
blue_bays=[(3.2,10.5,2),(17.9,25.2,2),(32.8,42.8,3)]
brick_bays=[(0,3.2),(10.5,17.9),(25.2,32.8),(42.8,46)]
for k in range(8):
    z=6+k*3
    for a,b in brick_bays:
        cs=[s for s in front_bal if a<s<b]
        F.wall(a,b,z,z+3,'Laterizio',[(s-.63,s+.63,z+.25,z+2.58) for s in cs])
        for j,s in enumerate(cs):
            window(F,s,z+.25,1.26,2.33,shutter=random.choice([.03,.10,.22,.36,.62]),seed=k*7+j)
            balcony(F,s,z+.14,1.7,.65,k*6+j)
            F.cub('Intonaco',s,z+2.72,1.5,.25,.18,.03,'Frontone finestra')
    for a,b,n in blue_bays:
        step=(b-a)/n
        for j in range(n):
            s=a+step*(j+.5); w=step-.38
            FB.wall(a+j*step,a+(j+1)*step,max(z,6.35),min(z+3,29.72),'Pannelli azzurri',[(s-w/2,s+w/2,z+1.18,z+2.56)])
            window(FB,s,z+1.18,w,1.38,shutter=random.choice([.05,.18,.35,.62,.88]),seed=k*7+j)
            FB.cub('Alluminio',s,z+1.13,w+.12,.06,.15,.025,'Traversi facciata')
    # Side elevation: 3 vertical blue bays, same 8 levels and baseline.
    R.panel('Laterizio',0,4.1,z,z+3); R.panel('Laterizio',10.8,15,z,z+3)
    for j in range(3):
        a=4.1+j*6.7/3; b=a+6.7/3; s=(a+b)/2; w=b-a-.25
        RB.wall(a,b,max(z,6.35),min(z+3,29.72),'Pannelli azzurri',[(s-w/2,s+w/2,z+1.12,z+2.55)])
        window(RB,s,z+1.12,w,1.43,shutter=[.23,.6,.85,.95][(k+j)%4],seed=k+j+4)
    # Rear right wing: paired windows in brickwork.
    wo=[(5.0,6.1,z+1.0,z+2.45),(6.3,7.4,z+1.0,z+2.45)]
    W.wall(0,12,z,z+3,'Laterizio',wo)
    for j,(a,b,lo,hi) in enumerate(wo):window(W,(a+b)/2,lo,b-a,hi-lo,shutter=[.0,.3,.85][(k+j)%3],seed=k+j+1)
    # Main rear residential bays, interrupted by projecting stair towers.
    cs=[1.4,4.5,8.3,15.2,18.6,22.4,29.7,32.2]
    B.wall(0,34,z,z+3,'Intonaco',[(s-.94,s+.94,z+.22,z+2.61) for s in cs])
    for j,s in enumerate(cs):
        window(B,s,z+.22,1.88,2.39,'aluminum',shutter=[0,.0,.25,.72][(k+j)%4],seed=k+j)
        balcony(B,s,z+.12,2.35,.98,k*8+j)
    # Recess wall and inferred left side receive real inset openings.
    for f in (N,L):
        cs2=[f.length*.5] if f==N else [2.7,7.3]
        f.wall(0,f.length,z,z+3,'Laterizio',[(s-.7,s+.7,z+.9,z+2.5) for s in cs2])
        for j,s in enumerate(cs2):window(f,s,z+.9,1.4,1.6,shutter=.3,seed=k+j)

for f,groups in [(FB,blue_bays),(RB,[(4.1,10.8,3)])]:
    for a,b,n in groups:
        for j in range(n+1):
            s=a+(b-a)*j/n
            f.cub('Alluminio',s,18.035,.17,23.37,.19,.075,'Montanti verticali')
            for delta in (-.105,.105):f.cub('Alluminio',s+delta,18.035,.026,23.37,.23,.085,'Profili scanalati')

# The entire window/panel assemblies project 60cm, not just their aluminum trims.
for base,groups in [(F,blue_bays),(R,[(4.1,10.8,3)])]:
    for a,b,n in groups:
        for s in (a,b):
            face('Fianchi aggetti','Laterizio',[base.pt(s,6.35),base.pt(s,29.72),base.pt(s,29.72,PROJECTION),base.pt(s,6.35,PROJECTION)],[(0,6.35),(0,29.72),(PROJECTION,29.72),(PROJECTION,6.35)])
        face('Sottosquadri aggetti','Calcestruzzo',[base.pt(a,6.35),base.pt(b,6.35),base.pt(b,6.35,PROJECTION),base.pt(a,6.35,PROJECTION)])
        face('Scossaline aggetti','Zinco',[base.pt(a,29.72),base.pt(b,29.72),base.pt(b,29.72,PROJECTION),base.pt(a,29.72,PROJECTION)])
        base.panel('Laterizio',a,b,6,6.35)
        base.panel('Laterizio',a,b,29.72,30)
        base.cub('Zinco',(a+b)/2,6.36,b-a,.045,.045,PROJECTION+.025,'Gocciolatoi aggetti')

# Opaque metal balcony panels and round fixings on the first front stack, visible in the new street reference.
for k in range(8):
    s=front_bal[0]; z=6+k*3+.14
    F.cub('Zinco',s,z+.65,1.56,.87,.03,.66,'Parapetti pieni')
    for dx in (-.62,.62):
        for dz in (.31,.99):
            p=F.pt(s+dx,z+dz,.68); q=F.pt(s+dx,z+dz,.70)
            rod('Fissaggi parapetti','Ferro verniciato',p,q,.018,8)

# Rounded glazed stair towers: full geometric glass-block grid, with aligned floor bands.
for j,(center,width) in enumerate(((12.2,4.0),(26.6,4.2))):
    # local rear s mapped into world x; faceted curved front corners.
    x=34-center; a=x-width/2; b=x+width/2
    pp=[(a,10),(b,10),(b,11.10),(b-.24,11.55),(b-.55,11.75),(a+.55,11.75),(a+.24,11.55),(a,11.10)]
    for ii in range(1,len(pp)):
        p=Vector(pp[ii]); q=Vector(pp[(ii+1)%len(pp)]); tangent=(q-p).normalized(); normal=Vector((tangent.y,-tangent.x))
        sf=Facade('Vano scala',p,tangent,normal,(q-p).length)
        sf.panel('Pietra grigia continua',0,sf.length,0,3.2)
        sf.panel('Vetro '+str((j+ii)%6),0,sf.length,3.2,31.8)
        for z0 in [3.2+i*(1.2 if REALTIME else .30) for i in range(24 if REALTIME else 96)]:sf.cub('Alluminio',sf.length/2,z0,sf.length,.023,.045,.025,'Reticolo vetrocemento')
        for a0 in range(int(sf.length/(.54 if REALTIME else .27))+1):sf.cub('Alluminio',a0*(.54 if REALTIME else .27),17.5,.022,28.6,.05,.03,'Reticolo vetrocemento')
        for k in range(9):sf.cub('Intonaco',sf.length/2,6+3*k,sf.length,.36,.10,.055,'Fasce vani scala')
    box('Vani scala coronamento','Calcestruzzo',(x,10.8,31.95),(width+.28,2.15,.27))
    box('Vani scala coronamento','Zinco',(x,10.8,32.105),(width+.30,2.18,.04))

# Rear balcony awnings with sag and striped fabric, several varied real projections.
for k,j in [(2,1),(4,4),(6,2),(7,5),(3,7)]:
    s=[1.4,4.5,8.3,15.2,18.6,22.4,29.7,32.2][j]; z=6+k*3+2.75
    for n in range(14):
        a=s-1.15+n*2.3/14; b=a+2.3/14; mat='Tenda verde' if n%2 else 'Tenda avorio'
        face('Tende da sole',mat,[B.pt(a,z,.12),B.pt(b,z,.12),B.pt(b,z-.35,1.12),B.pt(a,z-.35,1.12)])
        face('Tende da sole',mat,[B.pt(a,z-.35,1.12),B.pt(b,z-.35,1.12),B.pt(b,z-.52,1.12),B.pt(a,z-.52,1.12)])
    for a in (s-1.1,s+1.1):rod('Supporti tende','Alluminio',B.pt(a,z-.4,.1),B.pt(a,z-.35,1.1),.02)

# Wall-mounted condensers visible among rear balconies, with grille and pipework.
for k,j in [(0,2),(1,4),(2,6),(3,1),(4,5),(5,3),(6,0),(7,7)]:
    s=[1.4,4.5,8.3,15.2,18.6,22.4,29.7,32.2][j]+.88; z=6+k*3+2.2
    B.cub('Intonaco',s,z,.66,.44,.25,.19,'Climatizzatori')
    for i in range(8):B.cub('Alluminio',s,z-.16+i*.045,.53,.016,.025,.329,'Griglie climatizzatori')
    for ds in (-.25,.25):rod('Staffe climatizzatori','Zinco',B.pt(s+ds,z-.29,.03),B.pt(s+ds,z-.29,.35),.016)
    rod('Tubazioni','Intonaco',B.pt(s+.36,z,.16),B.pt(s+.36,z-.7,.16),.023)

# L-shaped pitched roof, modeled clay tiles rather than a flat brick shader.
e=[(-.38,-.38,30.16),(46.38,-.38,30.16),(46.38,15.38,30.16),(33.62,15.38,30.16),(33.62,10.38,30.16),(-.38,10.38,30.16)]
verts=e+[(5,5,33),(40,5,33),(40,9.5,33)]
roof_faces=[(0,1,7,6),(5,0,6),(5,6,7,4),(4,7,8,3),(3,8,2),(2,8,7,1)]
tile_count=0
def inside(p,poly):
    x,y=p; hit=False
    for i,a in enumerate(poly):
        b=poly[(i+1)%len(poly)]
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
    return hit
for ids in roof_faces:
    points=[Vector(verts[i]) for i in ids]; face('Copertura fondo','Tegole 2',points)
    normal=(points[1]-points[0]).cross(points[2]-points[0]).normalized()
    if normal.z<0:normal=-normal
    up=(Vector((0,0,1))-normal*normal.z).normalized(); cross=up.cross(normal).normalized(); origin=points[0]
    poly=[((p-origin).dot(cross),(p-origin).dot(up)) for p in points]
    umin=min(p[0] for p in poly); umax=max(p[0] for p in poly); vmin=min(p[1] for p in poly); vmax=max(p[1] for p in poly)
    rows=int((vmax-vmin)/.36)+1; cols=int((umax-umin)/.265)+1
    for r in range(0 if REALTIME else rows):
        vv=vmin+r*.36
        for c in range(cols):
            uu=umin+c*.265
            if not all(inside((uu+du,vv+dv),poly) for du,dv in [(0,0),(.273,0),(0,.405),(.273,.405)]):continue
            mat='Tegole '+str(random.randrange(8)); tile_count+=1
            for h in range(5):
                u0=uu+h*.273/5; u1=uu+(h+1)*.273/5
                def pt(u,v):return origin+cross*u+up*v+normal*(.025+.035*math.sin((u-uu)/.273*math.pi*2)+(.405-(v-vv))*.035)
                face('Tegole modellate',mat,[pt(u0,vv),pt(u1,vv),pt(u1,vv+.405),pt(u0,vv+.405)])
for a,b in [(Vector(verts[6]),Vector(verts[7])),(Vector(verts[7]),Vector(verts[8]))]:
    n=1 if REALTIME else int((b-a).length/.4)
    for i in range(n):rod('Coppi di colmo','Tegole 4',a+(b-a)*i/n+Vector((0,0,.10)),a+(b-a)*(i+1)/n+Vector((0,0,.10)),.15,12)

# Layered eaves, gutters and downspouts, with brackets.
for f in faces:
    for z,h,d,mat in [(29.78,.18,.33,'Intonaco'),(29.95,.12,.52,'Calcestruzzo'),(30.10,.10,.66,'Zinco')]:f.cub(mat,f.length/2,z,f.length+.12,h,d,.10,'Cornicioni')
    rod('Gronde','Zinco',f.pt(0,30.07,.42),f.pt(f.length,30.07,.42),.075,10)
    for s in (.18,f.length-.18):
        rod('Pluviali','Zinco',f.pt(s,.3,.12),f.pt(s,29.65,.12),.055,10)
        rod('Pluviali','Zinco',f.pt(s,29.65,.12),f.pt(s,30.05,.42),.055,10)
        for k in range(1,10):f.cub('Zinco',s,k*3,.15,.045,.17,.07,'Staffe pluviali')

for i,x in enumerate((4,10,17,25,32,40)):
    box('Comignoli','Intonaco',(x,4.5,33.17),(.50,.64,1.1))
    box('Comignoli','Zinco',(x,4.5,32.68),(.82,.92,.10))
    for z in (33.49,33.62,33.75):box('Comignoli','Tegole 3',(x,4.5,z),(.67,.82,.065))
    for dx in (-.23,.23):box('Comignoli','Intonaco',(x+dx,4.5,33.59),(.055,.60,.40))
    # Rooflight on front pitch.
    xx=x+.9; yy=2.5; zz=30.16+(yy+.38)*2.84/5.38
    box('Lucernari','Zinco',(xx,yy,zz+.075),(.78,.83,.10))
    face('Lucernari','Vetro 2',[(xx-.33,yy-.34,zz-.10),(xx+.33,yy-.34,zz-.10),(xx+.33,yy+.34,zz+.26),(xx-.33,yy+.34,zz+.26)])

root=bpy.data.objects.new('MOLASSI_V2_ROOT',None); C.objects.link(root)
root['dimensioni']='46 x 15 m; rientranza 12 x 5 m; gronda 30 m; colmo 33 m stimato'
root['piani_residenziali']=8; root['quota_inizio_residenziale']=6.0; root['quota_fascia_pietra']=3.2
root['sporgenza_volumi_azzurri_stimata']=PROJECTION
root['nota']='Ricostruzione dettagliata da riferimenti fotografici. Sinistra, microdettagli, interni, copertura e aperture basamento retro interpretati.'
bevel_groups={'Serramenti','Davanzali','Balconi solette','Balconi bordi','Montanti verticali','Cornicioni','Comignoli','Vani scala coronamento'}
if REALTIME:
    aliases={'Calcestruzzo':'Intonaco','Zinco':'Alluminio','Serramenti bronzo':'Ferro verniciato','Guarnizioni':'Ferro verniciato','Interni scuri':'Ferro verniciato','Tenda grigia':'Tenda avorio','Tapparella marrone':'Tapparella cotto','Vaso':'Tegole 2','Terra vaso':'Ferro verniciato','Foglie':'Tenda verde'}
    merged=defaultdict(lambda:[[],[],[]])
    for (group,mat),(vs,fs,uvs) in D.items():
        if group in ('Tende interne','Interni','Giunti pietra','Staffe pluviali','Staffe climatizzatori','Tubazioni','Griglie climatizzatori','Fissaggi parapetti'):continue
        mat=('Vetro 0' if mat.startswith('Vetro ') else 'Tegole 2' if mat.startswith('Tegole ') else aliases.get(mat,mat))
        d=merged[('SM_Molassi',mat)]; off=len(d[0]); d[0].extend(vs); d[1].extend([tuple(i+off for i in f) for f in fs])
        sx,sy=TEX_SIZES.get(mat,(1,1)); d[2].extend([[(u/sx,v/sy) for u,v in coords] for coords in uvs])
    D=merged
    C.name='MOLASSI_UNREAL'; root.name='MOLASSI_UNREAL_ROOT'; root['sporgenza_aggetti_m']=1.0
for (group,mat),(vs,fs,uvs) in D.items():
    me=bpy.data.meshes.new(group+' | '+mat); me.from_pydata(vs,[],fs); me.materials.append(MAT[mat]); me.update()
    ob=bpy.data.objects.new(me.name,me); C.objects.link(ob); ob.parent=root
    uv=me.uv_layers.new(name='UV_metrica')
    for poly,coords in zip(me.polygons,uvs):
        for li,p in zip(poly.loop_indices,coords):uv.data[li].uv=p
    if not REALTIME and group in bevel_groups:
        mod=ob.modifiers.new('Bordi reali','BEVEL'); mod.width=.008 if group=='Serramenti' else .015; mod.segments=2
        mod=ob.modifiers.new('Normali pesate','WEIGHTED_NORMAL')
C.asset_mark()

# Presentation setup: real sky illumination and a shadow-catching ground.
studio=bpy.data.collections.new('STUDIO_ANTEPRIME'); S.collection.children.link(studio)
def studio_obj(ob):
    for c in list(ob.users_collection):c.objects.unlink(ob)
    studio.objects.link(ob)
ground=material('Suolo',(.24,.23,.21),.94); noise(ground,22,.3,.009)
bpy.ops.mesh.primitive_plane_add(size=2000); ob=bpy.context.object; ob.name='Suolo anteprima'; ob.location.z=-.05; ob.data.materials.append(ground); studio_obj(ob)
S.world=bpy.data.worlds.new('Cielo fisico'); S.world.use_nodes=True; n=S.world.node_tree.nodes; l=S.world.node_tree.links
sky=n.new('ShaderNodeTexSky'); sky.sky_type='MULTIPLE_SCATTERING'; sky.sun_elevation=math.radians(37); sky.sun_rotation=math.radians(235); sky.sun_size=math.radians(3); sky.air_density=1.0
l.new(sky.outputs['Color'],n.get('Background').inputs['Color']); n.get('Background').inputs['Strength'].default_value=.45
bpy.ops.object.camera_add(); cam=bpy.context.object; studio_obj(cam); S.camera=cam; cam.data.type='PERSP'; cam.data.lens=52
def aim(loc,target):cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
S.render.engine='CYCLES'; S.cycles.samples=48; S.cycles.use_denoising=True; S.cycles.max_bounces=8
S.render.resolution_x=1800; S.render.resolution_y=1400; S.render.resolution_percentage=100; S.render.image_settings.file_format='PNG'
S.view_settings.view_transform='AgX'; S.view_settings.look='AgX - Medium High Contrast'
S.view_settings.exposure=-2.5
aim((83,-76,54),(23,6,15))
bpy.ops.object.select_all(action='DESELECT')
for ob in C.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=root
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=75; area.spaces.active.region_3d.view_location=(23,7,15); area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'Molassi_Unreal.blend' if REALTIME else 'Molassi_Dettagliato_V2.blend'))
if REALTIME:
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'Molassi_Unreal.glb'),use_selection=True,export_apply=True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT,'Molassi_Unreal.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
# No preview renders: user will inspect the BLEND directly.
for o in C.objects:
    if o.type=='MESH':o.data.calc_loop_triangles()
stats={'mesh':len([o for o in C.objects if o.type=='MESH']),'poligoni':sum(len(o.data.polygons) for o in C.objects if o.type=='MESH'),'triangoli':sum(len(o.data.loop_triangles) for o in C.objects if o.type=='MESH'),'tegole_geometriche':tile_count,'texture_incorporate':[i.name for i in bpy.data.images if i.packed_file],'quota_pietra_tutti_lati':3.2,'quota_residenziale_tutti_lati':6,'piani':8,'sporgenza_m':PROJECTION}
with open(os.path.join(OUT,'verifica_v2.json'),'w') as f:json.dump(stats,f,indent=2)
print('V2_COMPLETE',stats)
