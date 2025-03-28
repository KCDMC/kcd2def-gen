from record import merge, from_json, into_json
from schema import Root
from pathlib import Path
from argparse import ArgumentParser
from os import chdir

DEFAULT_OUTPUT_FOLDER_PATH = Path("entries")
DEFAULT_OUTPUT_FILE_NAME = 'merged'

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
    parser.add_argument('-o','--output',default=None)
    parser.add_argument('files',nargs='+')
    return parser

def main(argv):
    args = main_parser().parse_args(argv)
    chdir(Path(args.this).parent)
    output_file = args.output
    if output_file is None:
        import time
        timestamp = time.strftime("%Y-%m-%d--%H-%M-%S")
        output_file_name = f"{DEFAULT_OUTPUT_FILE_NAME}_{timestamp}.json"
        output_file = DEFAULT_OUTPUT_FOLDER_PATH / output_file_name
    else:
        output_file = Path(output_file)
    output_file.parent.mkdir(parents=True,exist_ok=True)
    merge_files(args.files,output_file)

if __name__ == '__main__':
    from sys import argv
    from traceback import print_exc
    try:
        main(argv)
        #input()
    except:
        print_exc()
        input()
