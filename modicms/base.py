import logging


class _ComponentWrapper(object):
    def __init__(self, head, wrapped):
        self.head = head
        self.wrapped = wrapped

    def __rshift__(self, next):
        self.wrapped.next = next
        return _ComponentWrapper(self.head, next)

    def process(self, metadata, data):
        self.head.process(metadata, data)

    def all_items_processed(self):
        self.head.all_items_processed()

    def is_invalid(self, metadata, source_mtime):
        return self.head.is_invalid(metadata, source_mtime)


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

    def all_items_processed(self):
        self._check_pipeline_continues()
        self.next.all_items_processed()

    def is_invalid(self, metadata, source_mtime):
        return self.next.is_invalid(metadata, source_mtime)
