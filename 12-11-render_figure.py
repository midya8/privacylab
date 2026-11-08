"""Exact finite-channel privacy figure with complete lossless audit metadata."""
import argparse
import base64
import html
import json
from pathlib import Path
import sys
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from privacylab import demo


def render(report):
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1050" viewBox="0 0 1120 1050"><rect width="1120" height="1050" fill="#f4efec"/><rect x="16" y="16" width="1088" height="1018" rx="22" fill="white"/><g font-family="Arial,sans-serif">']
    def t(x,y,value,size=17,fill='#251f21',weight='400',extra=''):
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" {extra}>{html.escape(str(value))}</text>')
    payload=base64.b64encode(zlib.compress(json.dumps(report,sort_keys=True,separators=(',',':')).encode(),9)).decode()
    out.append('<metadata id="full-privacy-report" data-encoding="zlib-base64-json">'+payload+'</metadata>')
    t(48,62,'PrivacyLab / private marginals can leak jointly',30,weight='600')
    t(48,96,'Exact rational finite-channel privacy factors, attaining events and randomness assumptions.',18,'#585254')
    t(48,139,'1  Marginal guarantees are not a license to compose shared coins',21,weight='600')
    for x,v in zip([58,468,655,805,955],['Developed channel','Pure factor','delta (t=1)','delta (t=3)','delta (t=9)']):t(x,182,v,16,'#585254')
    names=['Randomized response','Two independent releases','Vote + fresh tie-break','Parity only','Shared coin: first marginal','Shared coin: second marginal','Shared coin: joint release']
    for i,(name,row)in enumerate(zip(names,report['controls'])):
        yy=222+42*i;t(58,yy,name,17,weight='600'if i==6 else '400')
        values=[row['audits'][0]['pure_factor']or'infinite']+[r['delta']for r in row['audits']]
        for j,(xx,v)in enumerate(zip([468,655,805,955],values)):
            color='#bd2632'if i==6 else('#317e6b'if i==3 else'#251f21')
            t(xx,yy,v,17,color,'600'if i in [3,6]else'400',f'id="privacy-cell-{i}-{j}"')
    t(48,516,'t = exp(epsilon), NOT epsilon. Pure factors 3 and 9 mean epsilon = ln(3) and ln(9).',18,weight='600')
    t(48,548,'delta(t) is the maximum sum of positive P - tQ terms over both neighbor directions.',17,'#585254')
    t(48,595,'2  A = secret XOR Z, B = Z: the joint release recovers the secret',21,weight='600')
    t(58,639,'Joint output (A, B)',16,'#585254')
    for xx,label in zip([470,620,770,920],['00','01','10','11']):t(xx,639,label,17,weight='600')
    joint=report['controls'][-1]['audits'][0]['channel']
    for i,row in enumerate(joint['probabilities']):
        yy=683+45*i;t(58,yy,'P(output | secret = '+str(i)+')',17)
        for j,(xx,v)in enumerate(zip([470,620,770,920],row)):
            t(xx,yy,v,18,'#317e6b'if v!='0'else'#585254','600'if v!='0'else'400',f'id="joint-cell-{i}-{j}"')
    t(48,775,'The rows have disjoint supports. delta(t) = 1 for every finite t.',18,weight='600')
    t(48,809,'Each marginal looks private, but conditioned on A = 0, B is 0 versus 1 deterministically.',17,'#585254')
    t(48,842,'This violates the required conditional-mechanism premise, not a composition theorem.',17,'#585254')
    t(48,891,'3  Postprocessing may reduce privacy loss, without promising utility',21,weight='600')
    t(48,927,'Fresh tie-breaking returns the original randomized-response channel; parity is secret-independent.',17,'#585254')
    t(48,958,'Certificates concern supplied tables and listed neighbors, not a deployed model or secure sampler.',17,'#585254')
    out.append('<line x1="48" y1="981" x2="1072" y2="981" stroke="#eae9ea"/>')
    t(48,1009,'Reproduce: python examples/render_figure.py --check | full exact event witnesses embedded',15,'#585254')
    out.append('</g></svg>')
    return '\n'.join(out)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    target=Path(__file__).resolve().parents[1]/'assets/privacy-audit.svg';output=render(demo())
    if a.check:
        if target.read_text()!=output:raise SystemExit('privacy figure differs from exact report')
    else:target.write_text(output)


if __name__=='__main__':main()
