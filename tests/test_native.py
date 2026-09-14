import tempfile
import unittest
from pathlib import Path
from native import watch


class NativeTests(unittest.TestCase):
    def test_transient_file_events_survive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'watched';root.mkdir()
            result=watch(root,Path(temporary)/'watch.sqlite',1,collector=lambda *_:{'events':[{'kind':'Created','path':'gone.txt'},{'kind':'Deleted','path':'gone.txt'}],'overflow':False})
            self.assertEqual([row['type'] for row in result['events']],['create','delete'])
            self.assertTrue(all(row['sha256'] is None for row in result['events']))

    def test_overflow_is_not_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'watched';root.mkdir()
            result=watch(root,Path(temporary)/'watch.sqlite',1,collector=lambda *_:{'events':[],'overflow':True})
            self.assertFalse(result['ok'])
