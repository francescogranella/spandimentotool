import argparse
from spandimentotool.utils import save_municipalities

parser = argparse.ArgumentParser(description='Optional path argument')
parser.add_argument('-p', '--path', help='path to file', type=str, required=False)

args = parser.parse_args()

if args.path:
    save_municipalities(args.path)
else:
    save_municipalities()

