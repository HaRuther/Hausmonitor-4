from __future__ import annotations
import csv,hmac,io,os,uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI,File,Form,HTTPException,Request,UploadFile
from fastapi.responses import FileResponse,HTMLResponse,RedirectResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from starlette.middleware.sessions import SessionMiddleware
from .analytics import POINTS
from .database import LEVEL_UPLOAD_DIR,CRACK_UPLOAD_DIR,connection,init_db
from .repository import campaigns,grouped,level_analytics,crack_points,crack_point
from .pdf_reports import level_pdf,cracks_pdf
BASE=Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app):init_db();yield
app=FastAPI(title='Hausmonitor V4',version='4.0.0',lifespan=lifespan)
app.add_middleware(SessionMiddleware,secret_key=os.getenv('SECRET_KEY','change-me'),https_only=os.getenv('COOKIE_SECURE','false').lower()=='true',same_site='lax')
app.mount('/static',StaticFiles(directory=BASE/'static'),name='static');templates=Jinja2Templates(directory=BASE/'templates')
def guard(r):
    if os.getenv('APP_PASSWORD','') and not r.session.get('authenticated'):return RedirectResponse('/login',303)
def save_image(raw,content_type,prefix,directory):
    if content_type not in {'image/jpeg','image/png','image/webp'}:raise HTTPException(400,'Nur JPG, PNG oder WebP')
    if len(raw)>15*1024*1024:raise HTTPException(400,'Bild ist größer als 15 MB')
    Image.open(io.BytesIO(raw)).verify();ext={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}[content_type];name=f'{prefix}-{uuid.uuid4().hex}{ext}';(directory/name).write_bytes(raw);return name
@app.get('/health')
def health():return {'status':'ok','version':'4.0.0'}
@app.get('/login',response_class=HTMLResponse)
def login_page(request:Request):return templates.TemplateResponse(request=request,name='login.html',context={'error':None})
@app.post('/login')
def login(request:Request,password:str=Form(...)):
    if hmac.compare_digest(password,os.getenv('APP_PASSWORD','')):request.session['authenticated']=True;return RedirectResponse('/',303)
    return templates.TemplateResponse(request=request,name='login.html',context={'error':'Passwort ist falsch.'},status_code=401)
@app.post('/logout')
def logout(request:Request):request.session.clear();return RedirectResponse('/login',303)
@app.get('/',response_class=HTMLResponse)
def home(request:Request):
    if (r:=guard(request)):return r
    cs=campaigns();pts=crack_points();return templates.TemplateResponse(request=request,name='home.html',context={'latest':cs[-1] if cs else None,'campaign_count':len(cs),'crack_count':len(pts),'crack_measurement_count':sum(p['count'] for p in pts)})
@app.get('/level',response_class=HTMLResponse)
def level_dashboard(request:Request):
    if (r:=guard(request)):return r
    cs=campaigns();an=level_analytics(cs);latest=cs[-1] if cs else None;chart=[{'date':c['measured_at'],'delta':c['stats']['house']['delta'],'low':c['stats']['house']['delta']-c['stats']['house']['se'] if c['stats']['house']['delta'] is not None and c['stats']['house']['se'] is not None else None,'high':c['stats']['house']['delta']+c['stats']['house']['se'] if c['stats']['house']['delta'] is not None and c['stats']['house']['se'] is not None else None,'terrace':c['stats']['terrace']['delta'],'groundwater':c['groundwater'],'air_temp':c['air_temp']} for c in cs]
    return templates.TemplateResponse(request=request,name='level_dashboard.html',context={'campaigns':list(reversed(cs)),'latest':latest,'analysis':an,'chart':chart})
@app.get('/level/new',response_class=HTMLResponse)
def level_new(request:Request):
    if (r:=guard(request)):return r
    return templates.TemplateResponse(request=request,name='campaign_form.html',context={'now':datetime.now().strftime('%Y-%m-%dT%H:%M')})
@app.post('/level')
def level_create(request:Request,measured_at:str=Form(...),air_temp:float|None=Form(None),wall_temp_sw:float|None=Form(None),wall_temp_so:float|None=Form(None),groundwater:float|None=Form(None),rainfall_14d:float|None=Form(None),weather:str=Form(''),light_mode:str=Form(''),notes:str=Form('')):
    if (r:=guard(request)):return r
    with connection() as c:cid=c.execute('INSERT INTO campaigns(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes) VALUES(?,?,?,?,?,?,?,?,?)',(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes)).lastrowid
    return RedirectResponse(f'/level/{cid}/readings',303)
@app.get('/level/{cid}/readings',response_class=HTMLResponse)
def level_readings_page(request:Request,cid:int):
    if (r:=guard(request)):return r
    with connection() as c:row=c.execute('SELECT * FROM campaigns WHERE id=?',(cid,)).fetchone()
    if not row:raise HTTPException(404)
    return templates.TemplateResponse(request=request,name='readings_form.html',context={'campaign':dict(row),'points':POINTS,'existing':grouped(cid)})
@app.post('/level/{cid}/readings')
async def level_readings_save(request:Request,cid:int):
    if (r:=guard(request)):return r
    form=await request.form()
    with connection() as c:
        c.execute('DELETE FROM readings WHERE campaign_id=?',(cid,))
        for p in POINTS:
            seq=0
            for raw in form.getlist(p):
                raw=str(raw).strip().replace(',','.')
                if raw:seq+=1;c.execute('INSERT INTO readings(campaign_id,point,sequence,value) VALUES(?,?,?,?)',(cid,p,seq,float(raw)))
    return RedirectResponse(f'/level/{cid}',303)
@app.get('/level/{cid}',response_class=HTMLResponse)
def level_detail(request:Request,cid:int):
    if (r:=guard(request)):return r
    camp=next((x for x in campaigns() if x['id']==cid),None)
    if not camp:raise HTTPException(404)
    with connection() as c:photos=[dict(x) for x in c.execute('SELECT * FROM photos WHERE campaign_id=? ORDER BY id',(cid,))]
    return templates.TemplateResponse(request=request,name='campaign_detail.html',context={'campaign':camp,'readings':grouped(cid),'photos':photos})
@app.post('/level/{cid}/photos')
async def level_photo(request:Request,cid:int,point:str=Form(...),caption:str=Form(''),photo:UploadFile=File(...)):
    if (r:=guard(request)):return r
    name=save_image(await photo.read(),photo.content_type,f'level-{cid}',LEVEL_UPLOAD_DIR)
    with connection() as c:c.execute('INSERT INTO photos(campaign_id,point,filename,caption) VALUES(?,?,?,?)',(cid,point,name,caption))
    return RedirectResponse(f'/level/{cid}',303)
@app.get('/level-uploads/{name}')
def level_photo_get(request:Request,name:str):
    if (r:=guard(request)):return r
    path=LEVEL_UPLOAD_DIR/Path(name).name
    if not path.exists():raise HTTPException(404)
    return FileResponse(path)
@app.post('/level/{cid}/delete')
def level_delete(request:Request,cid:int):
    if (r:=guard(request)):return r
    with connection() as c:files=[x['filename'] for x in c.execute('SELECT filename FROM photos WHERE campaign_id=?',(cid,))];c.execute('DELETE FROM campaigns WHERE id=?',(cid,))
    for name in files:(LEVEL_UPLOAD_DIR/name).unlink(missing_ok=True)
    return RedirectResponse('/level',303)
@app.get('/exports/nivellement.csv')
def level_csv(request:Request):
    if (r:=guard(request)):return r
    out=io.StringIO();w=csv.writer(out,delimiter=';');w.writerow(['ID','Zeitpunkt','Luft °C','Wand SW °C','Wand SO °C','Grundwasser','Regen 14d','Wetter','Licht','Notiz','SW1','SW2','SW3','SW4','SW5','SO1','SO2','SO3','SO4','SO5','ANB1','ANB2','ANB3','ANB4','ANB5','TSW1','TSW2','TSW3','TSW4','TSW5','TSO1','TSO2','TSO3','TSO4','TSO5','Haus','Haus Δ','Haus SE','Terrasse','Terrasse Δ'])
    for c in campaigns():
        g=grouped(c['id']);vals=lambda p:g[p]+['']*(5-len(g[p]));w.writerow([c['id'],c['measured_at'],c['air_temp'],c['wall_temp_sw'],c['wall_temp_so'],c['groundwater'],c['rainfall_14d'],c['weather'],c['light_mode'],c['notes'],*vals('SW'),*vals('SO'),*vals('ANB'),*vals('TSW'),*vals('TSO'),c['stats']['house']['value'],c['stats']['house']['delta'],c['stats']['house']['se'],c['stats']['terrace']['value'],c['stats']['terrace']['delta']])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=nivellement.csv'})
@app.post('/imports/nivellement.csv')
async def level_import(request:Request,file:UploadFile=File(...)):
    if (r:=guard(request)):return r
    rows=csv.DictReader(io.StringIO((await file.read()).decode('utf-8-sig')),delimiter=';')
    with connection() as c:
        for x in rows:
            if not x.get('Zeitpunkt'):continue
            cid=c.execute('INSERT INTO campaigns(measured_at,air_temp,wall_temp_sw,wall_temp_so,groundwater,rainfall_14d,weather,light_mode,notes) VALUES(?,?,?,?,?,?,?,?,?)',(x['Zeitpunkt'],x.get('Luft °C') or None,x.get('Wand SW °C') or None,x.get('Wand SO °C') or None,x.get('Grundwasser') or None,x.get('Regen 14d') or None,x.get('Wetter',''),x.get('Licht',''),x.get('Notiz',''))).lastrowid
            for p in POINTS:
                for i in range(1,6):
                    raw=x.get(f'{p}{i}','').strip().replace(',','.')
                    if raw:c.execute('INSERT INTO readings(campaign_id,point,sequence,value) VALUES(?,?,?,?)',(cid,p,i,float(raw)))
    return RedirectResponse('/level',303)
@app.get('/reports/nivellement.pdf')
def level_report(request:Request):
    if (r:=guard(request)):return r
    cs=campaigns();return StreamingResponse(level_pdf(cs,level_analytics(cs)),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename=nivellement-bericht.pdf'})
@app.get('/cracks',response_class=HTMLResponse)
def cracks_dashboard(request:Request):
    if (r:=guard(request)):return r
    pts=crack_points();chart=[{'id':p['id'],'name':p['name'],'unit':p['unit'],'measurements':[{'date':m['measured_at'],'value':m['value'],'delta':m['value']-p['baseline'] if p['baseline'] is not None else None,'air_temp':m['air_temp']} for m in p['measurements']]} for p in pts]
    return templates.TemplateResponse(request=request,name='cracks_dashboard.html',context={'points':pts,'crack_chart':chart})
@app.get('/cracks/new',response_class=HTMLResponse)
def crack_new(request:Request):
    if (r:=guard(request)):return r
    return templates.TemplateResponse(request=request,name='crack_point_form.html',context={})
@app.post('/cracks')
def crack_create(request:Request,name:str=Form(...),location:str=Form(''),description:str=Form(''),unit:str=Form('mm'),reference_value:float|None=Form(None)):
    if (r:=guard(request)):return r
    try:
        with connection() as c:pid=c.execute('INSERT INTO crack_points(name,location,description,unit,reference_value) VALUES(?,?,?,?,?)',(name.strip(),location,description,unit,reference_value)).lastrowid
    except Exception as e:
        if 'UNIQUE' in str(e):raise HTTPException(400,'Name existiert bereits')
        raise
    return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/cracks/{pid}',response_class=HTMLResponse)
def crack_detail(request:Request,pid:int):
    if (r:=guard(request)):return r
    p=crack_point(pid)
    if not p:raise HTTPException(404)
    chart=[{'date':m['measured_at'],'value':m['value'],'delta':m['delta'],'air_temp':m['air_temp']} for m in p['measurements']]
    return templates.TemplateResponse(request=request,name='crack_detail.html',context={'point':p,'crack_detail_chart':chart})
@app.get('/cracks/{pid}/new',response_class=HTMLResponse)
def crack_measurement_new(request:Request,pid:int):
    if (r:=guard(request)):return r
    p=crack_point(pid)
    if not p:raise HTTPException(404)
    return templates.TemplateResponse(request=request,name='crack_measurement_form.html',context={'point':p,'now':datetime.now().strftime('%Y-%m-%dT%H:%M')})
@app.post('/cracks/{pid}/measurements')
async def crack_measurement_create(request:Request,pid:int,measured_at:str=Form(...),air_temp:float|None=Form(None),value:float=Form(...),notes:str=Form(''),photo:UploadFile|None=File(None)):
    if (r:=guard(request)):return r
    if not crack_point(pid):raise HTTPException(404)
    name=None
    if photo and photo.filename:name=save_image(await photo.read(),photo.content_type,f'crack-{pid}',CRACK_UPLOAD_DIR)
    with connection() as c:c.execute('INSERT INTO crack_measurements(crack_point_id,measured_at,air_temp,value,notes,photo_filename) VALUES(?,?,?,?,?,?)',(pid,measured_at,air_temp,value,notes,name))
    return RedirectResponse(f'/cracks/{pid}',303)
@app.get('/crack-uploads/{name}')
def crack_photo_get(request:Request,name:str):
    if (r:=guard(request)):return r
    path=CRACK_UPLOAD_DIR/Path(name).name
    if not path.exists():raise HTTPException(404)
    return FileResponse(path)
@app.post('/cracks/{pid}/measurements/{mid}/delete')
def crack_measurement_delete(request:Request,pid:int,mid:int):
    if (r:=guard(request)):return r
    with connection() as c:r=c.execute('SELECT photo_filename FROM crack_measurements WHERE id=? AND crack_point_id=?',(mid,pid)).fetchone();c.execute('DELETE FROM crack_measurements WHERE id=? AND crack_point_id=?',(mid,pid))
    if r and r['photo_filename']:(CRACK_UPLOAD_DIR/r['photo_filename']).unlink(missing_ok=True)
    return RedirectResponse(f'/cracks/{pid}',303)
@app.post('/cracks/{pid}/archive')
def crack_archive(request:Request,pid:int):
    if (r:=guard(request)):return r
    with connection() as c:c.execute('UPDATE crack_points SET active=0 WHERE id=?',(pid,))
    return RedirectResponse('/cracks',303)
@app.get('/exports/risse.csv')
def cracks_csv(request:Request):
    if (r:=guard(request)):return r
    out=io.StringIO();w=csv.writer(out,delimiter=';');w.writerow(['Messstelle','Ort','Beschreibung','Einheit','Datum','Lufttemperatur','Messwert','Änderung ggü. Start','Notiz','Foto'])
    for p in crack_points(True):
        for m in p['measurements']:w.writerow([p['name'],p['location'],p['description'],p['unit'],m['measured_at'],m['air_temp'],m['value'],m['value']-p['baseline'] if p['baseline'] is not None else None,m['notes'],m['photo_filename']])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=rissmonitoring.csv'})
@app.get('/reports/risse.pdf')
def cracks_report(request:Request):
    if (r:=guard(request)):return r
    return StreamingResponse(cracks_pdf(crack_points(True),CRACK_UPLOAD_DIR),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename=rissmonitoring-bericht.pdf'})
