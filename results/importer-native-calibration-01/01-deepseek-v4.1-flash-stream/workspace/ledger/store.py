import json
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
        key = row.get('id', '')
        if not key:
            raise ValueError('invalid id')
        try:
            revision = int(row['revision'])
        except (KeyError, TypeError, ValueError):
            raise ValueError('invalid revision')
        if revision <= 0:
            raise ValueError('invalid revision')
        op = row.get('op')
        if op not in ('upsert', 'delete'):
            raise ValueError('invalid op')
        if op == 'upsert':
            try:
                amount = int(row['amount_cents'])
            except (KeyError, TypeError, ValueError):
                raise ValueError('invalid amount')
        else:
            amount = 0
        previous = data['records'].get(key)
        if previous is not None and revision <= previous['revision']:
            return False
        data['records'][key] = {
            'id': key,
            'revision': revision,
            'category': row.get('category', ''),
            'amount_cents': amount,
            'note': row.get('note', ''),
            'deleted': op == 'delete',
        }
        return True
