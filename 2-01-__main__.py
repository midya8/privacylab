"""Strict, bounded, offline exact-probability JSON input."""
import argparse
import json
import sys
from . import audit,demo


def load_input(path):
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
    if not isinstance(obj,dict)or set(obj)!={'schema_version','channel','factor'}:
        raise ValueError('input needs exactly schema_version, channel, factor')
    if type(obj['schema_version'])is not int or obj['schema_version']!=1:
        raise ValueError('schema_version must be integer 1')
    return audit(obj['channel'],obj['factor'])


def main():
    p=argparse.ArgumentParser(description='Exact finite-channel privacy factors, deltas and attaining events')
    commands=p.add_subparsers(dest='command',required=True);commands.add_parser('demo')
    a=commands.add_parser('audit');a.add_argument('input');args=p.parse_args()
    try:result=demo()if args.command=='demo'else load_input(args.input)
    except(ValueError,OSError,UnicodeError)as exc:p.exit(2,'privacylab: '+str(exc)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=='__main__':sys.exit(main())
