from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image as RLImage

def f(v,n=3):return '–' if v is None else f'{v:.{n}f}'
def table(rows,widths=None):
    t=Table(rows,repeatRows=1,colWidths=widths);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17365d')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),.25,colors.grey),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP')]));return t
def level_pdf(cs,analysis):
    b=BytesIO();d=SimpleDocTemplate(b,pagesize=A4,rightMargin=12*mm,leftMargin=12*mm,topMargin=12*mm,bottomMargin=12*mm);s=getSampleStyleSheet();story=[Paragraph('Hausmonitor V4 – Nivellement-Bericht',s['Title']),Paragraph('Statistische Auswertung. Kein statischer oder geotechnischer Nachweis.',s['BodyText']),Spacer(1,4*mm)]
    rows=[['Datum','Haus','Haus Δ','SE','Terrasse','Terr. Δ','GW','Luft']]
    for c in cs:rows.append([c['measured_at'].replace('T',' '),f(c['stats']['house']['value']),f(c['stats']['house']['delta']),f(c['stats']['house']['se']),f(c['stats']['terrace']['value']),f(c['stats']['terrace']['delta']),f(c['groundwater']),f(c['air_temp'],1)])
    story.append(table(rows,[31*mm,20*mm,19*mm,17*mm,21*mm,20*mm,18*mm,17*mm]));story+=[Spacer(1,4*mm),Paragraph('Trend und Korrelation',s['Heading2'])]
    for label,key in [('Zeittrend','time'),('Grundwasser','groundwater'),('Lufttemperatur','air_temp'),('Wandtemperaturdifferenz','wall_delta')]:
        a=analysis.get(key);story.append(Paragraph(f'<b>{label}:</b> '+('nicht auswertbar' if not a else f"n={a['n']}, Steigung={f(a['slope'],4)}, R²={f(a['r2'])}"),s['BodyText']))
    d.build(story);b.seek(0);return b
def cracks_pdf(points,upload_dir):
    b=BytesIO();d=SimpleDocTemplate(b,pagesize=A4,rightMargin=14*mm,leftMargin=14*mm,topMargin=14*mm,bottomMargin=14*mm);s=getSampleStyleSheet();story=[Paragraph('Hausmonitor V4 – Rissmonitoring-Bericht',s['Title']),Paragraph('Dokumentation der Messstellen und zeitlichen Entwicklung.',s['BodyText']),Spacer(1,4*mm)]
    for pi,p in enumerate(points):
        story+=[Paragraph(p['name'],s['Heading2']),Paragraph(f"Ort: {p['location'] or '–'}<br/>Beschreibung: {p['description'] or '–'}<br/>Startwert: {f(p['baseline'])} {p['unit']}<br/>Aktuelle Änderung: {f(p['delta'])} {p['unit']}",s['BodyText'])]
        rows=[['Datum','Luft °C','Messwert','Δ Start','Notiz']]
        for m in p['measurements']:rows.append([m['measured_at'].replace('T',' '),f(m['air_temp'],1),f(m['value']),f(m['value']-p['baseline'] if p['baseline'] is not None else None),m['notes'] or ''])
        story.append(table(rows,[38*mm,23*mm,25*mm,25*mm,65*mm]))
        for m in p['measurements']:
            if m['photo_filename']:
                path=upload_dir/m['photo_filename']
                if path.exists():
                    story+=[Spacer(1,3*mm),Paragraph(f"Foto {m['measured_at'].replace('T',' ')}",s['Heading4']),RLImage(str(path),width=80*mm,height=60*mm,kind='proportional')]
        if pi<len(points)-1:story.append(PageBreak())
    d.build(story);b.seek(0);return b
