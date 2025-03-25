from record import merge, from_json, into_json
from schema import Root
from pathlib import Path
from argparse import ArgumentParser
from os import chdir

DEFAULT_OUTPUT = '../merged.json'

def merge_files(files,output):
    data = []
    for path in files:
        print(path)
        with open(path) as file:
            data.append(file.read())

    recs = list(map(from_json,data))

    res = recs[0]
    for rec in recs[1:]:
        res = merge(res,rec)

    out = into_json(res)
    
    with open(output,'w') as file:
        file.write(out)

def main_parser():
    parser = ArgumentParser()
    parser.add_argument('this')
    parser.add_argument('-o','--output',default=DEFAULT_OUTPUT)
    parser.add_argument('files',nargs='+')
    return parser

def main(argv):
    args = main_parser().parse_args(argv)
    chdir(Path(args.this).parent)
    merge_files(args.files,args.output)

if __name__ == '__main__':
    from sys import argv
    from traceback import print_exc
    try:
        main(argv)
        #input()
    except:
        print_exc()
        input()
