import os
import re
import shutil
import logging
import cStringIO as StringIO


class _ComponentWrapper(object):
    def __init__(self, head, wrapped):
        self.head = head
        self.wrapped = wrapped

    def __rshift__(self, next):
        self.wrapped.next = next
        return _ComponentWrapper(self.head, next)

    def process(self, metadata, data):
        self.head.process(metadata, data)

    def iteration_complete(self):
        self.head.iteration_complete()

    def get_mtime(self, metadata):
        return self.head.get_mtime(metadata)


class _Component(object):
    def __init__(self):
        self.next = None
        self.log = logging.getLogger(self.__class__.__name__)

    def __rshift__(self, next):
        self.next = next
        return _ComponentWrapper(self, next)

    def _check_pipeline_continues(self):
        if self.next is None:
            name = self.__class__.__name__
            raise Exception("Pipeline terminates prematurely at %s" % name)

    def process(self, metadata, data):
        self._check_pipeline_continues()
        self.next.process(metadata, data)

    def iteration_complete(self):
        self._check_pipeline_continues()
        self.next.iteration_complete()

    def get_mtime(self, metadata):
        return self.next.get_mtime(metadata)


class Scan(_Component):
    def __init__(self, root, ignore_dotfiles=True):
        self.root = os.path.abspath(root)
        self.ignore_dotfiles = ignore_dotfiles
        super(Scan, self).__init__()

    def _build_metadata(self, path):
        # determine output path from input path
        prefix = os.path.commonprefix([self.root, os.path.abspath(path)])
        output_path = path[len(prefix):]

        return {
            'root': self.root,
            'input_path': path,
            'output_path': output_path,
            'mtime': os.path.getmtime(path),
        }

    def __del__(self):
        try:
            self._scan()
        except Exception, e:
            import traceback
            traceback.print_exc(e)

    def _scan(self):
        for root, dirs, files in os.walk(self.root):
            if self.ignore_dotfiles:
                to_remove = [dir for dir in dirs if dir.startswith('.')]
                for dotdir in to_remove:
                    self.log.debug("Skipping dotdir '%s'" % dotdir)
                    dirs.remove(dotdir)

            for file in files:
                if self.ignore_dotfiles and file.startswith('.'):
                    self.log.debug("Skipping dotfile '%s'" % file)
                    continue
                path = os.path.join(root, file)
                metadata = self._build_metadata(path)

                target_mtime = super(Scan, self).get_mtime(metadata)
                if metadata['mtime'] > target_mtime:
                    self.log.info("Processing '%s'..." % path)
                    super(Scan, self).process(metadata, None)
                else:
                    self.log.info("Skipping unmodified file '%s'" % path)
            super(Scan, self).iteration_complete()


class MatchPath(_Component):
    def __init__(self):
        self.handlers = []
        super(MatchPath, self).__init__()

    def match(self, expr, handler):
        self.handlers.append((expr, handler))
        return self

    def _get_handler(self, metadata):
        path = metadata['input_path']

        for expr, handler in self.handlers:
            result = re.search(expr, path)
            if result:
                return expr, handler

        return None, None

    def process(self, metadata, data):
        expr, handler = self._get_handler(metadata)
        if handler:
            self.log.debug("Matched expression /%s/" % expr)
            handler.process(metadata, data)
        else:
            self.log.info("No path match found. Skipping.")

    def iteration_complete(self):
        for expr, handler in self.handlers:
            handler.iteration_complete()

    def get_mtime(self, metadata):
        expr, handler = self._get_handler(metadata)
        if handler:
            return handler.get_mtime(metadata)


class Read(_Component):
    def process(self, metadata, data):
        assert data is None

        with open(metadata['input_path'], 'r') as f:
            data = f.read()

        super(Read, self).process(metadata, data)


class ParseHeaders(_Component):
    def process(self, metadata, data):
        buffer = StringIO.StringIO(data)

        for line in buffer:
            if line == '\n':
                break

            key, value = line.split(':', 1)
            key = key.lower().replace('-', '_')
            value = value.strip()
            metadata[key] = value

        rest = buffer.read()
        super(ParseHeaders, self).process(metadata, rest)


try:
    import markdown

    class InterpretMarkdown(_Component):
        def _morph_path(self, metadata):
            # change the output file's extension
            output_root, old_extension = os.path.splitext(
                metadata['output_path'])
            metadata['output_path'] = output_root + '.html'

        def process(self, metadata, data):
            self._morph_path(metadata)

            md = markdown.Markdown()
            data = md.convert(data)

            super(InterpretMarkdown, self).process(metadata, data)

        def get_mtime(self, metadata):
            self._morph_path(metadata)
            return super(InterpretMarkdown, self).get_mtime(metadata)

except ImportError:
    pass

try:
    from mako.template import Template
    from mako.lookup import TemplateLookup
    from mako import exceptions

    class WrapInMako(_Component):
        def __init__(self, template_path):
            self.default_template = template_path
            super(WrapInMako, self).__init__()

        def process(self, metadata, data):
            lookup = TemplateLookup(directories=[metadata['root']])

            try:
                template_name = metadata.get('template', self.default_template)
                template = lookup.get_template(template_name)
                rendered = template.render(content=data, **metadata)
            except:
                self.log.error(exceptions.text_error_template().render())
                return

            super(WrapInMako, self).process(metadata, rendered)

except ImportError:
    pass


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

        self._process(absolute, metadata, data)
        self.log.info(absolute)

    def iteration_complete(self):
        pass

    def get_mtime(self, metadata):
        try:
            absolute = self._absolute(metadata)
            return os.path.getmtime(absolute)
        except OSError:
            pass


class WriteTo(_LocalTerminalComponent):
    def _process(self, absolute, metadata, data):
        # write out the file
        with open(absolute, 'wb') as f:
            f.write(data)

        # set the mtime
        os.utime(absolute, (metadata['mtime'], metadata['mtime']))


class CopyTo(_LocalTerminalComponent):
    def _process(self, absolute, metadata, data):
        shutil.copy2(metadata['input_path'], absolute)


try:
    import boto
    from boto.s3.key import Key

    import time
    import mimetypes

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

            self._process(key, headers, metadata, data)

        def iteration_complete(self):
            pass

        def get_mtime(self, metadata):
            key = self.bucket.get_key(metadata['output_path'])
            if key:
                mtime = key.get_metadata('modicms_mtime')
                if mtime:
                    return float(mtime)

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
