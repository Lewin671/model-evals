"""Trusted native-tool bridge. Never accepts a shell command or arbitrary path."""
import json
from pathlib import Path
import sys

if __package__ in (None,""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

from evalkit.workflows.tools import perform


def main():
    request=json.load(sys.stdin)
    observations,_=perform(Path(request['root']),[request['action']],int(request['seed']),request['variant'],request['change'])
    print(json.dumps(observations[0],ensure_ascii=False))


if __name__=='__main__':main()
