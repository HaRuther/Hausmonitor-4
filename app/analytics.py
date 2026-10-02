from math import sqrt
from statistics import mean,stdev
POINTS=('SW','SO','ANB','TSW','TSO')
def summary(v):
    if not v:return {'n':0,'mean':None,'sd':None,'se':None,'range':None}
    sd=stdev(v) if len(v)>1 else None
    return {'n':len(v),'mean':mean(v),'sd':sd,'se':sd/sqrt(len(v)) if sd is not None else None,'range':max(v)-min(v)}
def pair(a,b,base):
    if a['mean'] is None or b['mean'] is None:return {'value':None,'se':None,'delta':None,'snr':None,'quality':'unvollständig'}
    value=b['mean']-a['mean']; se=sqrt(a['se']**2+b['se']**2) if a['se'] is not None and b['se'] is not None else None
    delta=value-base if base is not None else None; snr=abs(delta)/se if delta is not None and se and se>0 else None
    q='Signal klar' if snr is not None and snr>=3 else 'Hinweis' if snr is not None and snr>=2 else 'im Rauschen' if snr is not None else 'nicht bewertbar'
    return {'value':value,'se':se,'delta':delta,'snr':snr,'quality':q}
def campaign_stats(g,bh=None,bt=None):
    o={p:summary(g.get(p,[])) for p in POINTS}; o['house']=pair(o['SW'],o['SO'],bh);o['terrace']=pair(o['TSW'],o['TSO'],bt);return o
def regression(xs,ys):
    p=[(float(x),float(y)) for x,y in zip(xs,ys) if x is not None and y is not None]
    if len(p)<3:return None
    mx=mean(x for x,_ in p);my=mean(y for _,y in p);den=sum((x-mx)**2 for x,_ in p)
    if not den:return None
    slope=sum((x-mx)*(y-my) for x,y in p)/den;intercept=my-slope*mx
    total=sum((y-my)**2 for _,y in p);res=sum((y-(intercept+slope*x))**2 for x,y in p)
    return {'n':len(p),'slope':slope,'intercept':intercept,'r2':1-res/total if total else None}
