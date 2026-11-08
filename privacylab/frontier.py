"""Exact all-factor upper envelopes for small supplied finite channels."""
from fractions import Fraction as F
from itertools import combinations
from .core import encode, rational, validate_channel


def _model(channel):
    c=validate_channel(channel)
    if len(c['secrets'])>4 or len(c['outputs'])>8:
        raise ValueError('frontier is limited to 4 secrets and 8 outputs')
    return c


def _value(curve,t):
    for s in curve:
        if F(s['lower'])<=t and (s['upper'] is None or t<=F(s['upper'])):
            return F(s['intercept'])-F(s['slope_magnitude'])*t
    raise AssertionError('frontier domain gap')


def _point(c,t):
    pairs=[]
    for edge in c['neighbors']:
        for i,j in [edge,edge[::-1]]:
            p,q=c['probabilities'][i],c['probabilities'][j]
            excess=[a-t*b for a,b in zip(p,q)];event=[k for k,v in enumerate(excess) if v>0]
            pp=sum((p[k] for k in event),F(0));qq=sum((q[k] for k in event),F(0))
            pairs.append(dict(from_index=i,to_index=j,delta=str(pp-t*qq),event_indices=event,
                              event_p=str(pp),event_q=str(qq),ties=[k for k,v in enumerate(excess) if v==0],
                              terms=[dict(p=str(a),q=str(b),excess=str(v),positive_part=str(max(F(0),v)))
                                     for a,b,v in zip(p,q,excess)]))
    maximum=max(F(p['delta']) for p in pairs)
    return dict(factor=str(t),delta=str(maximum),pairs=pairs,
                worst_pairs=[k for k,p in enumerate(pairs) if F(p['delta'])==maximum])


def _line(p,q,t):
    active=[k for k,(a,b) in enumerate(zip(p,q)) if a>t*b]
    return sum((p[k] for k in active),F(0)),sum((q[k] for k in active),F(0)),active


def frontier(channel):
    """Complete worst-directed-neighbor profile for every finite factor t>=1.

    Ratio knots alone do not determine the global envelope: different pair
    profiles can cross inside a ratio cell. All line intersections are considered.
    Each resulting affine piece is certified over its entire interval by endpoint
    domination of every overlapping local affine piece, with a tail slope check.
    """
    c=_model(channel);pairs=[];grid={F(1)};pure=F(1);mismatch=False
    for edge in c['neighbors']:
        for i,j in [edge,edge[::-1]]:
            p,q=c['probabilities'][i],c['probabilities'][j]
            ratios=sorted({a/b for a,b in zip(p,q) if b and a/b>1})
            grid.update(ratios);pure=max([pure]+ratios)
            singular=sum((a for a,b in zip(p,q) if not b),F(0));mismatch|=bool(singular)
            starts=[F(1)]+ratios;local=[]
            for k,l in enumerate(starts):
                u=starts[k+1] if k+1<len(starts) else None;probe=(l+u)/2 if u is not None else l+1
                a,b,active=_line(p,q,probe)
                local.append(dict(lower=str(l),upper=None if u is None else str(u),intercept=str(a),slope_magnitude=str(b),
                                  active_outputs=active))
            pairs.append(dict(from_index=i,to_index=j,singular_mass=str(singular),ratio_knots=[str(v) for v in ratios],segments=local))
    knots=sorted(grid);pieces=[]
    for k,l in enumerate(knots):
        u=knots[k+1] if k+1<len(knots) else None;probe=(l+u)/2 if u is not None else l+1
        lines=[_line(c['probabilities'][p['from_index']],c['probabilities'][p['to_index']],probe)[:2] for p in pairs]
        cuts={l}
        if u is not None:cuts.add(u)
        for (a,b),(aa,bb) in combinations(lines,2):
            if b!=bb:
                cross=(a-aa)/(b-bb)
                if cross>l and (u is None or cross<u):cuts.add(cross)
        starts=sorted(cuts)
        intervals=list(zip(starts,starts[1:]))
        if u is None:intervals.append((starts[-1],None))
        for left,right in intervals:
            x=(left+right)/2 if right is not None else left+1
            values=[a-b*x for a,b in lines];v=max(values);w=[i for i,value in enumerate(values) if value==v]
            a,b=lines[w[0]]
            item=dict(lower=str(left),upper=None if right is None else str(right),intercept=str(a),slope_magnitude=str(b),
                      interior_worst_pairs=w)
            if pieces and all(pieces[-1][f]==item[f] for f in ['intercept','slope_magnitude','interior_worst_pairs']):
                assert pieces[-1]['upper']==item['lower'];pieces[-1]['upper']=item['upper']
            else:pieces.append(item)
    # Certify every whole global interval, not just a convenient sample point.
    for segment in pieces:
        l=F(segment['lower']);u=None if segment['upper'] is None else F(segment['upper'])
        a,b=F(segment['intercept']),F(segment['slope_magnitude']);proof=[]
        for k,pair in enumerate(pairs):
            overlaps=[]
            for local in pair['segments']:
                ll=max(l,F(local['lower']));uu=None if u is None and local['upper'] is None else min(
                    v for v in [u,None if local['upper'] is None else F(local['upper'])] if v is not None)
                if uu is not None and ll>=uu:continue
                aa,bb=F(local['intercept']),F(local['slope_magnitude'])
                start=(a-aa)+(bb-b)*ll;end=None if uu is None else (a-aa)+(bb-b)*uu
                tail_slope=None if uu is not None else bb-b
                assert start>=0 and (end>=0 if end is not None else tail_slope>=0)
                overlaps.append(dict(lower=str(ll),upper=None if uu is None else str(uu),
                                     start_slack=str(start),end_slack=None if end is None else str(end),
                                     tail_slope_slack=None if tail_slope is None else str(tail_slope)))
            assert overlaps
            proof.append(dict(pair_index=k,overlaps=overlaps))
        segment['dominance']=proof
    for a,b in zip(pieces,pieces[1:]):
        x=F(a['upper']);assert a['upper']==b['lower'] and F(a['intercept'])-F(a['slope_magnitude'])*x==F(b['intercept'])-F(b['slope_magnitude'])*x
        assert F(a['slope_magnitude'])>=F(b['slope_magnitude'])
    plateau=max(F(p['singular_mass']) for p in pairs)
    assert pieces[-1]['upper'] is None and F(pieces[-1]['slope_magnitude'])==0 and F(pieces[-1]['intercept'])==plateau
    return dict(schema_version=1,channel=encode(c),domain='all finite exact multiplicative factors t >= 1, not epsilon',
                scope='complete profile of supplied finite table and listed neighbor edges only; frontier input limited to 4 secrets / 8 outputs',
                pair_curves=pairs,segments=pieces,ratio_grid=[str(v) for v in knots],
                knots=[dict(factor=s['lower'],point=_point(c,F(s['lower']))) for s in pieces],
                plateau=str(plateau),pure_factor=None if mismatch else str(pure),
                plateau_pairs=[k for k,p in enumerate(pairs) if F(p['singular_mass'])==plateau],
                unlisted_secret_pairs=[list(e) for e in combinations(range(len(c['secrets'])),2) if list(e) not in c['neighbors']])


def _invert(profile,target):
    d=rational(target,'target delta');c=_model(dict(profile['channel'],probabilities=[[F(v) for v in row] for row in profile['channel']['probabilities']]));plateau=F(profile['plateau'])
    if d<plateau:
        k=profile['plateau_pairs'][0];pair=profile['pair_curves'][k];p=c['probabilities'][pair['from_index']];q=c['probabilities'][pair['to_index']]
        event=[i for i,(a,b) in enumerate(zip(p,q)) if a and not b]
        return dict(status='unattainable',target_delta=str(d),factor=None,point=None,
                    reason='target is below an invariant singular-support mass',
                    obstruction=dict(pair_index=k,event_indices=event,p_mass=str(sum((p[i] for i in event),F(0))),q_mass='0'))
    for k,s in enumerate(profile['segments']):
        l=F(s['lower']);u=None if s['upper'] is None else F(s['upper']);a,b=F(s['intercept']),F(s['slope_magnitude'])
        if a-b*l<=d:
            value=l;break
        if b and (u is None or a-b*u<=d):
            value=(a-d)/b;break
    else:raise AssertionError('attainable target missing from frontier')
    point=_point(c,value);assert F(point['delta'])<=d and value>=1
    if value==1:certificate=dict(kind='domain_lower_bound',lower_factor='1')
    else:
        left=next(s for s in profile['segments'] if F(s['lower'])<value and (s['upper'] is None or value<=F(s['upper'])))
        a,b=F(left['intercept']),F(left['slope_magnitude']);assert b>0 and a-b*value==d
        certificate=dict(kind='positive_left_slope',interval_lower=left['lower'],interval_upper=left['upper'],
                         intercept=str(a),slope_magnitude=str(b),root=str((a-d)/b),
                         supporting_pair_indices=left['interior_worst_pairs'])
    return dict(status='minimum_attained',target_delta=str(d),factor=str(value),point=point,minimality=certificate,
                within_point_audit_domain=value<=10**12 and max(value.numerator.bit_length(),value.denominator.bit_length())<=512,
                factor_note='exact mathematical factor; the original audit() keeps its separate 10^12 factor cap and 512-bit factor component limit')


def minimum_factor(channel,target_delta):
    profile=frontier(channel)
    return dict(schema_version=1,frontier=profile,inverse=_invert(profile,target_delta))


def frontier_demo():
    def ch(rows,edges=None):return dict(schema_version=1,secrets=[f's{i}' for i in range(len(rows))],outputs=[f'y{i}' for i in range(len(rows[0]))],
                                      neighbors=edges or [[i,i+1] for i in range(len(rows)-1)],probabilities=rows)
    rr=ch([['3/4','1/4'],['1/4','3/4']])
    singular=ch([['1/2',0,'1/2'],[0,'1/2','1/2']])
    # Finite but very large privacy factor, outside the original point audit cap.
    tiny=F(1,10**30);large=ch([[F(1,2),F(1,2)],[tiny,1-tiny]])
    crossing=ch([['1/16','5/16','1/8','1/2'],['5/16','3/8','1/16','1/4'],['1/8','5/16','3/16','3/8']],[[0,1],[1,2]])
    controls=[]
    for name,c,targets in [('randomized response',rr,[0,'1/4','1/2']),('singular plateau',singular,['1/4','1/2']),
                           ('neighbor envelope switches',crossing,[0,'15/64','1/4','1/2']),('large exact factor',large,[0,'1/4'])]:
        p=frontier(c);controls.append(dict(name=name,profile=p,queries=[_invert(p,v) for v in targets]))
    return dict(schema_version=1,description='Exact developed finite-channel frontiers and inverse delta budgets',controls=controls)
