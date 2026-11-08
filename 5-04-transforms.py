"""Finite transforms with explicit randomness and alignment assumptions."""
from .core import encode, labels, matrix, validate_channel


def independent_product(first, second):
    """Joint release using fresh independent mechanism randomness given secret."""
    a,b=validate_channel(first),validate_channel(second)
    if a['secrets']!=b['secrets'] or a['neighbors']!=b['neighbors']:
        raise ValueError('product requires identical ordered secrets and neighbor edges')
    pairs=[(i,j)for i in range(len(a['outputs']))for j in range(len(b['outputs']))]
    if len(pairs)>64:raise ValueError('product exceeds 64 outputs')
    c=dict(schema_version=1,secrets=a['secrets'],neighbors=a['neighbors'],
           outputs=[f'pair/{i}/{j}'for i,j in pairs],
           probabilities=[[u[i]*v[j]for i,j in pairs]for u,v in zip(a['probabilities'],b['probabilities'])])
    return dict(channel=encode(c),assumption='independent fresh randomness conditional on each secret',
                output_pairs=[dict(output_index=k,first_index=i,second_index=j,
                                   first_label=a['outputs'][i],second_label=b['outputs'][j])for k,(i,j)in enumerate(pairs)])


def postprocess(channel,kernel):
    """One row-stochastic kernel used for all secrets, with fresh randomness."""
    c=validate_channel(channel)
    if not isinstance(kernel,dict) or set(kernel)!={'schema_version','input_outputs','outputs','probabilities'}:
        raise ValueError('kernel needs exactly schema_version, input_outputs, outputs, probabilities')
    if type(kernel['schema_version'])is not int or kernel['schema_version']!=1:
        raise ValueError('kernel schema_version must be integer 1')
    if kernel['input_outputs']!=c['outputs']:raise ValueError('kernel input_outputs must match exact channel output order')
    out=labels(kernel['outputs'],'kernel outputs',1,64)
    k=matrix(kernel['probabilities'],len(c['outputs']),len(out))
    rows=[[sum((p[a]*k[a][b]for a in range(len(k))),0)for b in range(len(out))]for p in c['probabilities']]
    return encode(dict(schema_version=1,secrets=c['secrets'],outputs=out,neighbors=c['neighbors'],probabilities=rows))
