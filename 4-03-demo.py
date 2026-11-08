"""Developed exact controls, not a trained-model privacy certificate."""
from .core import audit
from .transforms import independent_product, postprocess


def channel(rows, outputs):
    return dict(schema_version=1,secrets=['secret/0','secret/1'],outputs=outputs,neighbors=[[0,1]],probabilities=rows)


def demo():
    rr=channel([['3/4','1/4'],['1/4','3/4']],['0','1'])
    product=independent_product(rr,rr)
    independent=product['channel']
    vote_kernel=dict(schema_version=1,input_outputs=independent['outputs'],outputs=['0','1'],
                     probabilities=[[1,0],['1/2','1/2'],['1/2','1/2'],[0,1]])
    vote=postprocess(independent,vote_kernel)
    parity_kernel=dict(schema_version=1,input_outputs=independent['outputs'],outputs=['even','odd'],
                       probabilities=[[1,0],[0,1],[0,1],[1,0]])
    parity=postprocess(independent,parity_kernel)
    # Z=0 with probability3/4. Release A=x XOR Z, B=Z with the SAME Z.
    shared=channel([['3/4',0,0,'1/4'],[0,'1/4','3/4',0]],['00','01','10','11'])
    first_kernel=dict(schema_version=1,input_outputs=shared['outputs'],outputs=['0','1'],
                      probabilities=[[1,0],[1,0],[0,1],[0,1]])
    second_kernel=dict(schema_version=1,input_outputs=shared['outputs'],outputs=['0','1'],
                       probabilities=[[1,0],[0,1],[1,0],[0,1]])
    first=postprocess(shared,first_kernel);second=postprocess(shared,second_kernel)
    conditional=channel([[1,0],[0,1]],['B/0','B/1'])
    mechanisms=[('randomized_response',rr),('two_independent_releases',independent),
                ('vote_with_fresh_tiebreak',vote),('parity_only',parity),
                ('shared_coin_first_marginal',first),('shared_coin_second_marginal',second),('shared_coin_joint',shared)]
    controls=[dict(name=name,audits=[audit(c,t)for t in [1,3,9]])for name,c in mechanisms]
    assert [r['audits'][0]['pure_factor']for r in controls]==['3','9','3','1','3','1',None]
    assert [r['audits'][1]['delta']for r in controls]==['0','3/8','0','0','0','0','1']
    assert first==dict(rr,probabilities=rr['probabilities'])
    assert conditional['probabilities']==[[1,0],[0,1]]
    return dict(schema_version=1,scope='developed finite probability-table controls; no private data or trained-model guarantee',
                controls=controls,product_mapping=product['output_pairs'],
                postprocessing_kernels=dict(vote=vote_kernel,parity=parity_kernel,shared_first=first_kernel,shared_second=second_kernel),
                shared_coin=dict(noise_zero_probability='3/4',formula='A = secret XOR Z; B = Z; recover secret = A XOR B',
                                 conditional_on_A_zero=audit(conditional,3),
                                 warning='marginal guarantees do not justify composing correlated releases; the conditional second release is not private'))
