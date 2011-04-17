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
                self.log.debug("Processing '%s'..." % path)
                super(Scan, self).process(metadata, None)
            super(Scan, self).iteration_complete()


class ByPath(_Component):
    def __init__(self, handlers):
        self.handlers = []
        for expr, handler in handlers.iteritems():
            self.handlers.append((expr, handler))
        super(ByPath, self).__init__()

    def process(self, metadata, data):
        path = metadata['input_path']

        # TODO: deterministic handling of multiple matches
        for expr, handler in self.handlers:
            result = re.search(expr, path)
            if result:
                self.log.debug("Matched expression /%s/" % expr)
                handler.process(metadata, data)
                return

        self.log.debug("No path match found. Skipping.")

    def iteration_complete(self):
        for expr, handler in self.handlers:
            handler.iteration_complete()


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
        def process(self, metadata, data):
            # change the output file's extension
            output_root, old_extension = os.path.splitext(
                metadata['output_path'])
            metadata['output_path'] = output_root + '.html'

            md = markdown.Markdown()
            data = md.convert(data)

            super(InterpretMarkdown, self).process(metadata, data)

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


class _TerminalComponent(_Component):
    def __init__(self, root):
        self.root = root
        super(_TerminalComponent, self).__init__()

    def process(self, metadata, data):
        relative_output_path = metadata['output_path'][1:]
        absolute = os.path.join(self.root, relative_output_path)

        # make sure the containing directories exist
        dir = os.path.dirname(absolute)
        if not os.path.exists(dir):
            os.makedirs(dir)

        self._process(absolute, metadata, data)
        self.log.info(absolute)

    def iteration_complete(self):
        pass


class WriteTo(_TerminalComponent):
    def _process(self, absolute, metadata, data):
        # write out the file
        with open(absolute, 'wb') as f:
            f.write(data)

        # set the mtime
        os.utime(absolute, (metadata['mtime'], metadata['mtime']))


class CopyTo(_TerminalComponent):
    def _process(self, absolute, metadata, data):
        shutil.copy2(metadata['input_path'], absolute)
