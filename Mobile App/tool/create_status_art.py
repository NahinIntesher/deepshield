"""Generate original, small vector Lottie assets. No downloaded artwork."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'assets' / 'motion'
OUT.mkdir(parents=True, exist_ok=True)

def prop(v): return {'a': 0, 'k': v}
def animated(values):
    return {'a': 1, 'k': [dict(t=t, s=v, e=values[i+1][1], i={'x':[.67], 'y':[1]}, o={'x':[.33], 'y':[0]}) if i+1<len(values) else dict(t=t,s=v) for i,(t,v) in enumerate(values)]}
def path(points, closed=False):
    return {'ty':'sh','ks':prop({'i':[[0,0]]*len(points),'o':[[0,0]]*len(points),'v':points,'c':closed}),'nm':'Outline'}
def stroke(width=4, opacity=100):
    return {'ty':'st','c':prop([1,1,1,1]),'o':prop(opacity),'w':prop(width),'lc':2,'lj':2,'nm':'Ink'}
def group(shapes):
    return {'ty':'gr','it':shapes+[{'ty':'tr','p':prop([0,0]),'a':prop([0,0]),'s':prop([100,100]),'r':prop(0),'o':prop(100)}]}
def layer(name, shapes, position=None, opacity=None):
    return {'ddd':0,'ind':1,'ty':4,'nm':name,'sr':1,'ks':{'o':opacity or prop(100),'r':prop(0),'p':position or prop([0,0,0]),'a':prop([0,0,0]),'s':prop([100,100,100])},'ao':0,'shapes':[group(shapes)],'ip':0,'op':90,'st':0,'bm':0}
def ellipse(x,y,w,h): return {'ty':'el','p':prop([x,y]),'s':prop([w,h]),'nm':'Circle'}
def save(name,layers):
    for i,l in enumerate(layers): l['ind']=i+1
    data={'v':'5.7.4','fr':30,'ip':0,'op':90,'w':200,'h':200,'nm':'DeepShield '+name,'ddd':0,'assets':[],'layers':layers,'markers':[]}
    (OUT/(name+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')

shield=path([[100,32],[151,52],[147,114],[131,143],[100,166],[69,143],[53,114],[49,52]],True)
save('scan',[
    layer('Scan line',[path([[71,86],[129,86]]),stroke(4)],animated([(0,[0,-22,0]),(45,[0,42,0]),(89,[0,-22,0])])),
    layer('Frame',[shield,stroke(3,40)]),
    layer('Video',[path([[89,76],[89,119],[120,98]],True),stroke(3)]),
    layer('Corners',[path([[35,68],[35,39],[64,39]]),path([[136,39],[165,39],[165,68]]),path([[35,132],[35,161],[64,161]]),path([[136,161],[165,161],[165,132]]),stroke(3,65)]),
])
save('empty',[
    layer('Document',[path([[72,40],[117,40],[137,60],[137,145],[72,145]],True),stroke(3),path([[117,40],[117,60],[137,60]]),stroke(3)],animated([(0,[0,8,0]),(35,[0,0,0]),(89,[0,0,0])])),
    layer('Lines',[path([[86,81],[120,81]]),path([[86,96],[120,96]]),path([[86,111],[106,111]]),stroke(3,45)]),
    layer('Tray',[path([[42,123],[42,161],[158,161],[158,123]]),stroke(4)]),
    layer('Dot',[ellipse(154,63,9,9),stroke(3,45)]),
])
save('success',[
    layer('Check',[path([[73,99],[92,118],[130,78]]),stroke(6),{'ty':'tm','s':prop(0),'e':animated([(0,[0]),(28,[100]),(89,[100])]),'o':prop(0),'m':1,'nm':'Reveal'}]),
    layer('Ring',[ellipse(100,100,124,124),stroke(3,45)]),
    layer('Spark',[path([[153,35],[153,49]]),path([[146,42],[160,42]]),stroke(3)],opacity=animated([(0,[0]),(25,[100]),(60,[0]),(89,[0])])),
])

# Owner-selected motion: A (Orbit) for waiting; B (Focus) for model scans.
def trim(a,b):return {'ty':'tm','s':prop(a),'e':prop(b),'o':prop(0),'m':1}
orbit=layer('Outer arc',[ellipse(100,100,112,112),stroke(5),trim(0,68)])
orbit['ks']['a']=prop([100,100,0]);orbit['ks']['p']=prop([100,100,0]);orbit['ks']['r']=animated([(0,[0]),(89,[360])])
inner=layer('Inner arc',[ellipse(100,100,78,78),stroke(3,35),trim(0,42)])
inner['ks']['a']=prop([100,100,0]);inner['ks']['p']=prop([100,100,0]);inner['ks']['r']=animated([(0,[320]),(89,[-40])])
save('loading',[orbit,inner,layer('Track',[ellipse(100,100,112,112),stroke(5,9)])])
save('scan',[
 layer('Sweep',[path([[77,100],[123,100]]),stroke(3)],animated([(0,[0,-23,0]),(45,[0,23,0]),(89,[0,-23,0])])),
 layer('Focus frame',[path([[60,79],[60,60],[79,60]]),path([[121,60],[140,60],[140,79]]),path([[60,121],[60,140],[79,140]]),path([[121,140],[140,140],[140,121]]),stroke(4)]),
 layer('Lens',[ellipse(100,100,38,38),stroke(2,15)]),
])
save('empty',[
 layer('Magnifier',[ellipse(100,90,66,66),stroke(4),path([[124,114],[148,138]]),stroke(6)],animated([(0,[-8,0,0]),(30,[5,-4,0]),(60,[-3,2,0]),(89,[0,0,0])])),
 layer('No match',[path([[91,81],[109,99]]),path([[109,81],[91,99]]),stroke(3,45)]),
 layer('Document',[path([[47,53],[47,145],[116,145]]),stroke(3,18),path([[58,157],[130,157]]),stroke(3,12)]),
])
