import copy
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from privacylab import adaptive,adaptive_demo,encode_tree,validate_tree,audit,demo,independent_product
ROOT=Path(__file__).resolve().parents[1]


def sample(rounds=2,secrets=2):
    return dict(schema_version=1,secrets=[f's{i}' for i in range(secrets)],neighbors=[[i,i+1] for i in range(secrets-1)],
                round_outputs=[['0','1'] for _ in range(rounds)],
                steps=[[dict(history=list(h),probabilities=[['3/4','1/4'] if i%2==0 else ['1/4','3/4']
                                                            for i in range(secrets)]) for h in product(range(2),repeat=d)]
                       for d in range(rounds)])


def reference(spec):
    """Recursive path enumeration, separate from production's layer-by-layer propagation."""
    leaves={};prefix={}
    def visit(h,masses):
        prefix[h]=masses
        if len(h)==len(spec['steps']):leaves[h]=masses;return
        node=next(n for n in spec['steps'][len(h)] if tuple(n['history'])==h)
        for k in range(len(spec['round_outputs'][len(h)])):
            visit(h+(k,),[m*F(row[k]) for m,row in zip(masses,node['probabilities'])])
    visit((),[F(1)]*len(spec['secrets']))
    return leaves,prefix


def event_max(p,q,t):
    # Independent all-subset oracle, not the positive-part formula under test.
    return max(sum((p[k]-t*q[k] for k in range(len(p)) if mask>>k&1),F(0))
               for mask in range(1<<len(p)))


class AdaptiveTests(unittest.TestCase):
    def assert_report(self,r,exhaustive=True):
        t=F(r['product_factor']);spec=r['tree'];leaves,prefix=reference(spec)
        paths=list(leaves);joint=r['joint_audit']
        for k,m in enumerate(r['transcript_map']):
            self.assertEqual(tuple(m['history']),paths[k])
            self.assertEqual(m['labels'],[spec['round_outputs'][i][v] for i,v in enumerate(paths[k])])
            for i in range(len(spec['secrets'])):self.assertEqual(F(joint['channel']['probabilities'][i][k]),leaves[paths[k]][i])
        for c in r['conditionals']:
            self.assertEqual([F(v) for v in c['prefix_probabilities']],prefix[tuple(c['history'])])
            self.assertEqual(c['reachable_secrets'],[i for i,v in enumerate(prefix[tuple(c['history'])]) if v])
            for p in c['audit']['pairs']:
                pp=[F(v) for v in c['audit']['channel']['probabilities'][p['from_index']]]
                qq=[F(v) for v in c['audit']['channel']['probabilities'][p['to_index']]]
                self.assertEqual(F(p['delta']),event_max(pp,qq,F(c['audit']['factor'])))
        for pair,actual in zip(r['pairs'],joint['pairs']):
            i,j=pair['from_index'],pair['to_index'];g={():F(1)};loss=F(0);byround=[F(0)]*len(spec['steps'])
            for f in pair['flow']:
                depth=f['round_index'];h=tuple(f['history']);node=next(n for n in spec['steps'][depth] if tuple(n['history'])==h)
                p,q=node['probabilities'][i],node['probabilities'][j];ff=F(r['round_factors'][depth])
                clipped=[min(F(a),ff*F(b)) for a,b in zip(p,q)]
                self.assertEqual([F(v) for v in f['clipped_kernel']],clipped)
                self.assertEqual(F(f['good_mass_in']),g[h]);d=1-sum(clipped)
                self.assertEqual(F(f['conditional_delta']),d)
                removed=g[h]*d;loss+=removed;byround[depth]+=removed
                self.assertEqual(F(f['removed_mass']),removed)
                self.assertEqual(sum(map(F,f['good_mass_children']))+removed,g[h])
                for k,v in enumerate(clipped):
                    g[h+(k,)]=g[h]*v
                    self.assertEqual(F(f['good_mass_children'][k]),g[h+(k,)])
            self.assertEqual(list(map(F,pair['losses_by_round'])),byround)
            self.assertEqual(F(pair['clipped_delta_bound']),loss)
            self.assertEqual(F(pair['retained_mass']),sum(g[h] for h in paths))
            for leaf in pair['leaves']:
                h=tuple(leaf['history']);v=g[h];p,q=leaves[h][i],leaves[h][j]
                self.assertEqual(F(leaf['good_mass']),v);self.assertLessEqual(v,p);self.assertLessEqual(v,t*q)
                self.assertEqual(F(leaf['p_slack']),p-v);self.assertEqual(F(leaf['scaled_q_slack']),t*q-v)
            pp=[leaves[h][i] for h in paths];qq=[leaves[h][j] for h in paths]
            if exhaustive:self.assertEqual(F(actual['delta']),event_max(pp,qq,t))
            self.assertEqual(pair['actual_delta'],actual['delta'])
            self.assertEqual(F(pair['slack']),loss-F(actual['delta']))
            self.assertLessEqual(F(actual['delta']),loss)
            self.assertLessEqual(loss,F(r['uniform_survival_bound']))
        ds=[F(x['worst_conditional_delta']) for x in r['rounds']];survival=F(1)
        for d in ds:survival*=1-d
        self.assertEqual(F(r['uniform_survival_bound']),1-survival)
        self.assertEqual(F(r['unclamped_delta_sum']),sum(ds))
        self.assertEqual(F(r['additive_bound']),min(F(1),sum(ds)))
        self.assertEqual(F(r['clipped_delta_bound']),max(F(p['clipped_delta_bound']) for p in r['pairs']))
        self.assertLessEqual(F(joint['delta']),F(r['clipped_delta_bound']))
        self.assertLessEqual(F(r['uniform_survival_bound']),F(r['additive_bound']))

    def test_six_developed_controls_all_flow_and_events(self):
        controls=adaptive_demo()['controls']
        for c in controls:self.assert_report(c['report'])
        self.assertEqual([c['report']['joint_audit']['delta'] for c in controls],['0','3/8','1/2','1/2','0','1'])
        self.assertEqual([c['report']['clipped_delta_bound'] for c in controls],['0','1/2','3/4','1/2','0','1'])
        self.assertEqual([c['report']['uniform_survival_bound'] for c in controls],['0','1/2','3/4','1','1','1'])

    def test_24_seeded_three_round_trees_against_all_256_events(self):
        rng=random.Random(26319)
        for _ in range(24):
            s=sample(3,3)
            for step in s['steps']:
                for node in step:
                    node['probabilities']=[]
                    for i in range(3):
                        a=rng.randrange(9);node['probabilities'].append([str(F(a,8)),str(F(8-a,8))])
            self.assert_report(adaptive(s,[rng.choice([1,'3/2',3]) for _ in range(3)]))

    def test_actual_transcript_clipping_can_be_strictly_tighter(self):
        # Independent RR at T=1: actual 1/2, directional killed mass 3/4, additive 1.
        r=adaptive_demo()['controls'][2]['report']
        self.assertEqual(r['joint_audit']['delta'],'1/2');self.assertEqual(r['clipped_delta_bound'],'3/4')
        self.assertEqual(r['additive_bound'],'1')
        # Branch weighting beats even the uniform survival bound.
        r=adaptive_demo()['controls'][3]['report']
        self.assertEqual(r['pairs'][0]['losses_by_round'],['0','1/2'])
        self.assertEqual(r['uniform_survival_bound'],'1');self.assertEqual(r['clipped_delta_bound'],'1/2')

    def test_unreachable_histories_are_checked_but_not_weighted(self):
        r=adaptive_demo()['controls'][4]['report'];self.assertEqual(r['joint_audit']['delta'],'0')
        bad=r['conditionals'][2];self.assertEqual(bad['history'],[1]);self.assertEqual(bad['reachable_secrets'],[])
        self.assertEqual(bad['audit']['delta'],'1');self.assertEqual(r['rounds'][1]['worst_conditional_delta'],'1')
        for p in r['pairs']:
            f=p['flow'][2];self.assertEqual(f['conditional_delta'],'1');self.assertEqual(f['good_mass_in'],'0')
            self.assertEqual(f['removed_mass'],'0')
        s=copy.deepcopy(r['tree']);s['steps'][1].pop()
        with self.assertRaises(ValueError):adaptive(s,[1,1])

    def test_shared_coin_matches_old_joint_and_exposes_conditional_failure(self):
        r=adaptive_demo()['controls'][5]['report'];old=demo()['controls'][-1]['audits'][0]['channel']
        self.assertEqual(r['joint_audit']['channel']['probabilities'],old['probabilities'])
        self.assertEqual([c['audit']['delta'] for c in r['conditionals']],['0','1','1'])
        self.assertEqual(r['joint_audit']['pure_factor'],None)
        for row,x in zip(r['joint_audit']['channel']['probabilities'],[0,1]):
            for m,v in zip(r['transcript_map'],row):
                if F(v):self.assertEqual(m['history'][0]^m['history'][1],x)

    def test_history_independent_tree_matches_static_product(self):
        s=sample(2);r=adaptive(s,[3,3]);base=dict(schema_version=1,secrets=s['secrets'],neighbors=s['neighbors'],
                   outputs=['0','1'],probabilities=s['steps'][0][0]['probabilities'])
        p=independent_product(base,base)['channel']
        self.assertEqual(r['joint_audit']['channel']['probabilities'],p['probabilities'])
        self.assertEqual(r['joint_audit']['delta'],audit(p,9)['delta'])
        self.assertEqual(r['joint_audit']['pure_factor'],'9')

    def test_one_round_unary_and_zero_one_endpoints(self):
        s=sample(1);r=adaptive(s,[1]);self.assert_report(r)
        self.assertEqual(r['joint_audit']['delta'],r['clipped_delta_bound'])
        # Insert a deterministic unary prefix, without changing any law.
        old=sample(2);s=copy.deepcopy(old);s['round_outputs'].insert(0,['only'])
        s['steps']=[[dict(history=[],probabilities=[[1],[1]])]]+[
            [dict(history=[0]+n['history'],probabilities=n['probabilities']) for n in step] for step in old['steps']]
        r=adaptive(s,[1,1,1]);base=adaptive(old,[1,1]);self.assert_report(r)
        for field in ['clipped_delta_bound','uniform_survival_bound','additive_bound']:
            self.assertEqual(r[field],base[field])
        self.assertEqual(r['joint_audit']['channel']['probabilities'],base['joint_audit']['channel']['probabilities'])
        s=sample(1);s['steps'][0][0]['probabilities']=[[1,0],[0,1]]
        r=adaptive(s,[10**12]);self.assertEqual(r['joint_audit']['delta'],'1');self.assert_report(r)

    def test_secret_and_output_permutation_and_node_order(self):
        s=sample(3,3);rng=random.Random(552)
        for step in s['steps']:
            for node in step:
                node['probabilities']=[[str(F(k,8)),str(F(8-k,8))] for k in [rng.randrange(9) for _ in range(3)]]
        a=adaptive(s,[1,'3/2',3]);b=copy.deepcopy(s)
        b['secrets'].reverse();b['neighbors']=[[2-j,2-i] for i,j in s['neighbors']]
        for step in b['steps']:
            step.reverse()
            for node in step:
                node['history']=[1-v for v in node['history']]
                node['probabilities']=[list(reversed(row)) for row in reversed(node['probabilities'])]
        r=adaptive(b,[1,'3/2',3]);self.assert_report(r)
        for f in ['clipped_delta_bound','uniform_survival_bound','additive_bound']:self.assertEqual(a[f],r[f])
        self.assertEqual(a['joint_audit']['delta'],r['joint_audit']['delta'])
        for m in a['transcript_map']:
            h=[1-v for v in m['history']];k=next(v['output_index'] for v in r['transcript_map'] if v['history']==h)
            for i in range(3):self.assertEqual(a['joint_audit']['channel']['probabilities'][i][m['output_index']],r['joint_audit']['channel']['probabilities'][2-i][k])

    def test_full_capacity_six_rounds_64_leaves_eight_secrets_28_edges(self):
        s=sample(6,8);s['neighbors']=[list(e) for e in product(range(8),repeat=2) if e[0]<e[1]]
        # Secret-independent kernels make the capacity test fast but exercise every reported directed edge.
        for step in s['steps']:
            for node in step:node['probabilities']=[['1/2','1/2']]*8
        r=adaptive(s,[1]*6);self.assertEqual(len(r['conditionals']),63);self.assertEqual(len(r['transcript_map']),64)
        self.assertEqual(len(r['pairs']),56);self.assertEqual(r['clipped_delta_bound'],'0')
        self.assertEqual(r['joint_audit']['all_secret_pairs_listed'],True)
        for row in r['joint_audit']['channel']['probabilities']:self.assertEqual(row,['1/64']*64)
        for p in r['pairs']:self.assertEqual([v['good_mass'] for v in p['leaves']],['1/64']*64)
        # Generic round alphabet can use eight outcomes, not just binary labels.
        s=dict(schema_version=1,secrets=['s0','s1'],neighbors=[[0,1]],round_outputs=[[str(i) for i in range(8)]],
               steps=[[dict(history=[],probabilities=[['1/8']*8]*2)]])
        self.assertEqual(len(adaptive(s,[1])['transcript_map']),8)

    def test_exact_decimal_tiny_mass_and_computed_rational_limits(self):
        s=sample(1);tiny=F(1,10**100);s['steps'][0][0]['probabilities']=[[tiny,1-tiny],[0,1]]
        r=adaptive(s,[3]);self.assertEqual(F(r['joint_audit']['delta']),tiny);self.assert_report(r)
        s['steps'][0][0]['probabilities']=[['0.1','0.9'],['1/10','9/10']]
        self.assertEqual(adaptive(s,[1])['joint_audit']['delta'],'0')
        s=sample(2)
        for step in s['steps']:
            for node in step:node['probabilities']=[[F(1,2**400),1-F(1,2**400)]]*2
        with self.assertRaisesRegex(ValueError,'512-bit'):adaptive(s,[1,1])
        with self.assertRaises(ValueError):adaptive(sample(2),[10**12,2])

    def test_invalid_schemas_histories_probabilities_and_factors(self):
        base=sample(2);bad=[]
        for key in list(base):
            x=copy.deepcopy(base);x.pop(key);bad.append(x)
        for key,v in [('schema_version',True),('schema_version',2),('secrets',None),('neighbors',[[0,True]]),
                      ('neighbors',[[0,1],[1,0]]),('round_outputs',[]),('round_outputs',[['x','x']]),
                      ('round_outputs',[['x']]*7),('round_outputs',[['0','1']]*7),('steps',[]),('steps',None)]:
            x=copy.deepcopy(base);x[key]=v;bad.append(x)
        for h in [[True],[0.0],[-1],[2],[],[0,1],'0']:
            x=copy.deepcopy(base);x['steps'][1][0]['history']=h;bad.append(x)
        x=copy.deepcopy(base);x['steps'][1][1]['history']=[0];bad.append(x)
        x=copy.deepcopy(base);x['steps'][1][0]['extra']=1;bad.append(x)
        x=copy.deepcopy(base);x['steps'][1].pop();bad.append(x)
        for rows in [[[0.5,0.5]]*2,[[True,False]]*2,[['1/3','1/3']]*2,[['1','0']],[[1,0,0]]*2,[['1e-3','999/1000']]*2]:
            x=copy.deepcopy(base);x['steps'][1][1]['probabilities']=rows;bad.append(x)
        for x in bad:
            with self.subTest(x=x):
                with self.assertRaises(ValueError):adaptive(x,[1,1])
        for factors in [None,[],[1],[1,1,1],[True,1],[1.0,1],[0,1],['-1',1],['1/0',1]]:
            with self.assertRaises(ValueError):adaptive(base,factors)
        # Full node-count limit independent of transcript count: 8*8 followed by unary rounds.
        x=copy.deepcopy(base);x['round_outputs']=[[str(i) for i in range(8)]]*2+[['only']]*4
        with self.assertRaisesRegex(ValueError,'128 conditional'):validate_tree(x)

    def test_nonmutation_rng_canonicalization_and_omitted_edges(self):
        s=sample(2,3);original=copy.deepcopy(s);state=random.getstate();s['steps'][1].reverse()
        r=adaptive(s,[1,3]);self.assertEqual(r['tree'],encode_tree(original));self.assertEqual(random.getstate(),state)
        self.assertEqual(s['steps'][1][0]['history'],[1]);self.assertEqual(r['joint_audit']['unlisted_secret_pairs'],[[0,2]])
        a=encode_tree(s);b=encode_tree(validate_tree(s));self.assertEqual(a,b)

    def test_cli_full_reports_and_original_demo_unchanged(self):
        cmd=[sys.executable,'-m','privacylab']
        p=subprocess.run(cmd+['adaptive-demo'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout,(ROOT/'examples/adaptive-demo.json').read_text())
        self.assertEqual(json.loads(p.stdout),adaptive_demo())
        p=subprocess.run(cmd+['adaptive','examples/adaptive-input.json'],cwd=ROOT,capture_output=True,text=True)
        obj=json.loads((ROOT/'examples/adaptive-input.json').read_text());self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout),adaptive(obj['tree'],obj['factors']))
        p=subprocess.run(cmd+['demo'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.stdout,(ROOT/'examples/demo.json').read_text())

    def test_cli_strict_errors_empty_stdout(self):
        obj=json.loads((ROOT/'examples/adaptive-input.json').read_text());cases=[]
        for key in obj:
            x=copy.deepcopy(obj);x.pop(key);cases.append(json.dumps(x).encode())
        x=copy.deepcopy(obj);x['factors']=[True,1];cases.append(json.dumps(x).encode())
        x=copy.deepcopy(obj);x['schema_version']=True;cases.append(json.dumps(x).encode())
        cases+=[b'{"schema_version":1,"schema_version":1}',b'{"x":NaN}',b'\xff',b' '*100001,b'[]']
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'input.json'
            for data in cases:
                path.write_bytes(data);p=subprocess.run([sys.executable,'-m','privacylab','adaptive',str(path)],cwd=ROOT,capture_output=True)
                self.assertEqual(p.returncode,2,p.stderr);self.assertEqual(p.stdout,b'')
            p=subprocess.run([sys.executable,'-m','privacylab','adaptive',str(path)+'missing'],cwd=ROOT,capture_output=True)
            self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,b'')
