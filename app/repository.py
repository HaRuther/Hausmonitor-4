from statistics import mean
from .database import connection
from .analytics import POINTS,campaign_stats,regression

def grouped(cid):
    g={p:[] for p in POINTS}
    with connection() as c:
        for r in c.execute('SELECT point,value FROM readings WHERE campaign_id=? ORDER BY sequence',(cid,)):g[r['point']].append(r['value'])
    return g
def campaigns():
    with connection() as c:rows=[dict(r) for r in c.execute('SELECT * FROM campaigns ORDER BY measured_at,id')]
    bh=bt=None;out=[]
    for r in rows:
        s=campaign_stats(grouped(r['id']),bh,bt)
        if bh is None and s['house']['value'] is not None:bh=s['house']['value'];s=campaign_stats(grouped(r['id']),bh,bt)
        if bt is None and s['terrace']['value'] is not None:bt=s['terrace']['value'];s=campaign_stats(grouped(r['id']),bh,bt)
        r['stats']=s;out.append(r)
    return out
def level_analytics(cs):
    y=[c['stats']['house']['delta'] for c in cs]
    return {'time':regression(range(len(cs)),y),'groundwater':regression([c['groundwater'] for c in cs],y),'air_temp':regression([c['air_temp'] for c in cs],y),'wall_delta':regression([(c['wall_temp_so']-c['wall_temp_sw']) if c['wall_temp_so'] is not None and c['wall_temp_sw'] is not None else None for c in cs],y)}
def crack_points(include_inactive=False):
    with connection() as c:
        pts=[dict(r) for r in c.execute('SELECT * FROM crack_points '+('' if include_inactive else 'WHERE active=1')+' ORDER BY name')]
        for p in pts:
            ms=[dict(r) for r in c.execute('SELECT * FROM crack_measurements WHERE crack_point_id=? ORDER BY measured_at,id',(p['id'],))]
            p['measurements']=ms;p['count']=len(ms);p['latest']=ms[-1] if ms else None;p['baseline']=ms[0]['value'] if ms else p['reference_value']
            p['delta']=p['latest']['value']-p['baseline'] if p['latest'] and p['baseline'] is not None else None
            p['min']=min((m['value'] for m in ms),default=None);p['max']=max((m['value'] for m in ms),default=None);p['mean']=mean([m['value'] for m in ms]) if ms else None
    return pts
def crack_point(pid):
    with connection() as c:
        r=c.execute('SELECT * FROM crack_points WHERE id=?',(pid,)).fetchone()
        if not r:return None
        p=dict(r);p['measurements']=[dict(x) for x in c.execute('SELECT * FROM crack_measurements WHERE crack_point_id=? ORDER BY measured_at,id',(pid,))]
    p['baseline']=p['measurements'][0]['value'] if p['measurements'] else p['reference_value']
    for m in p['measurements']:m['delta']=m['value']-p['baseline'] if p['baseline'] is not None else None
    p['latest']=p['measurements'][-1] if p['measurements'] else None;p['delta']=p['latest']['value']-p['baseline'] if p['latest'] and p['baseline'] is not None else None
    return p
