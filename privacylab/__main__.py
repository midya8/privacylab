"""Strict, bounded, offline exact-probability JSON input."""
import argparse
import json
import sys
from . import audit,demo,adaptive,adaptive_demo,minimum_factor,frontier_demo


def load_input(path, command='audit'):
    with open(path,'rb')as stream:data=stream.read(100001)
    if len(data)>100000:raise ValueError('input exceeds 100000 bytes')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('duplicate JSON key: '+k)
            out[k]=v
        return out
    obj=json.loads(data.decode('utf-8'),object_pairs_hook=unique,
                   parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
    fields=({'schema_version','channel','factor'} if command=='audit' else
            {'schema_version','channel','target_delta'} if command=='frontier' else {'schema_version','tree','factors'})
    if not isinstance(obj,dict)or set(obj)!=fields:
        raise ValueError('input fields mismatch: '+', '.join(sorted(fields)))
    if type(obj['schema_version'])is not int or obj['schema_version']!=1:
        raise ValueError('schema_version must be integer 1')
    if command=='frontier':return minimum_factor(obj['channel'],obj['target_delta'])
    return audit(obj['channel'],obj['factor']) if command=='audit' else adaptive(obj['tree'],obj['factors'])


def main():
    p=argparse.ArgumentParser(description='Exact finite-channel privacy factors, deltas and attaining events')
    commands=p.add_subparsers(dest='command',required=True);commands.add_parser('demo');commands.add_parser('adaptive-demo');commands.add_parser('frontier-demo')
    a=commands.add_parser('audit');a.add_argument('input')
    a=commands.add_parser('adaptive');a.add_argument('input')
    a=commands.add_parser('frontier');a.add_argument('input');args=p.parse_args()
    try:result=demo() if args.command=='demo' else adaptive_demo() if args.command=='adaptive-demo' else frontier_demo() if args.command=='frontier-demo' else load_input(args.input,args.command)
    except(ValueError,OSError,UnicodeError)as exc:p.exit(2,'privacylab: '+str(exc)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=='__main__':sys.exit(main())
