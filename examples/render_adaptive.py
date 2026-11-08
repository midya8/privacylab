"""Exact adaptive transcript comparison with complete report metadata."""
import argparse
import base64
import html
import json
from pathlib import Path
import sys
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from privacylab import adaptive_demo


def render(report):
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1110" viewBox="0 0 1120 1110"><rect width="1120" height="1110" fill="#f4efec"/><rect x="16" y="16" width="1088" height="1078" rx="22" fill="white"/><g font-family="Arial,sans-serif">']
    def t(x,y,value,size=17,fill='#251f21',weight='400',extra=''):
        out.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" {extra}>{html.escape(str(value))}</text>')
    payload=base64.b64encode(zlib.compress(json.dumps(report,sort_keys=True,separators=(',',':')).encode(),9)).decode()
    out.append('<metadata id="full-adaptive-report" data-encoding="zlib-base64-json">'+payload+'</metadata>')
    t(48,62,'PrivacyLab / adaptation needs conditional laws',30,weight='600')
    t(48,96,'Unfold every transcript. Keep every killed-mass witness. Do not compose marginals.',18,'#585254')
    t(48,139,'1  Actual loss and three valid, sometimes loose, upper bounds',21,weight='600')
    for x,v in zip([58,485,610,745,875,995],['Developed tree','Factor T','Actual','Clipped','Uniform','Additive']):t(x,182,v,16,'#585254')
    names=['Independent pure RR','Adaptive RR or constant','Independent at factor one','Branch-weighted reveal','Unreachable reveal','Shared coin: conditional failure']
    for i,(name,c) in enumerate(zip(names,report['controls'])):
        yy=224+44*i;t(58,yy,name,17,weight='600' if i>=3 else '400')
        r=c['report'];values=[r['product_factor'],r['joint_audit']['delta'],r['clipped_delta_bound'],r['uniform_survival_bound'],r['additive_bound']]
        for j,(xx,v) in enumerate(zip([485,610,745,875,995],values)):
            color='#bd2632' if i==5 else '#317e6b' if i in [3,4] else '#251f21'
            t(xx,yy,v,18,color,'600' if i>=3 else '400',f'id="adaptive-cell-{i}-{j}"')
    t(48,518,'Every row: actual delta <= clipped deficit <= uniform bound <= additive bound.',18,weight='600')
    t(48,550,'T is the product of fixed round factors, not epsilon. Uniform uses all histories, even null ones.',17,'#585254')
    t(48,596,'2  Weight the branch before charging its conditional failure',21,weight='600')
    t(48,632,'Branch-weighted control: first release is a fair coin, independent of the secret.',17,'#585254')
    out.append('<path id="branch-left" d="M 548 673 L 290 747" fill="none" stroke="#317e6b" stroke-width="3"/>')
    out.append('<path id="branch-right" d="M 572 673 L 830 747" fill="none" stroke="#317e6b" stroke-width="3"/>')
    t(520,672,'root',20,weight='600')
    r=report['controls'][3]['report'];flow=r['pairs'][0]['flow']
    for i,(cx,rec,name) in enumerate(zip([290,830],flow[1:],['history [0]: reveal secret','history [1]: constant'])):
        t(cx-144,775,name,18,weight='600')
        vals=[rec['good_mass_in'],rec['conditional_delta'],rec['removed_mass']]
        for j,(label,value) in enumerate(zip(['incoming mass','local delta','removed mass'],vals)):
            y=810+32*j;t(cx-144,y,label,17,'#585254');t(cx+64,y,value,18,'#317e6b','600',f'id="branch-value-{i}-{j}"')
    t(48,935,'Total removed mass = 1/2, not the worst conditional delta 1 charged to every branch.',18,weight='600')
    t(48,972,'An impossible bad history still gets audited, but has zero incoming mass and zero charge.',17,'#585254')
    t(48,1006,'The shared-coin control instead has deterministic disclosure at reachable conditional nodes.',17,'#585254')
    out.append('<line x1="48" y1="1035" x2="1072" y2="1035" stroke="#eae9ea"/>')
    t(48,1069,'Finite supplied kernels only. No sampler verification, privacy filter, odometer or new composition theorem.',16,'#585254')
    out.append('</g></svg>')
    return '\n'.join(out)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    target=Path(__file__).resolve().parents[1]/'assets/adaptive-transcripts.svg';output=render(adaptive_demo())
    if a.check:
        if target.read_text()!=output:raise SystemExit('adaptive figure differs from exact report')
    else:target.write_text(output)


if __name__=='__main__':main()
