import os
import re

from modicms.base import _Component


class Read(_Component):
    def process_and_return(self, metadata, data):
        assert data is None

        with open(metadata['input_path'], 'r') as f:
            data = f.read()

        return metadata, data


class Scan(_Component):
    """Scan a directory and kick off the pipeline.

    """
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

                if super(Scan, self).is_invalid(metadata, metadata['mtime']):
                    self.log.debug("Processing '%s'..." % path)
                    super(Scan, self).process(metadata, None)
                else:
                    self.log.debug("Skipping unmodified file '%s'" % path)
        super(Scan, self).all_items_processed()


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

    def all_items_processed(self):
        for expr, handler in self.handlers:
            handler.all_items_processed()

    def is_invalid(self, metadata, source_mtime):
        expr, handler = self._get_handler(metadata)
        if handler:
            return handler.is_invalid(metadata, source_mtime)
