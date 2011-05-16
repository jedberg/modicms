import os
import tempfile

from modicms.input import Read

TEST_STRING = "This is a test of the emergency broadcast system."

class TestRead(object):
    def setUp(self):
        fd, name = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(TEST_STRING)
        self.name = name

    def tearDown(self):
        os.unlink(self.name)

    def testRead(self):
        reader = Read()
        metadata, data = reader.process_and_return(
            {'input_path': self.name}, 
            None
        )
        assert data == TEST_STRING
