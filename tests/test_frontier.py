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
from privacylab import audit,frontier,frontier_demo,minimum_factor
ROOT=Path(__file__).resolve().parents[1]


def ch(rows,edges=None):
    return dict(schema_version=1,secrets=[f's{i}' for i in range(len(rows))],outputs=[f'y{i}' for i in range(len(rows[0]))],
                neighbors=edges or [[i,i+1] for i in range(len(rows)-1)],probabilities=rows)


def exhaustive(channel,t):
    values=[]
    for i,j in [v for e in channel['neighbors'] for v in [e,e[::-1]]]:
        p,q=[[F(v) for v in channel['probabilities'][i]] for i in [i,j]]
        values.append(max(sum((p[k]-t*q[k] for k in range(len(p)) if mask>>k&1),F(0)) for mask in range(1<<len(p))))
    return max(values)


def global_value(profile,t):
    s=next(s for s in profile['segments'] if F(s['lower'])<=t and (s['upper'] is None or t<=F(s['upper'])))
    return F(s['intercept'])-F(s['slope_magnitude'])*t


class FrontierTests(unittest.TestCase):
    def check(self,p):
        c=p['channel'];segments=p['segments'];self.assertEqual(segments[0]['lower'],'1');self.assertIsNone(segments[-1]['upper'])
        for i,s in enumerate(segments):
            l=F(s['lower']);u=None if s['upper'] is None else F(s['upper']);a,b=F(s['intercept']),F(s['slope_magnitude'])
            self.assertGreaterEqual(b,0);self.assertEqual(global_value(p,l),exhaustive(c,l))
            for t in [l+F(1,2),l+1,l+10] if u is None else [l,(3*l+u)/4,(l+u)/2,(l+3*u)/4,u]:
                self.assertEqual(a-b*t,exhaustive(c,t))
                if t<=10**12:self.assertEqual(a-b*t,F(audit(c,t)['delta']))
            for entry in s['dominance']:
                pc=p['pair_curves'][entry['pair_index']]
                cursor=l
                for ov in entry['overlaps']:
                    ll=F(ov['lower']);uu=None if ov['upper'] is None else F(ov['upper']);self.assertEqual(ll,cursor)
                    local=next(v for v in pc['segments'] if F(v['lower'])<=ll and (v['upper'] is None or (uu is not None and uu<=F(v['upper']))))
                    aa,bb=F(local['intercept']),F(local['slope_magnitude'])
                    self.assertEqual(F(ov['start_slack']),a-aa+(bb-b)*ll);self.assertGreaterEqual(F(ov['start_slack']),0)
                    if uu is None:self.assertEqual(F(ov['tail_slope_slack']),bb-b);self.assertGreaterEqual(bb-b,0)
                    else:self.assertEqual(F(ov['end_slack']),a-aa+(bb-b)*uu);self.assertGreaterEqual(F(ov['end_slack']),0)
                    cursor=uu
                self.assertEqual(cursor,u)
            if i:
                prev=segments[i-1];self.assertEqual(prev['upper'],s['lower'])
                self.assertEqual(F(prev['intercept'])-F(prev['slope_magnitude'])*l,a-b*l)
                self.assertGreaterEqual(F(prev['slope_magnitude']),b)
        self.assertEqual(F(segments[-1]['intercept']),F(p['plateau']));self.assertEqual(F(segments[-1]['slope_magnitude']),0)
        for knot in p['knots']:
            t=F(knot['factor']);point=knot['point'];self.assertEqual(F(point['delta']),exhaustive(c,t))
            for pair in point['pairs']:
                pp=[F(v) for v in c['probabilities'][pair['from_index']]];qq=[F(v) for v in c['probabilities'][pair['to_index']]]
                event=[i for i,(a,b) in enumerate(zip(pp,qq)) if a>t*b]
                self.assertEqual(pair['event_indices'],event)
                self.assertEqual(F(pair['event_p']),sum((pp[k] for k in event),F(0)))
                self.assertEqual(F(pair['event_q']),sum((qq[k] for k in event),F(0)))

    def check_inverse(self,c,d):
        result=minimum_factor(c,d);p=result['frontier'];r=result['inverse'];d=F(d)
        if r['status']=='unattainable':
            self.assertLess(d,F(p['plateau']));o=r['obstruction'];self.assertEqual(o['q_mass'],'0');self.assertGreater(F(o['p_mass']),d)
            return
        t=F(r['factor']);self.assertGreaterEqual(t,1);self.assertLessEqual(exhaustive(c,t),d)
        self.assertEqual(F(r['point']['delta']),exhaustive(c,t))
        if t>1:
            cert=r['minimality'];a,b=F(cert['intercept']),F(cert['slope_magnitude']);self.assertGreater(b,0)
            self.assertEqual((a-d)/b,t)
            # Arbitrarily close predecessor on the certified positive-slope interval.
            left=F(cert['interval_lower']);near=(left+999*t)/1000
            self.assertGreater(exhaustive(c,near),d)
        else:self.assertEqual(r['minimality']['kind'],'domain_lower_bound')

    def test_developed_profiles_whole_interval_proofs_and_knots(self):
        for row in frontier_demo()['controls']:self.check(row['profile'])

    def test_nonratio_neighbor_envelope_switch_exact_closed_form(self):
        p=frontier_demo()['controls'][2]['profile'];self.assertNotIn('5/4',p['ratio_grid'])
        self.assertEqual([(s['lower'],s['upper'],s['intercept'],s['slope_magnitude']) for s in p['segments']],
                         [('1','5/4','5/8','5/16'),('5/4','5','5/16','1/16'),('5',None,'0','0')])
        point=p['knots'][1]['point'];self.assertEqual(point['worst_pairs'],[0,1]);self.assertEqual(point['delta'],'15/64')
        self.assertEqual(p['segments'][0]['interior_worst_pairs'],[0]);self.assertEqual(p['segments'][1]['interior_worst_pairs'],[1])

    def test_randomized_response_inverse_and_boundary_targets(self):
        c=frontier_demo()['controls'][0]['profile']['channel']
        for d,t in [(0,'3'),('1/4','2'),('1/2','1'),(1,'1')]:
            self.assertEqual(minimum_factor(c,d)['inverse']['factor'],t);self.check_inverse(c,d)
        self.assertEqual(minimum_factor(c,0)['frontier']['pure_factor'],'3')

    def test_32_seeded_four_output_frontiers_and_exhaustive_events(self):
        rng=random.Random(19483)
        for _ in range(32):
            rows=[]
            for i in range(3):
                cuts=sorted([rng.randrange(17) for _ in range(3)]);xs=[0]+cuts+[16]
                rows.append([str(F(b-a,16)) for a,b in zip(xs,xs[1:])])
            c=ch(rows,[[0,1],[0,2],[1,2]]);p=frontier(c);self.check(p)
            for d in [0,'1/8','1/2',1]:self.check_inverse(c,d)

    def test_singular_plateau_obstruction_and_equality_attainment(self):
        c=frontier_demo()['controls'][1]['profile']['channel'];self.assertEqual(frontier(c)['plateau'],'1/2')
        self.check_inverse(c,'1/4');self.check_inverse(c,'1/2')
        r=minimum_factor(c,'1/4')['inverse'];self.assertEqual(r['obstruction']['event_indices'],[0])
        self.assertIsNone(r['factor']);self.assertEqual(minimum_factor(c,'1/2')['inverse']['factor'],'1')
        # Positive plateau reached only after a finite decreasing segment.
        c=ch([['1/4','1/2','1/4',0],[0,'1/4','1/2','1/4']]);p=frontier(c);self.assertEqual(p['plateau'],'1/4')
        self.assertEqual(minimum_factor(c,'1/4')['inverse']['factor'],'2');self.check_inverse(c,'1/4')

    def test_exact_large_factor_keeps_original_point_domain_unchanged(self):
        c=frontier_demo()['controls'][3]['profile']['channel'];r=minimum_factor(c,0)['inverse']
        self.assertEqual(F(r['factor']),F(10**30,2));self.assertFalse(r['within_point_audit_domain']);self.check_inverse(c,0)
        with self.assertRaises(ValueError):audit(c,F(r['factor']))
        # Tiny API probabilities serialize to long fractions internally, not reparsed under the string cap.
        e=F(1,10**100);c=ch([[F(1,2),F(1,2)],[e,1-e]])
        self.assertEqual(F(minimum_factor(c,0)['inverse']['factor']),F(10**100,2))

    def test_all_equal_one_output_zeros_and_pure_witnesses(self):
        for c in [ch([[1],[1]]),ch([[0,1,0],[0,1,0]]),ch([['1/3','2/3'],['1/3','2/3']])]:
            p=frontier(c);self.assertEqual(len(p['segments']),1);self.assertEqual(p['plateau'],'0');self.assertEqual(p['pure_factor'],'1');self.check(p)
            self.assertEqual(minimum_factor(c,0)['inverse']['factor'],'1')
        c=ch([[1,0],[0,1]]);p=frontier(c);self.assertEqual(p['plateau'],'1');self.assertIsNone(p['pure_factor']);self.check(p)
        self.check_inverse(c,'9/10');self.check_inverse(c,1)

    def test_directed_pairs_and_omitted_neighbors(self):
        c=ch([['1/2','1/2'],['1/2','1/2'],[1,0]],[[0,1]])
        p=frontier(c);self.assertEqual(len(p['pair_curves']),2);self.assertEqual(p['unlisted_secret_pairs'],[[0,2],[1,2]])
        self.assertEqual(p['pure_factor'],'1')
        c['neighbors']+=[[1,2]];self.assertEqual(frontier(c)['plateau'],'1/2')
        c=ch([['1/2','1/2'],['1/4','3/4']]);p=frontier(c)
        self.assertEqual(p['knots'][0]['point']['worst_pairs'],[0,1]);self.assertEqual(p['segments'][0]['interior_worst_pairs'],[0])

    def test_secret_output_row_order_and_label_permutations(self):
        c=frontier_demo()['controls'][2]['profile']['channel'];p=frontier(c);r=copy.deepcopy(c)
        r['secrets'].reverse();r['probabilities']=[list(reversed(row)) for row in reversed(r['probabilities'])]
        r['outputs'].reverse();r['neighbors']=[[2-j,2-i] for i,j in reversed(r['neighbors'])]
        q=frontier(r)
        for t in [1,F(5,4),2,5,9]:self.assertEqual(global_value(p,t),global_value(q,t))
        for d in [0,'15/64','1/4',1]:self.assertEqual(minimum_factor(c,d)['inverse']['factor'],minimum_factor(r,d)['inverse']['factor'])

    def test_full_four_secret_eight_output_six_edge_capacity(self):
        c=ch([['1/8']*8 for _ in range(4)],[[i,j] for i in range(4) for j in range(i+1,4)])
        p=frontier(c);self.assertEqual(len(p['pair_curves']),12);self.assertEqual(len(p['segments']),1)
        self.assertEqual(len(p['segments'][0]['dominance']),12);self.assertEqual(p['unlisted_secret_pairs'],[]);self.check(p)
        c=ch([[1]+[0]*7,[0]*7+[1],[0,1]+[0]*6,[0]*6+[1,0]],c['neighbors']);self.check(frontier(c))
        rng=random.Random(887);rows=[]
        for i in range(4):
            cuts=[0]+sorted(rng.sample(range(1,64),7))+[64]
            rows.append([str(F(b-a,64)) for a,b in zip(cuts,cuts[1:])])
        self.check(frontier(ch(rows,c['neighbors'])))

    def test_nonmutation_rng_and_exact_decimal_strings(self):
        c=ch([['0.1','0.9'],['1/10','9/10']]);before=copy.deepcopy(c);state=random.getstate();p=frontier(c)
        self.assertEqual(p['pure_factor'],'1');self.assertEqual(c,before);self.assertEqual(random.getstate(),state)
        self.assertEqual(minimum_factor(c,0)['inverse']['factor'],'1')

    def test_invalid_channel_target_and_scope_limits(self):
        c=ch([['3/4','1/4'],['1/4','3/4']])
        for target in [True,0.5,'-1','1e-2','1/0',2,None]:
            with self.assertRaises(ValueError):minimum_factor(c,target)
        for bad in [ch([[1]+[0]*8]*2),ch([[1]]*5),dict(c,extra=1),dict(c,schema_version=True),dict(c,neighbors=[[True,1]]),
                    dict(c,probabilities=[[.75,.25],[.25,.75]]),dict(c,probabilities=[['1/3','1/3']]*2)]:
            with self.assertRaises(ValueError):frontier(bad)

    def test_cli_all_six_full_outputs_and_committed_report(self):
        p=subprocess.run([sys.executable,'-m','privacylab','frontier-demo'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout,(ROOT/'examples/frontier-demo.json').read_text())
        self.assertEqual(json.loads(p.stdout),frontier_demo())
        o=json.loads((ROOT/'examples/frontier-input.json').read_text())
        p=subprocess.run([sys.executable,'-m','privacylab','frontier','examples/frontier-input.json'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout),minimum_factor(o['channel'],o['target_delta']))
        for command,artifact in [('demo','demo.json'),('adaptive-demo','adaptive-demo.json')]:
            p=subprocess.run([sys.executable,'-m','privacylab',command],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.stdout,(ROOT/'examples'/artifact).read_text())

    def test_cli_invalid_input_strict_empty_stdout(self):
        obj=json.loads((ROOT/'examples/frontier-input.json').read_text());cases=[]
        for key in obj:
            bad=copy.deepcopy(obj);bad.pop(key);cases.append(json.dumps(bad).encode())
        for field,value in [('target_delta',True),('target_delta',0.25),('schema_version',True),('extra',1)]:
            bad=copy.deepcopy(obj);bad[field]=value;cases.append(json.dumps(bad).encode())
        cases+=[b'{"schema_version":1,"schema_version":1}',b'NaN',b'\xff',b' '*100001,b'[]']
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'input.json'
            for data in cases:
                path.write_bytes(data);p=subprocess.run([sys.executable,'-m','privacylab','frontier',str(path)],cwd=ROOT,capture_output=True)
                self.assertEqual(p.returncode,2,p.stderr);self.assertEqual(p.stdout,b'')
            p=subprocess.run([sys.executable,'-m','privacylab','frontier',str(path)+'missing'],cwd=ROOT,capture_output=True)
            self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,b'')
