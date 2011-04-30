import os

from modicms.base import _Component

try:
    from mako.lookup import TemplateLookup
    from mako import exceptions

    class WrapInMako(_Component):
        def __init__(self, template_path):
            self.default_template = template_path
            super(WrapInMako, self).__init__()

        def _get_template(self, metadata):
            lookup = TemplateLookup(directories=[metadata['root']])
            template_name = metadata.get('template', self.default_template)
            try:
                return lookup.get_template(template_name)
            except:
                pass

        def process(self, metadata, data):
            template = self._get_template(metadata)

            try:
                rendered = template.render(content=data, **metadata)
            except:
                self.log.error(exceptions.text_error_template().render())
                return

            super(WrapInMako, self).process(metadata, rendered)

        def is_invalid(self, metadata, source_mtime):
            template = self._get_template(metadata)
            template_mtime = os.path.getmtime(template.filename)
            latest_source_mtime = max(template_mtime, source_mtime)

            return super(WrapInMako, self).is_invalid(metadata,
                                                      latest_source_mtime)


except ImportError:
    pass
