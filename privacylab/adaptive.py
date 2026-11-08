"""Exact finite adaptive transcripts and one-sided killed-mass certificates.

Kernels are the caller's full conditional laws, not unconditional marginals.
"""
from fractions import Fraction as F
from itertools import product
from .core import audit, encode, labels, matrix, rational, validate_channel


def histories(alphabets, depth):
    return list(product(*(range(len(a)) for a in alphabets[:depth])))


def validate_tree(tree):
    keys={'schema_version','secrets','neighbors','round_outputs','steps'}
    if not isinstance(tree,dict) or set(tree)!=keys:
        raise ValueError('tree needs exactly schema_version, secrets, neighbors, round_outputs, steps')
    if type(tree['schema_version']) is not int or tree['schema_version']!=1:
        raise ValueError('tree schema_version must be integer 1')
    # Reuse the static channel's secret/adjacency validation, not its audit result.
    base=validate_channel(dict(schema_version=1,secrets=tree['secrets'],neighbors=tree['neighbors'],
                               outputs=['placeholder'],probabilities=[[1] for _ in tree['secrets']])) if isinstance(tree['secrets'],(list,tuple)) else None
    if base is None:raise ValueError('tree secrets must be a label sequence')
    alphabets=tree['round_outputs']
    if not isinstance(alphabets,(list,tuple)) or not 1<=len(alphabets)<=6:
        raise ValueError('round_outputs needs 1..6 rounds')
    alphabets=[labels(a,'round outputs',1,8) for a in alphabets]
    count=1;nodes=0
    for a in alphabets:
        nodes+=count;count*=len(a)
        if count>64 or nodes>128:raise ValueError('tree exceeds 64 transcripts or 128 conditional nodes')
    steps=tree['steps']
    if not isinstance(steps,(list,tuple)) or len(steps)!=len(alphabets):
        raise ValueError('one complete step is required per round')
    canonical=[]
    for depth,(alphabet,step) in enumerate(zip(alphabets,steps)):
        expected=histories(alphabets,depth)
        if not isinstance(step,(list,tuple)) or len(step)!=len(expected):
            raise ValueError('each step needs every syntactically possible history exactly once')
        found={}
        for node in step:
            if not isinstance(node,dict) or set(node)!={'history','probabilities'}:
                raise ValueError('conditional node needs exactly history and probabilities')
            h=node['history']
            if (not isinstance(h,(list,tuple)) or len(h)!=depth or
                any(type(v)is not int or not 0<=v<len(alphabets[i]) for i,v in enumerate(h))):
                raise ValueError('history needs valid integer output indices in prior-round order')
            h=tuple(h)
            if h in found:raise ValueError('duplicate history')
            found[h]=matrix(node['probabilities'],len(base['secrets']),len(alphabet))
        canonical.append([dict(history=list(h),probabilities=found[h]) for h in expected])
    return dict(schema_version=1,secrets=base['secrets'],neighbors=base['neighbors'],
                round_outputs=alphabets,steps=canonical)


def encode_tree(tree):
    t=validate_tree(tree)
    return dict(t,steps=[[dict(history=n['history'],probabilities=[[str(v) for v in row] for row in n['probabilities']])
                          for n in step] for step in t['steps']])


def _channel(tree, depth, rows):
    return dict(schema_version=1,secrets=tree['secrets'],neighbors=tree['neighbors'],
                outputs=tree['round_outputs'][depth],probabilities=rows)


def adaptive(tree, factors):
    """Audit supplied conditional kernels at fixed, history-independent round factors.

    Return exact transcript law, every conditional audit and directional clipping
    flows. The clipped subdistribution is below both P and product(factors)*Q.
    This is not a privacy filter, odometer or optimal-composition implementation.
    """
    t=validate_tree(tree);rounds=len(t['round_outputs']);n=len(t['secrets'])
    if not isinstance(factors,(list,tuple)) or len(factors)!=rounds:
        raise ValueError('one fixed factor is required per round')
    fs=[rational(v,'round factor',factor=True) for v in factors]
    total=F(1)
    for f in fs:total=rational(total*f,'product factor',factor=True)
    prefix={():[F(1)]*n};conditionals=[];rounds_summary=[];tables=[]
    for depth,step in enumerate(t['steps']):
        table={tuple(v['history']):v['probabilities'] for v in step};tables.append(table)
        next_prefix={};records=[]
        for h in histories(t['round_outputs'],depth):
            rows=table[h];rep=audit(_channel(t,depth,rows),fs[depth])
            rec=dict(round_index=depth,history=list(h),history_labels=[t['round_outputs'][i][v] for i,v in enumerate(h)],
                     prefix_probabilities=[str(v) for v in prefix[h]],
                     reachable_secrets=[i for i,v in enumerate(prefix[h]) if v],audit=rep)
            records.append(rec);conditionals.append(rec)
            for k in range(len(t['round_outputs'][depth])):
                next_prefix[h+(k,)]=[rational(prefix[h][i]*rows[i][k],'transcript probability') for i in range(n)]
        d=max(F(v['audit']['delta']) for v in records)
        rounds_summary.append(dict(round_index=depth,factor=str(fs[depth]),worst_conditional_delta=str(d),
                                   worst_histories=[v['history'] for v in records if F(v['audit']['delta'])==d]))
        prefix=next_prefix
    leaf_paths=histories(t['round_outputs'],rounds)
    joint=dict(schema_version=1,secrets=t['secrets'],neighbors=t['neighbors'],
                      outputs=[f'transcript/{k}' for k in range(len(leaf_paths))],
                      probabilities=[[prefix[h][i] for h in leaf_paths] for i in range(n)])
    joint_report=audit(joint,total);pair_reports=[]
    survival=F(1);sum_delta=F(0)
    for r in rounds_summary:
        d=F(r['worst_conditional_delta']);survival*=1-d;sum_delta+=d
    uniform=1-survival;additive=min(F(1),sum_delta)
    for pair in joint_report['pairs']:
        i,j=pair['from_index'],pair['to_index'];good={():F(1)};flow=[];losses=[]
        for depth,table in enumerate(tables):
            new_good={};loss=F(0)
            for h in histories(t['round_outputs'],depth):
                p,q=table[h][i],table[h][j];clipped=[min(a,fs[depth]*b) for a,b in zip(p,q)]
                local=1-sum(clipped,F(0));removed=rational(good[h]*local,'removed mass')
                children=[rational(good[h]*v,'clipped prefix mass') for v in clipped]
                flow.append(dict(round_index=depth,history=list(h),good_mass_in=str(good[h]),
                                 conditional_delta=str(local),clipped_kernel=[str(v) for v in clipped],
                                 removed_mass=str(removed),good_mass_children=[str(v) for v in children]))
                loss+=removed
                for k,v in enumerate(children):new_good[h+(k,)]=v
            losses.append(loss);good=new_good
        retained=sum(good.values(),F(0));deficit=1-retained;actual=F(pair['delta'])
        assert sum(losses,F(0))==deficit and actual<=deficit<=uniform<=additive<=1
        leaves=[]
        for k,h in enumerate(leaf_paths):
            p,q=prefix[h][i],prefix[h][j];v=good[h]
            assert 0<=v<=p and v<=total*q
            leaves.append(dict(output_index=k,history=list(h),p=str(p),q=str(q),good_mass=str(v),
                               p_slack=str(p-v),scaled_q_slack=str(total*q-v)))
        pair_reports.append(dict(from_index=i,to_index=j,actual_delta=str(actual),clipped_delta_bound=str(deficit),
                                 retained_mass=str(retained),slack=str(deficit-actual),
                                 losses_by_round=[str(v) for v in losses],flow=flow,leaves=leaves))
    worst_clip=max(F(v['clipped_delta_bound']) for v in pair_reports)
    return dict(schema_version=1,tree=encode_tree(t),round_factors=[str(v) for v in fs],product_factor=str(total),
                scope='exact supplied finite conditional laws and listed edges only; no external randomness verification',
                conditional_semantics='each table is a full law given secret and entire prior transcript, including null histories',
                factor_semantics='fixed factors per round, independent of transcript; epsilon is natural_log(factor)',
                transcript_map=[dict(output_index=k,history=list(h),labels=[t['round_outputs'][i][v] for i,v in enumerate(h)])
                                for k,h in enumerate(leaf_paths)],
                conditionals=conditionals,rounds=rounds_summary,joint_audit=joint_report,pairs=pair_reports,
                clipped_delta_bound=str(worst_clip),uniform_survival_bound=str(uniform),
                additive_bound=str(additive),unclamped_delta_sum=str(sum_delta),
                worst_clipped_pairs=[k for k,v in enumerate(pair_reports) if F(v['clipped_delta_bound'])==worst_clip],
                ordering='actual joint delta <= maximum directed clipping deficit <= uniform survival bound <= clamped additive bound')


def adaptive_demo():
    rr=[['3/4','1/4'],['1/4','3/4']];constant=[[1,0],[1,0]];reveal=[[1,0],[0,1]]
    def tree(first,zero,one):
        return dict(schema_version=1,secrets=['bit0','bit1'],neighbors=[[0,1]],round_outputs=[['0','1'],['0','1']],
                    steps=[[dict(history=[],probabilities=first)],
                           [dict(history=[0],probabilities=zero),dict(history=[1],probabilities=one)]])
    cases=[('independent pure RR',tree(rr,rr,rr),[3,3]),
           ('adaptive RR or constant',tree(rr,rr,constant),[1,3]),
           ('independent at factor one',tree(rr,rr,rr),[1,1]),
           ('branch-weighted reveal',tree([['1/2','1/2']]*2,reveal,constant),[1,1]),
           ('unreachable reveal',tree(constant,constant,reveal),[1,1]),
           ('shared coin conditional failure',tree(rr,reveal,[[0,1],[1,0]]),[3,1])]
    controls=[dict(name=name,report=adaptive(spec,factors)) for name,spec,factors in cases]
    expected=[('9','0','0','0','0'),('3','3/8','1/2','1/2','1/2'),('1','1/2','3/4','3/4','1'),
              ('1','1/2','1/2','1','1'),('1','0','0','1','1'),('3','1','1','1','1')]
    for c,e in zip(controls,expected):
        r=c['report'];assert (r['product_factor'],r['joint_audit']['delta'],r['clipped_delta_bound'],
                             r['uniform_survival_bound'],r['additive_bound'])==e
    return dict(schema_version=1,description='Developed finite adaptive controls; exact probabilities, not sampled privacy',
                controls=controls)
