import unittest
from app import changes

class WatchTests(unittest.TestCase):
    def row(self,h='a',inode=1):return {'sha256':h,'size':1,'mtime_ns':1,'inode':inode}
    def test_rename(self):self.assertEqual(changes({'old':self.row()},{'new':self.row()})[0]['type'],'rename')
    def test_modify(self):self.assertEqual(changes({'x':self.row()},{'x':self.row('b')})[0]['type'],'modify')
    def test_delete_no_hash(self):self.assertIsNone(changes({'x':self.row()},{})[0]['sha256'])
    def test_distinct_inode_not_rename(self):self.assertEqual({e['type'] for e in changes({'x':self.row()},{'y':self.row(inode=2)})},{'create','delete'})
