import os
import sys
import shutil

from modicms.base import _Component


class _LocalTerminalComponent(_Component):
    def __init__(self, root):
        self.root = root
        super(_LocalTerminalComponent, self).__init__()

    def _absolute(self, metadata):
        relative_output_path = metadata['output_path'][1:]
        return os.path.join(self.root, relative_output_path)

    def process(self, metadata, data):
        absolute = self._absolute(metadata)

        # make sure the containing directories exist
        dir = os.path.dirname(absolute)
        if not os.path.exists(dir):
            os.makedirs(dir)

        print >>sys.stderr, metadata['output_path']
        self._process(absolute, metadata, data)

    def all_items_processed(self):
        pass

    def is_invalid(self, metadata, source_mtime):
        try:
            absolute = self._absolute(metadata)
            target_mtime = os.path.getmtime(absolute)
            return target_mtime < source_mtime
        except OSError:
            return True


class WriteTo(_LocalTerminalComponent):
    def _process(self, absolute, metadata, data):
        # write out the file
        with open(absolute, 'wb') as f:
            f.write(data)


class CopyTo(_LocalTerminalComponent):
    def _process(self, absolute, metadata, data):
        shutil.copy2(metadata['input_path'], absolute)


try:
    import boto

    import time
    import mimetypes

    mimetypes.types_map.setdefault('.ttf', 'application/octet-stream')
    mimetypes.types_map.setdefault('.otf', 'application/octet-stream')
    mimetypes.types_map.setdefault('.eot', 'application/vnd.ms-fontobject')
    mimetypes.types_map.setdefault('.woff', 'application/x-woff')

    class _S3TerminalComponent(_Component):
        def __init__(self, bucket):
            self.connection = boto.connect_s3()
            self.bucket = self.connection.get_bucket(bucket)
            super(_Component, self).__init__()

        def process(self, metadata, data):
            key = self.bucket.new_key(metadata['output_path'])
            key.set_metadata('modicms_mtime', str(time.time()))

            type, encoding = mimetypes.guess_type(metadata['output_path'])
            assert type is not None
            headers = {
                'Content-Type': type,
            }

            print >>sys.stderr, metadata['output_path']
            self._process(key, headers, metadata, data)

        def all_items_processed(self):
            pass

        def is_invalid(self, metadata, source_mtime):
            key = self.bucket.get_key(metadata['output_path'])
            if key:
                mtime = key.get_metadata('modicms_mtime')
                if mtime:
                    return float(mtime) < source_mtime
            return True

    class WriteToS3(_S3TerminalComponent):
        def _process(self, key, headers, metadata, data):
            key.set_contents_from_string(data,
                                         headers=headers,
                                         policy='public-read')

    class CopyToS3(_S3TerminalComponent):
        def _process(self, key, headers, metadata, data):
            key.set_contents_from_filename(metadata['input_path'],
                                           headers=headers,
                                           policy='public-read')

except ImportError:
    pass
