import cStringIO as StringIO

from modicms.base import _Component


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
