import os

from modicms.base import _Component

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

        def is_invalid(self, metadata, source_mtime):
            self._morph_path(metadata)
            return super(InterpretMarkdown, self).is_invalid(metadata,
                                                             source_mtime)

except ImportError:
    pass
