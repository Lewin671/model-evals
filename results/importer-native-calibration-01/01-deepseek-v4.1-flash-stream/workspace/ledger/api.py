import copy
import hashlib

from .parser import decode
from .store import Store


class Ingestor:
    def __init__(self, database_path):
        self.store = Store(database_path)
        self.data = self.store.load()
        self.cache = None

    def feed(self, stream_id, delivery_id, text, final=False):
        stream = self.data['streams'].get(stream_id)
        if stream is not None:
            prior = stream.get('deliveries', {}).get(str(delivery_id))
            if prior is not None:
                if prior.get('text') == text and bool(prior.get('final')) == bool(final):
                    return 0
                raise ValueError('conflicting retry')
        new = copy.deepcopy(self.data)
        stream = new['streams'].get(stream_id)
        if stream is None:
            stream = {'pending': '', 'header': None, 'deliveries': {}}
            new['streams'][stream_id] = stream
        pending, header, rows = decode(stream['pending'], stream['header'], text, final)
        accepted = 0
        for row in rows:
            if self.store.apply(new, row):
                accepted += 1
        stream['pending'] = pending
        stream['header'] = header
        stream['deliveries'][str(delivery_id)] = {'text': text, 'final': bool(final)}
        self.data = new
        self.cache = None
        self.store.save(self.data)
        return accepted

    def records(self):
        return [{k: row[k] for k in ('id', 'revision', 'category', 'amount_cents', 'note')}
                for _, row in sorted(self.data['records'].items()) if not row['deleted']]

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
