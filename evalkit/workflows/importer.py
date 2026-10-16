"""Synthetic multi-file importer task, independent oracle and tiered scenarios."""
import copy
import csv
import io
import json
from pathlib import Path
import random

FIELDS=["id","revision","category","amount_cents","note","op"]

CONTRACT='''# Stream Ledger

Repair/complete the implementation while preserving its public API. Use only Python's
standard library. You can change ledger/parser.py, ledger/store.py and ledger/api.py.

## API and behavior

- Ingestor(database_path) opens or creates a persistent database. One active writer only.
- feed(stream_id, delivery_id, text, final=False) appends a Unicode CSV fragment and
  returns the number of accepted record revisions, including tombstones. Each pair of
  stream_id/delivery_id identifies one delivery; exact retries return 0 and change nothing.
- Fragments may split anywhere, including quotes, headers and CRLF. Multiple streams
  may be interleaved. Each stream has its own header, pending fragment and delivery IDs.
- CSV has these named columns in any order: id, revision, category, amount_cents, note, op.
  Quoted newlines, escaped quotes, commas and Unicode are valid. Empty physical lines
  are ignored; an empty import or header-only import is valid.
- Commit complete logical records ending in LF or CRLF. final=True also commits a final
  complete record without a newline. An incomplete quoted record at final=True is invalid.
- revision is a positive integer; id is nonempty; op is upsert or delete. Upserts require
  integer amount_cents and preserve category/note. Negative amounts are valid credits.
  Delete rows may leave category/amount/note empty.
- Highest revision wins globally by record ID, independent of arrival order or stream.
  Equal/older revisions are ignored. Deleted IDs retain their revision so older upserts
  cannot resurrect them. A later, higher revision may restore an ID.
- A feed is atomic: invalid complete rows raise ValueError without changing records,
  pending text, delivery bookkeeping or headers, including the in-memory instance.
  A corrected retry of a failed delivery ID must still work.
- Restarting Ingestor must preserve committed records, tombstones, pending text and replay
  bookkeeping. No feed after a stream's final delivery is required, except replay retries.
- records() returns live records sorted lexicographically by ID, with exactly the fields
  id, revision (int), category, amount_cents (int), note. Deleted records are excluded.
- summary() returns {"total_cents": int, "by_category": {category: int}} from live records.
  Keep zero-valued categories if live records remain; remove categories with no live records.
  Repeated summary calls must reflect successful feeds and ignore failed/ignored ones.
- import_csv(database_path, text) remains supported: import a complete CSV document and
  return its summary. Multiple independent files (each with a header) may use one database;
  importing an identical document again is harmless.

## Available file tools

Respond with {"actions": [...]}. Actions execute in order, then their results are returned.
You may batch actions. Supported actions:
  {"tool":"read", "paths":["ledger/api.py", ...]}
  {"tool":"write", "files":{"ledger/api.py":"complete source text", ...}}
  {"tool":"test"}
  {"tool":"finish"}
You may read README.md, ledger/__init__.py and the three source files; only those three
source files can be written. test executes fixed public checks in a fresh sandbox. Hidden
checks are run after the episode; their source is not available to the file tools.
No real shell/browser/network is needed. Implement runnable files, not an explanation.
Equivalent implementations and normal JSON Markdown fences/singleton wrappers are accepted.
'''

CHANGE='''Change request from the downstream consumer (part of the final acceptance contract):
An already accepted (stream_id, delivery_id) is an exact retry ONLY if BOTH text and final
match the original delivery. A conflicting retry must raise ValueError without mutating
any state. This comparison must survive restarting Ingestor. A failed/unaccepted delivery
is still free to be corrected and retried under its ID. Implement this in addition to
the original requirements. No migration of pre-existing databases from older code is tested.
'''

PARSER_REFERENCE='''import csv
import io

def decode(pending, header, text, final=False):
    data = pending + text
    quoted = False
    boundaries = []
    i = 0
    while i < len(data):
        if data[i] == '"':
            if quoted and i + 1 < len(data) and data[i + 1] == '"':
                i += 2
                continue
            quoted = not quoted
        elif data[i] == '\\n' and not quoted:
            boundaries.append(i + 1)
        i += 1
    if final:
        if quoted:
            raise ValueError('incomplete quoted record')
        if not boundaries or boundaries[-1] != len(data):
            boundaries.append(len(data))
    consumed = boundaries[-1] if boundaries else 0
    complete = data[:consumed]
    rows = []
    try:
        parsed = csv.reader(io.StringIO(complete, newline=''), strict=True)
        for values in parsed:
            if not values:
                continue
            if header is None:
                if len(values) != 6 or set(values) != {'id','revision','category','amount_cents','note','op'}:
                    raise ValueError('invalid header')
                header = values
            else:
                if len(values) != len(header):
                    raise ValueError('invalid field count')
                rows.append(dict(zip(header, values)))
    except csv.Error as exc:
        raise ValueError(str(exc)) from exc
    return data[consumed:], header, rows
'''

STORE_REFERENCE='''import json
import os
import tempfile
from pathlib import Path

class Store:
    def __init__(self, path):
        self.path = Path(path)
    def load(self):
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {'streams': {}, 'records': {}}
    def save(self, data):
        with tempfile.NamedTemporaryFile('w', dir=self.path.parent, delete=False) as f:
            json.dump(data, f)
            name = f.name
        os.replace(name, self.path)
    def apply(self, data, row):
        key = row['id']
        revision = int(row['revision'])
        if not key or revision <= 0 or row['op'] not in ('upsert', 'delete'):
            raise ValueError('invalid record')
        amount = int(row['amount_cents']) if row['op'] == 'upsert' else 0
        previous = data['records'].get(key)
        if previous and revision <= previous['revision']:
            return False
        data['records'][key] = {'id': key, 'revision': revision, 'category': row['category'],
            'amount_cents': amount, 'note': row['note'], 'deleted': row['op'] == 'delete'}
        return True
'''

API_REFERENCE='''import copy
import hashlib
import json
from .parser import decode
from .store import Store

class Ingestor:
    def __init__(self, database_path):
        self.store = Store(database_path)
        self.data = self.store.load()
    def feed(self, stream_id, delivery_id, text, final=False):
        next_state = copy.deepcopy(self.data)
        stream = next_state['streams'].setdefault(stream_id, {'pending': '', 'header': None, 'deliveries': {}})
        fingerprint = hashlib.sha256(json.dumps([text, final]).encode()).hexdigest()
        if delivery_id in stream['deliveries']:
            if stream['deliveries'][delivery_id] != fingerprint:
                raise ValueError('conflicting delivery')
            return 0
        pending, header, rows = decode(stream['pending'], stream['header'], text, final)
        accepted = 0
        for row in rows:
            accepted += self.store.apply(next_state, row)
        stream['pending'] = pending
        stream['header'] = header
        stream['deliveries'][delivery_id] = fingerprint
        self.store.save(next_state)
        self.data = next_state
        return accepted
    def records(self):
        return [{k: row[k] for k in ('id','revision','category','amount_cents','note')}
                for key, row in sorted(self.data['records'].items()) if not row['deleted']]
    def summary(self):
        groups = {}
        for row in self.records():
            key = row['category']
            groups[key] = groups.get(key, 0) + row['amount_cents']
        return {'total_cents': sum(groups.values()), 'by_category': groups}

def import_csv(database_path, text):
    ingestor = Ingestor(database_path)
    stream = 'legacy-' + hashlib.sha256(text.encode()).hexdigest()
    ingestor.feed(stream, 'complete', text, final=True)
    return ingestor.summary()
'''

PARSER_NAIVE='''import csv
import io

def decode(pending, header, text, final=False):
    data = pending + text
    cut = len(data) if final else data.rfind('\\n') + 1
    lines = data[:cut].splitlines()
    rows = []
    for line in lines:
        values = next(csv.reader([line]))
        if not values:
            continue
        if header is None:
            header = values
        elif len(values) != len(header):
            raise ValueError('invalid field count')
        else:
            rows.append(dict(zip(header, values)))
    return data[cut:], header, rows
'''

API_STARTER='''import hashlib
from .parser import decode
from .store import Store

class Ingestor:
    def __init__(self, database_path):
        self.store = Store(database_path)
        self.data = self.store.load()
        self.cache = None
    def feed(self, stream_id, delivery_id, text, final=False):
        stream = self.data['streams'].setdefault(stream_id, {'pending': '', 'header': None, 'deliveries': []})
        if delivery_id in stream['deliveries']:
            return 0
        pending, header, rows = decode(stream['pending'], stream['header'], text, final)
        accepted = 0
        for row in rows:
            accepted += self.store.apply(self.data, row)
            self.store.save(self.data)
        stream.update(pending=pending, header=header)
        stream['deliveries'].append(delivery_id)
        self.store.save(self.data)
        return accepted
    def records(self):
        return [{k: row[k] for k in ('id','revision','category','amount_cents','note')}
                for key, row in sorted(self.data['records'].items()) if not row['deleted']]
    def summary(self):
        if self.cache is None:
            groups = {}
            for row in self.records():
                groups[row['category']] = groups.get(row['category'], 0) + row['amount_cents']
            self.cache = {'total_cents': sum(groups.values()), 'by_category': groups}
        return self.cache

def import_csv(database_path, text):
    obj = Ingestor(database_path)
    obj.feed('file-' + hashlib.sha256(text.encode()).hexdigest(), 'all', text, True)
    return obj.summary()
'''


def sources(variant, reference=False, mutant=None):
    files={"README.md":CONTRACT,"ledger/__init__.py":"from .api import Ingestor, import_csv\n",
           "ledger/parser.py":PARSER_REFERENCE,"ledger/store.py":STORE_REFERENCE,"ledger/api.py":API_REFERENCE}
    if not reference:
        files["ledger/api.py"]=API_STARTER
        if variant=="stream":
            files["ledger/parser.py"]=PARSER_NAIVE
            files["ledger/store.py"]=STORE_REFERENCE.replace("if previous and revision <= previous['revision']:","if previous and revision == previous['revision']:")
        elif variant=="state":
            files["ledger/store.py"]=STORE_REFERENCE.replace("if previous and revision <= previous['revision']:","if previous and revision == previous['revision']:")
            files["ledger/api.py"]=API_STARTER.replace("stream['deliveries']","self.data.setdefault('deliveries', [])")
        else: raise ValueError("unknown variant")
    if mutant:
        if mutant=="line-splitter": files["ledger/parser.py"]=PARSER_NAIVE
        elif mutant=="last-arrival": files["ledger/store.py"]=STORE_REFERENCE.replace("if previous and revision <= previous['revision']:","if False:")
        elif mutant=="non-atomic": files["ledger/api.py"]=API_REFERENCE.replace("next_state = copy.deepcopy(self.data)","next_state = self.data")
        elif mutant=="text-only-replay": files["ledger/api.py"]=API_REFERENCE.replace("json.dumps([text, final])","json.dumps(text)")
        elif mutant=="no-replay": files["ledger/api.py"]=API_REFERENCE.replace("if delivery_id in stream['deliveries']:","if False:")
        else: raise ValueError("unknown mutant")
    return files


def materialize(root,variant,reference=False,mutant=None):
    for name,text in sources(variant,reference,mutant).items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)


def csv_text(rows,header=FIELDS,ending="\n"):
    out=io.StringIO(newline="");w=csv.writer(out,lineterminator=ending)
    w.writerow(header)
    for row in rows:w.writerow([row[k] for k in header])
    return out.getvalue()


def row(key,revision,amount,category="work",note="",op="upsert"):
    return dict(zip(FIELDS,[key,str(revision),category,str(amount),note,op]))


def oracle_rows(documents):
    """Whole-document parser + independent max-revision fold; no streaming scanner."""
    versions={}
    for text in documents:
        for item in csv.DictReader(io.StringIO(text,newline="")):
            key=item["id"];rev=int(item["revision"])
            if key not in versions or versions[key][0]<rev: versions[key]=(rev,item)
    live=[]
    for key,(rev,item) in sorted(versions.items()):
        if item["op"]=="delete":continue
        live.append({"id":key,"revision":rev,"category":item["category"],"amount_cents":int(item["amount_cents"]),"note":item["note"]})
    groups={}
    for item in live:groups[item["category"]]=groups.get(item["category"],0)+item["amount_cents"]
    return {"records":live,"summary":{"total_cents":sum(groups.values()),"by_category":groups}}


def feed(text,stream="s",delivery="d",final=True):
    return {"op":"feed","stream":stream,"delivery":delivery,"text":text,"final":final}


def scenarios(seed,variant,public=False,change=True):
    rng=random.Random(seed ^ (0xA137 if variant=="stream" else 0xB241) ^ (0xD0C5 if public else 0))
    key=f"{'sample' if public else 'item'}-{rng.randrange(100,999)}";other=key+"-b"
    a=row(key,1,rng.randrange(400,1400),note='Review, "next"\n第二行')
    b=row(other,1,-137,"travel","credit")
    plain=csv_text([row(key,1,200)])
    quoted=csv_text([a,b],ending="\r\n")
    newer=csv_text([row(key,3,-250,"new","correction")],header=list(reversed(FIELDS)))
    deleted=csv_text([row(key,4,"","","",op="delete")])
    stale=csv_text([row(key,2,9999,"wrong")])
    checks=[]
    def add(name,tier,ops,documents,accepted=None,error_indices=(),snapshots=None):
        checks.append({"name":name,"tier":tier,"ops":ops,"expected":oracle_rows(documents),
                       "accepted":accepted or {},"error_indices":list(error_indices),"snapshots":snapshots or {}})
    add("legacy-files",1,[{"op":"legacy","text":plain},{"op":"legacy","text":newer},{"op":"legacy","text":newer}],
        [plain,newer,newer])
    add("fragmented-records",1,[feed(plain[:9],delivery="a",final=False),{"op":"restart"},feed(plain[9:],delivery="b")],
        [plain],accepted={0:0,2:1})
    i=quoted.index('"next')+1
    add("quoted-boundaries",2,[feed(quoted[:i],delivery="a",final=False),{"op":"restart"},feed(quoted[i:],delivery="b")],
        [quoted],accepted={0:0,2:2})
    cuts=sorted(rng.sample(range(1,len(quoted)),min(13,len(quoted)-1)))
    parts=[quoted[x:y] for x,y in zip([0]+cuts,cuts+[len(quoted)])]
    ops=[]
    for n,part in enumerate(parts):
        operation=feed(part,delivery=str(n),final=n==len(parts)-1)
        ops.extend([operation,{"op":"restart"},copy.deepcopy(operation)])
    add("partition-replay",2,ops,[quoted],accepted={i:0 for i,o in enumerate(ops) if i%3==2})
    add("independent-streams",2,[feed(plain,stream="left"),feed(newer,stream="right"),{"op":"restart"}],
        [plain,newer],accepted={0:1,1:1})
    add("revisions-and-delete",3,[{"op":"snapshot"},feed(plain,stream="one"),{"op":"snapshot"},
        feed(newer,stream="two"),feed(deleted,stream="three"),{"op":"restart"},feed(stale,stream="four")],
        [plain,newer,deleted,stale],accepted={1:1,3:1,4:1,6:0},snapshots={2:oracle_rows([plain])})
    invalid=csv_text([row(key,1,20),row(other,1,"not-an-int")])
    fixed=csv_text([row(key,1,20),row(other,1,30)])
    add("atomic-corrected-retry",3,[feed(invalid),{"op":"snapshot"},{"op":"restart"},feed(fixed)],
        [fixed],accepted={3:2},error_indices=[0],snapshots={1:oracle_rows([])})
    # A failed tail must not consume the header/pending prefix from an earlier delivery.
    head=plain[:plain.index("\n")+1]+key+",1,work,"
    add("atomic-pending",3,[feed(head,delivery="prefix",final=False),feed("bad,note,upsert\n",delivery="tail"),
        {"op":"restart"},feed("71,note,upsert\n",delivery="tail")],
        [csv_text([row(key,1,71,note="note")])],error_indices=[1],accepted={0:0,3:1})
    add("final-without-newline",2,[feed(quoted.rstrip("\r\n"))],[quoted])
    if change:
        add("conflicting-replay",3,[feed(plain),{"op":"restart"},feed(plain+"\n"),feed(plain,final=False),feed(plain)],
            [plain],error_indices=[2,3],accepted={0:1,4:0})
        add("incomplete-final-rollback",3,[feed(plain[:10],delivery="a",final=False),
            feed(plain[10:]+f'{other},1,work,88,"open',delivery="b"),{"op":"restart"},feed(plain[10:],delivery="b")],
            [plain],error_indices=[1],accepted={3:1})
    if public:
        wanted={"legacy-files","fragmented-records","revisions-and-delete"}
        if change:wanted.add("conflicting-replay")
        return [c for c in checks if c["name"] in wanted]
    return checks
