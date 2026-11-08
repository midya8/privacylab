import copy
from fractions import Fraction as F
from itertools import combinations
import random
import unittest
from privacylab import audit, demo, encode
from privacylab.demo import channel


def total(xs):return sum(xs,F(0))


class PrivacyTests(unittest.TestCase):
    def test_randomized_response_and_factor_is_not_epsilon(self):
        rows=demo()['controls'];rr=rows[0]['audits']
        self.assertEqual([a['delta']for a in rr],['1/2','0','0'])
        self.assertTrue(all(a['pure_factor']=='3'for a in rr))
        self.assertEqual(rr[1]['pairs'][0]['tie_indices'],[0])
        self.assertEqual(rr[1]['pairs'][0]['event_indices'],[])
        self.assertIn('factor is not epsilon',rr[0]['epsilon_relation'])

    def test_sum_all_positive_excesses_not_max_single_output(self):
        r=audit(channel([['2/5','2/5','1/5'],['1/10','1/10','4/5']],['a','b','c']),2)
        p=r['pairs'][0];self.assertEqual(p['delta'],'2/5');self.assertEqual(p['event_indices'],[0,1])
        self.assertEqual(p['event_p'],'4/5');self.assertEqual(p['event_q'],'1/5')
        self.assertEqual(p['terms'][0]['positive_part'],'1/5')

    def test_exhaustive_all_events_seeded_reference(self):
        rng=random.Random(681)
        for _ in range(24):
            weights=[[rng.randint(0,5)for _ in range(4)]for _ in range(3)]
            for row in weights:
                if not sum(row):row[0]=1
            probs=[[F(v,sum(row))for v in row]for row in weights]
            c=dict(schema_version=1,secrets=['a','b','c'],outputs=['w','x','y','z'],neighbors=[[0,1],[1,2],[0,2]],probabilities=probs)
            for t in [F(1),F(3,2),F(3),F(9)]:
                r=audit(c,t);worst=F(0)
                for pair in r['pairs']:
                    p,q=probs[pair['from_index']],probs[pair['to_index']]
                    reference=max(total(p[k]-t*q[k]for k in range(4)if mask>>k&1)for mask in range(16))
                    self.assertEqual(F(pair['delta']),reference);worst=max(worst,reference)
                    event=pair['event_indices'];self.assertEqual(total(p[k]-t*q[k]for k in event),reference)
                self.assertEqual(F(r['delta']),worst)

    def test_every_term_event_and_support_field_reconstructed(self):
        for control in demo()['controls']:
            for r in control['audits']:
                t=F(r['factor']);p=r['channel']['probabilities']
                for pair in r['pairs']:
                    a,b=map(lambda row:list(map(F,row)),[p[pair['from_index']],p[pair['to_index']]])
                    singular=F(0)
                    for k,term in enumerate(pair['terms']):
                        self.assertEqual(F(term['excess']),a[k]-t*b[k])
                        self.assertEqual(F(term['positive_part']),max(a[k]-t*b[k],F(0)))
                        self.assertEqual(term['support_case'],'finite'if b[k]else('singular'if a[k]else'both_zero'))
                        self.assertEqual(term['ratio'],str(a[k]/b[k])if b[k]else None)
                        if a[k]and not b[k]:singular+=a[k]
                    self.assertEqual(F(pair['singular_mass']),singular)
                    self.assertEqual(F(pair['event_p']),total(a[k]for k in pair['event_indices']))
                    self.assertEqual(F(pair['event_q']),total(b[k]for k in pair['event_indices']))
                    self.assertEqual(F(pair['delta']),F(pair['event_p'])-t*F(pair['event_q']))

    def test_pure_factor_is_minimal_via_output_witness(self):
        r=audit(channel([['3/4','1/4'],['1/4','3/4']],['a','b']),3)
        self.assertEqual(len(r['pure_witnesses']),2)
        for w in r['pure_witnesses']:
            rows=r['channel']['probabilities'];p=F(rows[w['from_index']][w['output_index']]);q=F(rows[w['to_index']][w['output_index']])
            self.assertEqual(p,3*q);self.assertGreater(p-F(299,100)*q,0)
        self.assertGreater(F(audit(r['channel'],'299/100')['delta']),0)

    def test_support_mismatch_and_both_zero_are_distinct(self):
        c=channel([[1,0,0],[0,1,0]],['a','b','unused']);r=audit(c,10**12)
        self.assertEqual(r['delta'],'1');self.assertIsNone(r['pure_factor'])
        self.assertEqual(r['pure_factor_status'],'infinite_due_to_support_mismatch')
        self.assertEqual([v['support_case']for v in r['pairs'][0]['terms']],['singular','finite','both_zero'])
        self.assertEqual(r['pairs'][0]['singular_mass'],'1')

    def test_undirected_edges_audited_both_ways_and_omitted_edges_visible(self):
        c=dict(schema_version=1,secrets=['a','b','c'],outputs=['0','1'],neighbors=[[1,0]],probabilities=[[1,0],[1,0],[0,1]])
        r=audit(c,1);self.assertEqual(r['delta'],'0');self.assertEqual(r['pure_factor'],'1')
        self.assertEqual([(p['from_index'],p['to_index'])for p in r['pairs']],[(0,1),(1,0)])
        self.assertEqual(r['unlisted_secret_pairs'],[[0,2],[1,2]]);self.assertFalse(r['all_secret_pairs_listed'])
        c['neighbors'].append([0,2]);self.assertEqual(audit(c,1)['delta'],'1')

    def test_factor_monotonicity_and_convexity(self):
        for control in demo()['controls']:
            c=control['audits'][0]['channel'];d=[F(audit(c,t)['delta'])for t in [1,2,3,5,9]]
            self.assertTrue(all(a>=b for a,b in zip(d,d[1:])))
            self.assertLessEqual(d[1],(d[0]+d[2])/2)
            self.assertLessEqual(d[3],F(2,3)*d[2]+F(1,3)*d[4])

    def test_permutation_invariance(self):
        c=demo()['controls'][1]['audits'][0]['channel'];base=audit(c,3)
        perm=copy.deepcopy(c);perm['outputs']=perm['outputs'][::-1];perm['probabilities']=[r[::-1]for r in c['probabilities']]
        self.assertEqual(audit(perm,3)['delta'],base['delta']);self.assertEqual(audit(perm,3)['pure_factor'],base['pure_factor'])
        perm=copy.deepcopy(c);perm['secrets']=perm['secrets'][::-1];perm['probabilities']=perm['probabilities'][::-1]
        self.assertEqual(audit(perm,3)['delta'],base['delta'])

    def test_exact_decimal_strings_and_fraction_round_trip(self):
        c=channel([['0.1','0.9'],['1/10','9/10']],['a','b'])
        r=audit(c,'1.5');self.assertEqual(r['factor'],'3/2');self.assertEqual(r['delta'],'0')
        self.assertEqual(r['channel']['probabilities'],[['1/10','9/10'],['1/10','9/10']])
        self.assertEqual(encode(r['channel']),r['channel'])

    def test_no_mutation_rng_and_full_capacity(self):
        c=channel([['3/4','1/4'],['1/4','3/4']],['a','b']);old=copy.deepcopy(c);state=random.getstate();audit(c,3)
        self.assertEqual(c,old);self.assertEqual(state,random.getstate())
        c=dict(schema_version=1,secrets=[str(i)for i in range(8)],outputs=[str(i)for i in range(64)],neighbors=[list(e)for e in combinations(range(8),2)],probabilities=[['1/64']*64 for _ in range(8)])
        r=audit(c,1);self.assertEqual(len(r['pairs']),56);self.assertEqual(r['delta'],'0');self.assertEqual(r['pure_factor'],'1');self.assertTrue(r['all_secret_pairs_listed'])

    def test_invalid_probabilities_and_no_silent_normalization(self):
        for v in [True,.5,float('nan'),'-1/2','1/0','01','1e-2',' 1/2','1/2 ',str(2**600),2**600]:
            c=channel([[v,0],[1,0]],['a','b'])
            with self.assertRaises(ValueError):audit(c,1)
        for rows in [[[1,1],[1,0]],[[0,0],[1,0]],[[1],[1,0]],[[1,0]]]:
            with self.assertRaises(ValueError):audit(channel(rows,['a','b']),1)
        c=channel([['1/3','2/3'],['1/2','1/2']],['a','b']);self.assertEqual(encode(c)['probabilities'],c['probabilities'])

    def test_invalid_graph_schema_labels_and_factors(self):
        base=channel([[1,0],[1,0]],['a','b'])
        for edges in [[],[[0,0]],[[0,2]],[[True,1]],[[0,1],[1,0]],None]:
            with self.assertRaises(ValueError):audit(dict(base,neighbors=edges),1)
        for c in [dict(base,schema_version=True),dict(base,extra=1),dict(base,outputs=['a','a']),dict(base,secrets=['a']),dict(base,outputs=['bad\n','b']),dict(base,probabilities=None)]:
            with self.assertRaises(ValueError):audit(c,1)
        for t in [True,1.0,'0','-1','1e3',10**12+1,'nan',None]:
            with self.assertRaises(ValueError):audit(base,t)

    def test_rare_support_leak_retained_without_float_rounding(self):
        tiny=F(1,10**100);c=channel([[1-tiny,tiny],[1,0]],['common','rare'])
        r=audit(c,10**12);self.assertEqual(F(r['delta']),tiny);self.assertIsNone(r['pure_factor'])
        self.assertEqual(r['pairs'][0]['event_indices'],[1]);self.assertEqual(F(r['pairs'][0]['singular_mass']),tiny)
        self.assertEqual(F(r['channel']['probabilities'][0][0]),1-tiny)
