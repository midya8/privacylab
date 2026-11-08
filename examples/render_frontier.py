"""All-factor finite privacy frontier, exact inverse cells and lossless metadata."""
import argparse
import base64
from fractions import Fraction as F
import html
import json
from pathlib import Path
import sys
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from privacylab import frontier_demo


def xy(t,delta):return 150+216*(float(t)-1),510-768*float(delta)


def pair_points(pair):
    starts=sorted({F(1),F(5)}|{F(s['lower']) for s in pair['segments'] if 1<=F(s['lower'])<=5})
    values=[]
    for t in starts:
        s=next(v for v in pair['segments'] if F(v['lower'])<=t and (v['upper'] is None or t<=F(v['upper'])))
        values.append(xy(t,F(s['intercept'])-F(s['slope_magnitude'])*t))
    return values


def query_cells(report):
    controls=report['controls'];cross=controls[2]
    return [(f'Envelope delta {q["target_delta"]}',q['factor'],'positive left-slope root') for q in cross['queries'] if q['target_delta'] in ['1/4','15/64','0']]+[
        ('Singular delta 1/4','unattainable','singular mass = 1/2'),
        ('Large-factor delta 0',controls[3]['queries'][0]['factor'],'outside point-audit domain')]


def render(report):
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1110" viewBox="0 0 1120 1110"><rect width="1120" height="1110" fill="#f4efec"/><rect x="16" y="16" width="1088" height="1078" rx="22" fill="white"/><g font-family="Arial,sans-serif">']
    def t(x,y,v,size=17,fill='#251f21',weight='400',extra=''):
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" {extra}>{html.escape(str(v))}</text>')
    payload=base64.b64encode(zlib.compress(json.dumps(report,sort_keys=True,separators=(',',':')).encode(),9)).decode()
    out.append('<metadata id="full-frontier-report" data-encoding="zlib-base64-json">'+payload+'</metadata>')
    t(48,62,'PrivacyLab / the worst neighbor can change',30,weight='600')
    t(48,96,'Exact all-factor upper envelopes, whole-interval certificates and inverse delta budgets.',18,'#585254')
    t(48,143,'1  A global breakpoint that no individual likelihood-ratio grid contains',21,weight='600')
    t(150,201,'delta(t)',17,'#585254');t(600,201,'gray: directed pair profiles | green: their maximum',16,'#585254')
    out.append('<path d="M 150 250 L 150 510 L 1030 510" stroke="#b9b4b6" fill="none"/>')
    for d,label in [(F(0),'0'),(F(1,8),'1/8'),(F(1,4),'1/4'),(F(5,16),'5/16')]:
        yy=xy(F(1),d)[1];out.append(f'<line x1="150" y1="{yy:.3f}" x2="1014" y2="{yy:.3f}" stroke="#ebe7e8"/>');t(98,yy+5,label,15,'#585254')
    p=report['controls'][2]['profile']
    for i,pair in enumerate(p['pair_curves']):
        points=' '.join(f'{x:.3f},{y:.3f}' for x,y in pair_points(pair))
        out.append(f'<polyline id="directed-curve-{i}" points="{points}" fill="none" stroke="#b9b4b6" stroke-width="2"/>')
    points=[]
    for knot in p['knots']:
        tt=F(knot['factor']);dd=F(knot['point']['delta']);points.append(xy(tt,dd))
    out.append('<polyline id="global-frontier" points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in points)+'" fill="none" stroke="#317e6b" stroke-width="5"/>')
    for i,(x,y) in enumerate(points):out.append(f'<circle id="frontier-knot-{i}" cx="{x:.3f}" cy="{y:.3f}" r="5" fill="#317e6b"/>')
    for v in [F(1),F(5,4),F(2),F(3),F(5)]:
        xx=xy(v,F(0))[0];t(xx-10,539,str(v),15,'#585254')
    t(1034,539,'t',16,'#585254');t(247,288,'pair 0 -> pair 1 at t = 5/4',18,'#317e6b','600')
    t(48,580,'delta = 5/8 - 5t/16 on [1,5/4]; then 5/16 - t/16 on [5/4,5]; then zero.',18,weight='600')
    t(48,613,'5/4 is absent from the ratio grid {1, 6/5, 3/2, 2, 5/2, 3, 5}. Cross-pair envelopes matter.',17,'#585254')
    t(48,659,'2  The smallest factor meeting a target delta, or an exact obstruction',21,weight='600')
    for x,v in zip([58,360,730],['Developed query','Minimum factor','Certificate']):t(x,702,v,16,'#585254')
    for i,(name,value,note) in enumerate(query_cells(report)):
        yy=744+42*i;t(58,yy,name,17,extra=f'id="frontier-query-{i}-0"');t(360,yy,value,17,'#317e6b' if value!='unattainable' else '#bd2632','600',f'id="frontier-query-{i}-1"');t(730,yy,note,16,'#585254')
    t(48,988,'Each affine piece dominates every local piece over its whole interval, including the infinite tail.',17,'#585254')
    t(48,1021,'All factors are multiplicative t = exp(epsilon), not epsilon. No new privacy theorem is claimed.',17,'#585254')
    out.append('<line x1="48" y1="1042" x2="1072" y2="1042" stroke="#eae9ea"/>')
    t(48,1073,'Small supplied finite tables only: at most 4 secrets / 8 outputs. Not a sampler, model or production accountant.',16,'#585254')
    out.append('</g></svg>')
    return '\n'.join(out)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    target=Path(__file__).resolve().parents[1]/'assets/factor-frontier.svg';output=render(frontier_demo())
    if a.check:
        if target.read_text()!=output:raise SystemExit('frontier figure differs from exact report')
    else:target.write_text(output)


if __name__=='__main__':main()
