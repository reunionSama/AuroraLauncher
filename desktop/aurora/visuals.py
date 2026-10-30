# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
# Gesture equations ported from AuroraLauncher-Android/android-port/aurora_motion.rs.
from __future__ import annotations
import math,random,time
from pathlib import Path
from PySide6.QtCore import Property,Signal,Slot,QTimer,QRectF,QPointF
from PySide6.QtGui import QColor,QPainter,QImage,QLinearGradient,QRadialGradient,QPainterPath,QPolygonF,QTransform
from PySide6.QtQuick import QQuickPaintedItem

NAMES=['挥手','点头','环顾','鞠躬','欢呼','伸展','摇摆','踏步','奔跑','跳跃','舞蹈','敬礼','思考','鼓掌','平衡','侧倾','转肩','仰望','踢腿','庆祝']
def gesture(ident,t):
    s=math.sin(t*4);pulse=max(0,math.sin(t*math.pi/3.2));parts={k:[0.,0.,0.] for k in ('body','head','leftArm','rightArm','leftLeg','rightLeg')};dy=0.
    b,h,la,ra,ll,rl=(parts[k] for k in parts)
    if ident==0:ra[2]=2.3+s*.35;ra[0]=-.25
    elif ident==1:h[0]=s*.4
    elif ident==2:h[1]=math.sin(t*2)*.8
    elif ident==3:b[0]=-.65*pulse;h[0]=-.2*pulse
    elif ident==4:la[2]=-2.7*pulse;ra[2]=2.7*pulse
    elif ident==5:la[2]=-1.6*pulse;ra[2]=1.6*pulse;h[0]=.3*pulse
    elif ident==6:b[2]=s*.18;la[2]=-.3;ra[2]=.3
    elif ident in (7,8):
        a=.65 if ident==7 else .95;ll[0]=s*a;rl[0]=-s*a;la[0]=-s*(.5 if ident==7 else 1);ra[0]=-la[0];b[0]=0 if ident==7 else -.25
    elif ident==9:dy=(1-math.cos(t*8))*1.25;la[2]=-.5;ra[2]=.5
    elif ident==10:b[1]=s*.4;la[2]=-1.1+s*.4;ra[2]=1.1+s*.4;ll[2]=-.1;rl[2]=.1
    elif ident==11:ra[0]=-1.6*pulse;ra[2]=.6*pulse;h[0]=-.1
    elif ident==12:h[2]=.2*pulse;ra[0]=-1.2*pulse;ra[2]=.25*pulse
    elif ident==13:la[0]=ra[0]=-1.1;la[1]=s*.45;ra[1]=-s*.45
    elif ident==14:la[2]=-1.4;ra[2]=1.4;ll[0]=.5*pulse;b[2]=-.15*pulse
    elif ident==15:b[2]=-.32*pulse;h[2]=.2*pulse;ra[2]=.55*pulse
    elif ident==16:la[0]=s*.6;la[2]=-.4;ra[0]=math.sin(t*4+1.57)*.6;ra[2]=.4
    elif ident==17:h[0]=.65*pulse;h[1]=.3*s
    elif ident==18:rl[0]=-.95*pulse;la[0]=-.5*pulse;ra[0]=.5*pulse
    elif ident==19:la[2]=-2.4;ra[2]=2.4;dy=(1-math.cos(t*8))*.75;b[1]=s*.25
    def ease(x):x=max(0,min(1,x));return x*x*(3-2*x)
    weight=ease(t/.28)*ease((3.2-t)/.4)
    return {k:[a*weight for a in v] for k,v in parts.items()},dy*weight

def rotate(v,r):
    x,y,z=v;rx,ry,rz=r
    c,s=math.cos(rx),math.sin(rx);y,z=y*c-z*s,y*s+z*c
    c,s=math.cos(ry),math.sin(ry);x,z=x*c+z*s,-x*s+z*c
    c,s=math.cos(rz),math.sin(rz);x,y=x*c-y*s,x*s+y*c
    return x,y,z

class AnimatedPaint(QQuickPaintedItem):
    changed=Signal()
    def __init__(self,parent=None):
        super().__init__(parent);self.setAntialiasing(True);self._active=True;self._fps=60;self._frames=0;self._last=time.monotonic();self._time=0.
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(16)
    def tick(self):
        now=time.monotonic();delta=min(.1,now-self._last);self._last=now
        if self._active:self._time+=delta;self._frames+=1;self.update()
    def setActive(self,v):
        self._active=bool(v);self._last=time.monotonic()
        if v:self.timer.start(max(16,int(1000/self._fps)))
        else:self.timer.stop()
        self.changed.emit()
    renderActive=Property(bool,lambda self:self._active,setActive,notify=changed)
    def setFps(self,v):self._fps=max(15,min(60,int(v)));self.timer.setInterval(round(1000/self._fps));self.changed.emit()
    fps=Property(int,lambda self:self._fps,setFps,notify=changed)
    frameCount=Property(int,lambda self:self._frames,notify=changed)

class AuroraView(AnimatedPaint):
    def __init__(self,parent=None):
        super().__init__(parent);self._brightness=.72;self._hue=.4;self._speed=.5;self._phase=0.;self._brushes=[];self._size=None;self._cache_brushes()
    def tick(self):
        old=self._time;super().tick();self._phase+=(self._time-old)*(.15+self._speed*.7)
    def _cache_brushes(self):
        self._brushes=[]
        for layer in range(4):
            color=QColor.fromHsvF(((125+self._hue*120+layer*18)%360)/360,.7,.95)
            img=QImage(2,256,QImage.Format.Format_ARGB32_Premultiplied);img.fill(0)
            p=QPainter(img);grad=QLinearGradient(0,0,0,256)
            for stop,alpha in [(0,0),(.35,.25),(.7,1),(1,0)]:c=QColor(color);c.setAlphaF(alpha);grad.setColorAt(stop,c)
            p.fillRect(img.rect(),grad);p.end();self._brushes.append(img)
    def setBrightness(self,v):self._brightness=max(0,min(1,float(v)));self.update();self.changed.emit()
    brightness=Property(float,lambda self:self._brightness,setBrightness,notify=AnimatedPaint.changed)
    def setHue(self,v):self._hue=float(v);self._cache_brushes();self.update();self.changed.emit()
    hue=Property(float,lambda self:self._hue,setHue,notify=AnimatedPaint.changed)
    def setSpeed(self,v):self._speed=float(v);self.changed.emit()
    speed=Property(float,lambda self:self._speed,setSpeed,notify=AnimatedPaint.changed)
    def paint(self,target):
        w,h=self.width(),self.height()
        if min(w,h)<1:return
        rw=max(1,min(800,round(w*.6)));rh=max(1,round(h*rw/w))
        if not hasattr(self,'_frame') or self._frame.width()!=rw or self._frame.height()!=rh:
            self._frame=QImage(rw,rh,QImage.Format.Format_ARGB32_Premultiplied)
        painter=QPainter(self._frame)
        self._draw(painter,rw,rh);painter.end()
        target.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,True)
        target.drawImage(QRectF(0,0,w,h),self._frame)
    def _draw(self,p,w,h):
        t=self._phase
        bg=QLinearGradient(0,0,0,h);bg.setColorAt(0,QColor('#030c1b'));bg.setColorAt(.65,QColor('#092635'));bg.setColorAt(1,QColor('#091b27'));p.fillRect(QRectF(0,0,w,h),bg)
        p.setPen(QColor('#c6e4f2'))
        for i in range(110):
            p.setOpacity(.2+.4*(.5+.5*math.sin(t+i)));p.drawPoint(QPointF((i*7919%1000)/1000*w,(i*3571%1000)/1500*h))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        n=112 if self._fps>=60 else 72;column=w/n+1
        for layer,img in enumerate(self._brushes):
            for i in range(n):
                u=i/n;fold=math.sin(u*8+t*.55+layer)+.35*math.sin(u*21-t*.3+layer*2)
                top=h*(.13+layer*.07)+h*.1*fold;bottom=min(top+h*(.28+.07*math.sin(u*13+t+layer)),h*.87)
                p.setOpacity(self._brightness*(.14+.19*(.5+.5*math.sin(u*37+t+layer))))
                p.drawImage(QRectF(u*w,top,column,bottom-top),img)
        p.setOpacity(1);p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if self._size!=(w,h):
            self._size=(w,h);self._mountain=QPainterPath();self._mountain.moveTo(0,h);self._mountain.lineTo(0,h*.89)
            for i in range(49):u=i/48;self._mountain.lineTo(u*w,h*(.82-.06*math.sin(u*15)-.02*math.cos(u*47)))
            self._mountain.lineTo(w,h);self._mountain.closeSubpath()
        p.fillPath(self._mountain,QColor('#050e19'))

class PlayerView(AnimatedPaint):
    poseChanged=Signal()
    def __init__(self,parent=None):
        super().__init__(parent);self._yaw=-.36;self._skin=QImage();self._skinPath='';self._actions=True;self._interval=15;self._action=-1;self._actionStart=-100.;self._nextAction=15.;self._lastAction=-1
    def tick(self):
        super().tick()
        if self._active and self._actions and self._time>=self._nextAction:self.triggerAction();self._nextAction=self._time+self._interval
    def setYaw(self,v):self._yaw=float(v);self.update();self.changed.emit()
    yawAngle=Property(float,lambda self:self._yaw,setYaw,notify=AnimatedPaint.changed)
    def setSkin(self,path):
        if path==self._skinPath:return
        image=QImage(path)
        if image.isNull():return
        if image.width() not in (64,128,256,512,1024) or image.height() not in (image.width(),image.width()//2):return
        image=image.scaled(64,64 if image.width()==image.height() else 32)
        if image.height()==32:
            full=QImage(64,64,QImage.Format.Format_ARGB32);full.fill(0);p=QPainter(full);p.drawImage(0,0,image);p.drawImage(QRectF(16,48,16,16),image,QRectF(0,16,16,16));p.drawImage(QRectF(32,48,16,16),image,QRectF(40,16,16,16));p.end();image=full
        self._skin=image;self._skinPath=path;self.update();self.changed.emit()
    skinPath=Property(str,lambda self:self._skinPath,setSkin,notify=AnimatedPaint.changed)
    def setActions(self,v):self._actions=bool(v);self.changed.emit()
    actions=Property(bool,lambda self:self._actions,setActions,notify=AnimatedPaint.changed)
    def setInterval(self,v):self._interval=max(5,min(60,int(v)));self._nextAction=self._time+self._interval;self.changed.emit()
    interval=Property(int,lambda self:self._interval,setInterval,notify=AnimatedPaint.changed)
    actionName=Property(str,lambda self:NAMES[self._action] if self._time-self._actionStart<3.2 and self._action>=0 else '随时准备，出发冒险',notify=poseChanged)
    @Slot()
    def triggerAction(self):
        self._action=random.choice([i for i in range(20) if i!=self._lastAction]);self._lastAction=self._action;self._actionStart=self._time;self.poseChanged.emit();self.update()
    def paint(self,p):
        w,h=self.width(),self.height()
        if self._skin.isNull() or min(w,h)<1:return
        t=self._time;elapsed=t-self._actionStart
        pose,dy=gesture(self._action,elapsed) if 0<=elapsed<=3.2 else ({k:[0,0,0] for k in ('body','head','leftArm','rightArm','leftLeg','rightLeg')},0)
        idle=math.sin(t*1.5)*.025;pose['leftArm'][2]+=idle;pose['rightArm'][2]-=idle
        scale=min(w/23,h/37);center=w*.5;base=h*.94
        shadow=QRadialGradient(center,base-4,scale*9);shadow.setColorAt(0,QColor(0,0,0,70));shadow.setColorAt(1,QColor(0,0,0,0));p.setPen(QColor(0,0,0,0));p.setBrush(shadow);p.drawEllipse(QRectF(center-scale*9,base-scale*2,scale*18,scale*4))
        # name, dimensions, pivot, center relative to pivot, skin box origin
        boxes=[('head',(8,8,8),(0,24,0),(0,4,0),(0,0)),('body',(8,12,4),(0,24,0),(0,-6,0),(16,16)),
               ('leftArm',(4,12,4),(-6,24,0),(0,-6,0),(32,48)),('rightArm',(4,12,4),(6,24,0),(0,-6,0),(40,16)),
               ('leftLeg',(4,12,4),(-2,12,0),(0,-6,0),(16,48)),('rightLeg',(4,12,4),(2,12,0),(0,-6,0),(0,16))]
        faces=[]
        for name,dims,pivot,offset,uv in boxes:
            bw,bh,bd=dims;x,y,z=-bw/2,-bh/2,-bd/2;X,Y,Z=bw/2,bh/2,bd/2
            verts=[[(x,Y,Z),(X,Y,Z),(X,y,Z),(x,y,Z)],[(X,Y,z),(x,Y,z),(x,y,z),(X,y,z)],[(x,Y,z),(x,Y,Z),(x,y,Z),(x,y,z)],[(X,Y,Z),(X,Y,z),(X,y,z),(X,y,Z)],[(x,Y,z),(X,Y,z),(X,Y,Z),(x,Y,Z)],[(x,y,Z),(X,y,Z),(X,y,z),(x,y,z)]]
            u,v=uv;uvs=[(u+bd,v+bd,bw,bh),(u+bd+bw+bd,v+bd,bw,bh),(u,v+bd,bd,bh),(u+bd+bw,v+bd,bd,bh),(u+bd,v,bw,bd),(u+bd+bw,v,bw,bd)]
            for face,(points,rect) in enumerate(zip(verts,uvs)):
                world=[]
                for vertex in points:
                    rel=tuple(vertex[i]+offset[i] for i in range(3));rel=rotate(rel,pose[name]);rel=tuple(rel[i]+pivot[i] for i in range(3))
                    if name!='body':rel=rotate((rel[0],rel[1]-18,rel[2]),pose['body']);rel=(rel[0],rel[1]+18,rel[2])
                    rel=rotate((rel[0],rel[1]-16+dy,rel[2]),(0,self._yaw,0));rel=rotate(rel,(-.12,0,0));world.append(rel)
                polygon=QPolygonF([QPointF(center+a*scale,base-(b+16)*scale) for a,b,c in world]);faces.append((sum(v[2] for v in world)/4,polygon,rect,face))
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,False)
        for depth,poly,(u,v,sw,sh),face in sorted(faces,key=lambda x:x[0]):
            a,b,c,d=[poly[i] for i in range(4)]
            determinant=(b.x()-a.x())*(d.y()-a.y())-(b.y()-a.y())*(d.x()-a.x())
            if abs(determinant)<.1:continue
            p.save();p.setTransform(QTransform((b.x()-a.x())/sw,(b.y()-a.y())/sw,(d.x()-a.x())/sh,(d.y()-a.y())/sh,a.x(),a.y()),True)
            p.drawImage(QRectF(0,0,sw,sh),self._skin,QRectF(u,v,sw,sh));p.restore()
            if face in (1,2,3,5):p.setPen(QColor(0,0,0,0));p.setBrush(QColor(0,0,0,35 if face in (2,3) else 65));p.drawPolygon(poly)
