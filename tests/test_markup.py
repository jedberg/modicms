try:
    from modicms import InterpretMarkdown

    class TestMarkdown(object):
        def setUp(self):
            self.md = InterpretMarkdown()

        def testMorphPath(self):
            metadata, data = self.md.process_and_return(
                {'output_path': 'test.md'},
                ''
            )

            assert metadata['output_path'] == 'test.html'

        def testConvertMarkdown(self):
            metadata, data = self.md.process_and_return(
                {'output_path': 'test.md'},
                '*Hello*'
            )

            assert data == '<p><em>Hello</em></p>'
except ImportError:
    pass


try:
    from modicms import ConvertCleverCSS

    class TestCleverCSS(object):
        def setUp(self):
            self.ccss = ConvertCleverCSS()

        def testMorphPath(self):
            metadata, data = self.ccss.process_and_return(
                {'output_path': 'test.ccss'},
                ''
            )

            assert metadata['output_path'] == 'test.css'

        def testConvertCleverCSS(self):
            metadata, data = self.ccss.process_and_return(
                {'output_path': 'test.ccss'},
                'p:\n\tcolor: red'
            )

            assert data == 'p{color:#f00}'

except ImportError:
    pass


from modicms import CompressJavascript

class TestCompressJavascript(object):
    def setUp(self):
        self.js = CompressJavascript()

    def testDoesntMorphPath(self):
        metadata, data = self.js.process_and_return(
            {'output_path': 'test.js'}, 
            ''
        )

        assert metadata['output_path'] == 'test.js'

    def testCompressJavascript(self):
        input = 'function test() {\nalert("Test!");}'
        metadata, data = self.js.process_and_return(
            {'output_path': 'test.js'},
            input
        )

        assert len(data) < len(input)
