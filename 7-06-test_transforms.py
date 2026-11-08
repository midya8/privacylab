import copy
from fractions import Fraction as F
from math import comb
import random
import unittest
from privacylab import audit,demo,independent_product,postprocess
from privacylab.demo import channel


class TransformTests(unittest.TestCase):
    def test_product_every_probability_and_mapping(self):
        a=channel([['3/4','1/4'],['1/4','3/4']],['a','b']);b=channel([['2/3','1/3'],['1/3','2/3']],['c','d'])
        r=independent_product(a,b);c=r['channel']
        for k,entry in enumerate(r['output_pairs']):
            i,j=entry['first_index'],entry['second_index']
            for x in [0,1]:self.assertEqual(F(c['probabilities'][x][k]),F(a['probabilities'][x][i])*F(b['probabilities'][x][j]))
            self.assertEqual(entry['first_label'],a['outputs'][i]);self.assertEqual(entry['second_label'],b['outputs'][j])
        self.assertEqual(audit(c,6)['pure_factor'],'6');self.assertEqual(audit(c,6)['delta'],'0')

    def test_repeated_rr_closed_form_and_count_postprocessing(self):
        rr=channel([['3/4','1/4'],['1/4','3/4']],['0','1']);c=rr
        for n in [2,3,4]:
            c=independent_product(c,rr)['channel'];self.assertEqual(audit(c,3**n)['pure_factor'],str(3**n))
            kernel=dict(schema_version=1,input_outputs=c['outputs'],outputs=[f'count/{k}'for k in range(n+1)],probabilities=[[int(k==i.bit_count())for k in range(n+1)]for i in range(2**n)])
            reduced=postprocess(c,kernel)
            expected0=[F(comb(n,k))*F(1,4)**k*F(3,4)**(n-k)for k in range(n+1)]
            self.assertEqual(list(map(F,reduced['probabilities'][0])),expected0)
            self.assertEqual(list(map(F,reduced['probabilities'][1])),expected0[::-1])
            for t in [1,3,9]:self.assertEqual(audit(c,t)['delta'],audit(reduced,t)['delta'])

    def test_stochastic_vote_and_deterministic_parity(self):
        controls=demo()['controls'];rr=controls[0]['audits'][0]['channel'];vote=controls[2]['audits'][0]['channel'];parity=controls[3]['audits'][0]['channel']
        self.assertEqual(vote['probabilities'],rr['probabilities']);self.assertEqual(parity['probabilities'],[['5/8','3/8'],['5/8','3/8']])
        self.assertEqual(controls[1]['audits'][1]['delta'],'3/8');self.assertEqual(controls[2]['audits'][1]['delta'],'0')
        self.assertEqual(controls[3]['audits'][0]['pure_factor'],'1')

    def test_data_processing_seeded_channels_and_kernels(self):
        rng=random.Random(815)
        for _ in range(24):
            rows=[[rng.randint(0,5)for _ in range(4)]for _ in range(2)]
            for row in rows:
                if not sum(row):row[0]=1
            c=channel([[F(v,sum(row))for v in row]for row in rows],['a','b','c','d'])
            weights=[[rng.randint(1,5)for _ in range(3)]for _ in range(4)]
            k=dict(schema_version=1,input_outputs=c['outputs'],outputs=['x','y','z'],probabilities=[[F(v,sum(row))for v in row]for row in weights])
            reduced=postprocess(c,k)
            for t in [1,'3/2',3,9]:self.assertLessEqual(F(audit(reduced,t)['delta']),F(audit(c,t)['delta']))

    def test_shared_coin_reconstruction_marginals_and_conditional_failure(self):
        r=demo();controls=r['controls'];joint=controls[-1]['audits'][0]['channel']
        for secret,row in enumerate(joint['probabilities']):
            for out,p in zip(joint['outputs'],row):
                if F(p):self.assertEqual(int(out[0])^int(out[1]),secret)
        self.assertEqual(controls[-3]['audits'][0]['pure_factor'],'3');self.assertEqual(controls[-2]['audits'][0]['pure_factor'],'1')
        self.assertTrue(all(a['delta']=='1'for a in controls[-1]['audits']))
        self.assertIsNone(controls[-1]['audits'][0]['pure_factor'])
        conditional=r['shared_coin']['conditional_on_A_zero'];self.assertEqual(conditional['delta'],'1')
        for secret in [0,1]:
            row=list(map(F,joint['probabilities'][secret]));den=row[0]+row[1]
            self.assertEqual([row[0]/den,row[1]/den],list(map(F,conditional['channel']['probabilities'][secret])))

    def test_identity_constant_and_output_permutation_kernels(self):
        c=channel([['3/4','1/4'],['1/4','3/4']],['a','b'])
        ident=dict(schema_version=1,input_outputs=['a','b'],outputs=['a','b'],probabilities=[[1,0],[0,1]])
        self.assertEqual(postprocess(c,ident),c)
        constant=dict(ident,outputs=['constant'],probabilities=[[1],[1]])
        self.assertEqual(audit(postprocess(c,constant),1)['pure_factor'],'1')
        flip=dict(ident,probabilities=[[0,1],[1,0]])
        self.assertEqual(audit(postprocess(c,flip),1)['delta'],audit(c,1)['delta'])

    def test_no_mutation_rng_and_product_capacity(self):
        c=channel([['1/8']*8,['1/8']*8],[str(i)for i in range(8)]);old=copy.deepcopy(c);state=random.getstate()
        product=independent_product(c,c)['channel'];self.assertEqual(len(product['outputs']),64)
        with self.assertRaises(ValueError):independent_product(product,c)
        self.assertEqual(c,old);self.assertEqual(random.getstate(),state)

    def test_alignment_and_kernel_validation(self):
        c=channel([['3/4','1/4'],['1/4','3/4']],['a','b'])
        for bad in [dict(c,secrets=['secret/1','secret/0']),dict(c,neighbors=[]),dict(c,extra=1)]:
            with self.assertRaises(ValueError):independent_product(c,bad)
        k=dict(schema_version=1,input_outputs=['a','b'],outputs=['x'],probabilities=[[1],[1]])
        for bad in [dict(k,schema_version=True),dict(k,secrets=['x','y']),dict(k,input_outputs=['b','a']),dict(k,probabilities=[[1],[0]]),dict(k,outputs=['x','x'])]:
            with self.assertRaises(ValueError):postprocess(c,bad)

    def test_computed_transform_probability_bit_limit_is_explicit(self):
        tiny=F(1,2**400);c=channel([[tiny,1-tiny],[tiny,1-tiny]],['tiny','common'])
        with self.assertRaisesRegex(ValueError,'512-bit'):independent_product(c,c)
