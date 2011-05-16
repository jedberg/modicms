import os
import urllib

from modicms.base import _Component


class _MarkupComponent(_Component):
    def _morph_path(self, metadata):
        metadata = metadata.copy()
        output_path = metadata['output_path']
        output_root, old_extension = os.path.splitext(output_path)
        metadata['output_path'] = output_root + self.output_extension
        return metadata

    def process_and_return(self, metadata, data):
        morphed = self._morph_path(metadata)
        data = self._process(morphed, data)
        return morphed, data

    def _process(slf, metadata, data):
        raise NotImplementedError()

    def is_invalid(self, metadata, source_mtime):
        morphed = self._morph_path(metadata)
        return super(_MarkupComponent, self).is_invalid(
            morphed,
            source_mtime
        )


try:
    import markdown

    class InterpretMarkdown(_MarkupComponent):
        output_extension = '.html'

        def _process(self, metadata, data):
            md = markdown.Markdown()
            data = md.convert(data)
            return data

except ImportError:
    pass


try:
    import clevercss

    class ConvertCleverCSS(_MarkupComponent):
        output_extension = '.css'

        def _process(self, metadata, data):
            return clevercss.convert(data, minified=True)

except ImportError:
    pass


class CompressJavascript(_MarkupComponent):
    output_extension = '.js'

    def _process(self, metadata, data):
        params = urllib.urlencode({
            'js_code': data,
            'compilation_level': 'SIMPLE_OPTIMIZATIONS',
            'output_format': 'text',
            'output_info': 'compiled_code',
        })

        resp = urllib.urlopen(
            'http://closure-compiler.appspot.com/compile',
            params
        )

        return resp.read()
