import io,os
from PIL import Image
os.environ['DATABASE_PATH']='/tmp/hm4.db';os.environ['UPLOAD_DIR']='/tmp/hm4-uploads';os.environ['APP_PASSWORD']=''
from fastapi.testclient import TestClient
from app.main import app
from app.database import DB_PATH

def setup_module():
    if DB_PATH.exists():DB_PATH.unlink()
def png():
    b=io.BytesIO();Image.new('RGB',(20,20),'white').save(b,'PNG');return b.getvalue()
def test_all_modules_and_exports():
    with TestClient(app) as c:
        assert c.get('/health').json()['version']=='4.0.0'
        r=c.post('/level',data={'measured_at':'2026-10-02T10:00','air_temp':'16'},follow_redirects=False);cid=r.headers['location'].split('/')[2]
        c.post(f'/level/{cid}/readings',data={'SW':['2.575','2.58','2.58','2.575','2.585'],'SO':['8.27','8.27','8.275','8.28','8.275'],'TSW':['3','3.01','3','3','2.99'],'TSO':['9','9.01','9','9','8.99']})
        assert '5.695' in c.get(f'/level/{cid}').text
        c.post(f'/level/{cid}/photos',data={'point':'SW','caption':'Test'},files={'photo':('x.png',png(),'image/png')})
        assert c.get('/exports/nivellement.csv').status_code==200
        assert c.get('/reports/nivellement.pdf').content[:4]==b'%PDF'
        r=c.post('/cracks',data={'name':'R1','location':'Wohnzimmer','unit':'mm'},follow_redirects=False);pid=r.headers['location'].split('/')[2]
        c.post(f'/cracks/{pid}/measurements',data={'measured_at':'2026-10-02T11:00','air_temp':'20','value':'0.5','notes':'Start'},files={'photo':('r.png',png(),'image/png')})
        c.post(f'/cracks/{pid}/measurements',data={'measured_at':'2026-10-03T11:00','air_temp':'21','value':'0.7','notes':'Folge'})
        page=c.get(f'/cracks/{pid}');assert '0.200' in page.text
        assert c.get('/exports/risse.csv').status_code==200
        assert c.get('/reports/risse.pdf').content[:4]==b'%PDF'
