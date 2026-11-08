"""Exact finite-channel hockey-stick audits. No sampled privacy estimates."""
from fractions import Fraction as F
from itertools import combinations
import re


def rational(value, name='probability', *, factor=False):
    if isinstance(value, bool) or not isinstance(value, (int, str, F)):
        raise ValueError(name+' must be an integer, exact rational string or Fraction, not float/bool')
    if isinstance(value, str) and (len(value)>160 or re.fullmatch(r'(0|[1-9][0-9]*)(/[1-9][0-9]*|\.[0-9]+)?', value) is None):
        raise ValueError(name+' has invalid exact rational syntax')
    try:
        v=F(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(name+' is invalid') from exc
    if max(v.numerator.bit_length(),v.denominator.bit_length())>512:
        raise ValueError(name+' exceeds 512-bit rational limit')
    if not (1<=v<=10**12 if factor else 0<=v<=1):
        raise ValueError(name+' is out of range')
    return v


def labels(values, name, lower, upper):
    if (not isinstance(values,(list,tuple)) or not lower<=len(values)<=upper or
        any(not isinstance(v,str) or re.fullmatch(r'[A-Za-z0-9_.:/ -]{1,40}',v) is None for v in values) or
        len(set(values))!=len(values)):
        raise ValueError(name+' needs unique 1..40 character ASCII labels')
    return list(values)


def matrix(values, rows, cols):
    if not isinstance(values,(list,tuple)) or len(values)!=rows:
        raise ValueError('probability matrix row count mismatch')
    result=[]
    for row in values:
        if not isinstance(row,(list,tuple)) or len(row)!=cols:
            raise ValueError('probability matrix column count mismatch')
        row=[rational(v)for v in row]
        if sum(row,F(0))!=1:raise ValueError('probability rows must sum exactly to 1; never normalized')
        result.append(row)
    return result


def validate_channel(channel):
    if not isinstance(channel,dict) or set(channel)!={'schema_version','secrets','outputs','neighbors','probabilities'}:
        raise ValueError('channel needs exactly schema_version, secrets, outputs, neighbors, probabilities')
    if type(channel['schema_version'])is not int or channel['schema_version']!=1:
        raise ValueError('schema_version must be integer 1')
    secrets=labels(channel['secrets'],'secrets',2,8);outputs=labels(channel['outputs'],'outputs',1,64)
    edges=channel['neighbors']
    if not isinstance(edges,(list,tuple)) or not 1<=len(edges)<=28:raise ValueError('neighbors needs 1..28 undirected edges')
    canonical=[]
    for e in edges:
        if (not isinstance(e,(list,tuple)) or len(e)!=2 or any(type(i)is not int or not 0<=i<len(secrets)for i in e) or e[0]==e[1]):
            raise ValueError('neighbor edge needs two distinct valid integer secret indices')
        edge=sorted(e)
        if edge in canonical:raise ValueError('duplicate undirected neighbor edge')
        canonical.append(edge)
    return dict(schema_version=1,secrets=secrets,outputs=outputs,neighbors=sorted(canonical),
                probabilities=matrix(channel['probabilities'],len(secrets),len(outputs)))


def encode(channel):
    c=validate_channel(channel)
    return dict(c,probabilities=[[str(v)for v in row]for row in c['probabilities']])


def audit(channel, factor):
    """Smallest delta for t=factor=exp(epsilon), over the listed neighbor edges."""
    c=validate_channel(channel);t=rational(factor,'factor',factor=True)
    pairs=[];pure=F(1);singular=False;witnesses=[]
    for edge in c['neighbors']:
        for i,j in [edge,edge[::-1]]:
            p,q=c['probabilities'][i],c['probabilities'][j]
            terms=[];event=[];ties=[];mass=F(0);local_pure=F(1);local_singular=False
            for k,(a,b)in enumerate(zip(p,q)):
                excess=a-t*b
                if excess>0:event.append(k)
                if excess==0:ties.append(k)
                if b:
                    ratio=a/b;local_pure=max(local_pure,ratio);pure=max(pure,ratio)
                    case='finite';witnesses.append(dict(from_index=i,to_index=j,output_index=k,ratio=str(ratio)))
                else:
                    ratio=None;case='singular'if a else 'both_zero'
                    if a:singular=True;local_singular=True;mass+=a
                terms.append(dict(output_index=k,p=str(a),q=str(b),ratio=None if ratio is None else str(ratio),
                                  support_case=case,excess=str(excess),positive_part=str(max(excess,F(0)))))
            event_p=sum((p[k]for k in event),F(0));event_q=sum((q[k]for k in event),F(0))
            delta=event_p-t*event_q
            assert delta==sum((F(r['positive_part'])for r in terms),F(0)) and 0<=delta<=1
            pairs.append(dict(from_index=i,to_index=j,from_secret=c['secrets'][i],to_secret=c['secrets'][j],
                              delta=str(delta),event_indices=event,event_outputs=[c['outputs'][k]for k in event],
                              event_p=str(event_p),event_q=str(event_q),tie_indices=ties,
                              singular_mass=str(mass),pure_factor=None if local_singular else str(local_pure),terms=terms))
    maximum=max(F(r['delta'])for r in pairs)
    omitted=[list(e)for e in combinations(range(len(c['secrets'])),2)if list(e)not in c['neighbors']]
    return dict(schema_version=1,arithmetic='exact rational supplied channel probabilities',
                scope='finite channel and listed undirected neighbor edges only; not an audit of a deployed implementation',
                channel=encode(c),factor=str(t),epsilon_relation='epsilon = natural_log(factor); factor is not epsilon',
                delta=str(maximum),pure_factor=None if singular else str(pure),
                pure_factor_status='infinite_due_to_support_mismatch'if singular else 'finite',
                pure_witnesses=[]if singular else [w for w in witnesses if F(w['ratio'])==pure],
                worst_pairs=[i for i,r in enumerate(pairs)if F(r['delta'])==maximum],pairs=pairs,
                all_secret_pairs_listed=not omitted,unlisted_secret_pairs=omitted)
