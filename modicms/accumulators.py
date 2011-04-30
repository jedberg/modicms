import sys
import datetime

from base import _Component


class _Accumulate(_Component):
    def __init__(self):
        self.items = []
        super(_Accumulate, self).__init__()

    def is_invalid(self, metadata, source_mtime):
        return True

    def process(self, metadata, data):
        self.items.append((metadata, data))

    def all_items_processed(self):
        mtime, updates = self._accumulate(self.items)

        for metadata, data in self.items:
            metadata.update(updates)
            new_mtime = max(mtime, metadata['mtime'])
            if super(_Accumulate, self).is_invalid(metadata, new_mtime):
                super(_Accumulate, self).process(metadata, data)

    def _accumulate(self, items):
        raise Exception("not implemented")


try:
    from dateutil.parser import parse as _parse_date
except ImportError:
    def _parse_date(date_str):
        return datetime.strptime(date_str, '%Y/%m/%d %H:%M:%S')


class AccumulateBlogEntries(_Accumulate):
    def __init__(self, path='/blog'):
        self.path = path
        super(AccumulateBlogEntries, self).__init__()

    def _accumulate(self, items):
        most_recent_modification = 0
        blog_entries = []

        for metadata, data in items:
            if metadata['output_path'].startswith(self.path):
                title = metadata.get('title', None)
                if not title:
                    print >>sys.stderr, "%s has no title, skipping." % (
                                                metadata['input_path'])

                mtime = metadata['mtime']
                post_date = datetime.datetime.fromtimestamp(mtime)
                date_str = metadata.get('date', None)
                if date_str:
                    post_date = _parse_date(date_str)

                most_recent_modification = max(most_recent_modification, mtime)
                blog_entries.append((post_date,
                                     metadata['output_path'],
                                     title))

        blog_entries.sort(key=lambda x: x[0], reverse=True)

        return most_recent_modification, {
            'blog_entries': blog_entries
        }
