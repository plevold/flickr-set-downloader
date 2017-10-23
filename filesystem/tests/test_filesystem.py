# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import unittest
import sys
import os.path

_dirname = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, _dirname)
import filesystem


class MockFilesystemOperations:
    def __init__(self, exists_result=True):
        self.exists_result = exists_result
        self.mkdir_called = False
        self.exists_called = False
        self.rename_called = False
        self.delete_called = False

    def mkdir(self, _):
        self.mkdir_called = True

    def exists(self, _):
        self.exists_called = True
        return self.exists_result

    def rename(self, _, __):
        self.rename_called = True

    def delete(self, _):
        self.delete_called = True


class MockCreator:
    def __init__(self):
        self.creator_called = False

    def creator(self, _):
        self.creator_called = True


class TestFileSystem(unittest.TestCase):

    def test_add_file(self):
        mock_fsops = MockFilesystemOperations()
        mock_creator = MockCreator()
        fs = filesystem.Filesystem('dummy dir', fsops=mock_fsops)

        fs.add('a', 'name1', mock_creator.creator)

        self.assertTrue(mock_creator.creator_called)
        self.assertTrue(fs.state.has_identifier('a'))
        self.assertEqual('name1', fs.state.get_filename('a'))


    def test_add_file_when_filename_exists(self):
        mock_fsops = MockFilesystemOperations()
        mock_creator1 = MockCreator()
        mock_creator2 = MockCreator()
        fs = filesystem.Filesystem('dummy dir', fsops=mock_fsops)

        fs.add('a', 'name1', mock_creator1.creator)
        fs.add('b', 'name1', mock_creator2.creator)
        fs.finish_sync()

        self.assertTrue(mock_creator1.creator_called)
        self.assertTrue(mock_creator2.creator_called)
        self.assertTrue(fs.state.has_identifier('b'))
        self.assertFalse(fs.state.has_identifier('a'))
        self.assertTrue(mock_fsops.delete_called)


    def test_two_syncs(self):
        mock_fsops = MockFilesystemOperations()
        mock_creator1 = MockCreator()
        mock_creator2 = MockCreator()
        mock_creator3 = MockCreator()
        mock_creator4 = MockCreator()
        fs = filesystem.Filesystem('dummy dir', fsops=mock_fsops)

        # First sync
        fs.add('a', 'name1', mock_creator1.creator)
        fs.add('b', 'name2', mock_creator2.creator)
        fs.finish_sync()
        # Second sync, nothing new
        fs.add('a', 'name1', mock_creator3.creator)
        fs.add('b', 'name2', mock_creator4.creator)
        fs.finish_sync()

        self.assertTrue(mock_creator1.creator_called)
        self.assertTrue(mock_creator2.creator_called)
        self.assertFalse(mock_creator3.creator_called)
        self.assertFalse(mock_creator4.creator_called)
        self.assertTrue(fs.state.has_identifier('a'))
        self.assertTrue(fs.state.has_identifier('b'))
        self.assertEqual('name1', fs.state.get_filename('a'))
        self.assertEqual('name2', fs.state.get_filename('b'))
        self.assertFalse(mock_fsops.delete_called)


    def test_second_sync_with_new_name(self):
        mock_fsops = MockFilesystemOperations()
        mock_creator1 = MockCreator()
        mock_creator2 = MockCreator()
        mock_creator3 = MockCreator()
        mock_creator4 = MockCreator()
        fs = filesystem.Filesystem('dummy dir', fsops=mock_fsops)

        # First sync
        fs.add('a', 'name1', mock_creator1.creator)
        fs.add('b', 'name2', mock_creator2.creator)
        fs.finish_sync()
        # Second sync, b has new name
        fs.add('a', 'name1', mock_creator3.creator)
        fs.add('b', 'name3', mock_creator4.creator)
        fs.finish_sync()

        self.assertTrue(mock_creator1.creator_called)
        self.assertTrue(mock_creator2.creator_called)
        self.assertFalse(mock_creator3.creator_called)
        self.assertFalse(mock_creator4.creator_called)
        self.assertTrue(fs.state.has_identifier('a'))
        self.assertTrue(fs.state.has_identifier('b'))
        self.assertEqual('name1', fs.state.get_filename('a'))
        self.assertEqual('name3', fs.state.get_filename('b'))
        self.assertFalse(mock_fsops.delete_called)


    def test_second_sync_adds_file_with_same_name(self):
        mock_fsops = MockFilesystemOperations()
        mock_creator1 = MockCreator()
        mock_creator2 = MockCreator()
        mock_creator3 = MockCreator()
        mock_creator4 = MockCreator()
        mock_creator5 = MockCreator()
        fs = filesystem.Filesystem('dummy dir', fsops=mock_fsops)

        # First sync
        fs.add('a', 'name1', mock_creator1.creator)
        fs.add('b', 'name2', mock_creator2.creator)
        fs.finish_sync()
        # Second sync, c takes name of b
        fs.add('a', 'name1', mock_creator3.creator)
        fs.add('c', 'name2', mock_creator4.creator)
        fs.add('b', 'name3', mock_creator5.creator)

        self.assertTrue(mock_creator1.creator_called)
        self.assertTrue(mock_creator2.creator_called)
        self.assertFalse(mock_creator3.creator_called)
        self.assertTrue(mock_creator4.creator_called)
        self.assertFalse(mock_creator5.creator_called)
        self.assertTrue(fs.state.has_identifier('a'))
        self.assertTrue(fs.state.has_identifier('b'))
        self.assertTrue(fs.state.has_identifier('c'))
        self.assertEqual('name1', fs.state.get_filename('a'))
        self.assertEqual('name3', fs.state.get_filename('b'))
        self.assertEqual('name2', fs.state.get_filename('c'))
        self.assertTrue('name1' in fs.state.touched_filenames)
        self.assertTrue('name2' in fs.state.touched_filenames)
        self.assertTrue('name3' in fs.state.touched_filenames)
        self.assertFalse(mock_fsops.delete_called)


    def test_second_sync_removes_file(self):
        mock_fsops = MockFilesystemOperations()
        mock_creator1 = MockCreator()
        mock_creator2 = MockCreator()
        mock_creator3 = MockCreator()
        mock_creator4 = MockCreator()
        mock_creator5 = MockCreator()
        fs = filesystem.Filesystem('dummy dir', fsops=mock_fsops)

        # First sync
        fs.add('a', 'name1', mock_creator1.creator)
        fs.add('b', 'name2', mock_creator2.creator)
        fs.add('c', 'name3', mock_creator3.creator)
        fs.finish_sync()
        # Second sync, b is removed
        fs.add('a', 'name1', mock_creator4.creator)
        fs.add('c', 'name3', mock_creator5.creator)
        fs.finish_sync()

        self.assertTrue(mock_creator1.creator_called)
        self.assertTrue(mock_creator2.creator_called)
        self.assertTrue(mock_creator3.creator_called)
        self.assertFalse(mock_creator4.creator_called)
        self.assertFalse(mock_creator5.creator_called)
        self.assertTrue(mock_fsops.delete_called)
        self.assertTrue(fs.state.has_identifier('a'))
        self.assertFalse(fs.state.has_identifier('b'))
        self.assertTrue(fs.state.has_identifier('c'))
        self.assertEqual('name1', fs.state.get_filename('a'))
        self.assertEqual('name3', fs.state.get_filename('c'))


    def test_complex_case(self):
        mock_fsops = MockFilesystemOperations()
        def mock_delete(x):
            print("Delete {}".format(x))
        mock_fsops.delete = mock_delete
        mock_creator = MockCreator()
        mock_creator_a = MockCreator()
        mock_creator_c = MockCreator()
        mock_creator_d = MockCreator()
        mock_creator_e = MockCreator()
        mock_creator_f = MockCreator()
        fs = filesystem.Filesystem('dummy dir', fsops=mock_fsops)

        # First sync
        print('start')
        fs.add('a', 'name1', mock_creator.creator)
        fs.add('b', 'name2', mock_creator.creator)
        fs.add('c', 'name3', mock_creator.creator)
        fs.add('d', 'name4', mock_creator.creator)
        fs.finish_sync()
        # Second sync:
        # - b is removed
        # - c and d switches name
        # - e is added with name of b
        # - f is added
        fs.add('a', 'name1', mock_creator_a.creator)
        fs.add('c', 'name4', mock_creator_c.creator)
        fs.add('d', 'name3', mock_creator_d.creator)
        fs.add('e', 'name2', mock_creator_e.creator)
        fs.add('f', 'name6', mock_creator_f.creator)
        fs.finish_sync()
        print('done')

        self.assertFalse(mock_creator_a.creator_called)
        self.assertFalse(mock_creator_c.creator_called)
        self.assertFalse(mock_creator_d.creator_called)
        self.assertTrue(mock_creator_e.creator_called)
        self.assertTrue(mock_creator_f.creator_called)

        self.assertTrue(fs.state.has_identifier('a'))
        self.assertFalse(fs.state.has_identifier('b'))
        self.assertTrue(fs.state.has_identifier('c'))
        self.assertTrue(fs.state.has_identifier('d'))
        self.assertTrue(fs.state.has_identifier('e'))
        self.assertTrue(fs.state.has_identifier('f'))

        self.assertEqual('name1', fs.state.get_filename('a'))
        self.assertEqual('name4', fs.state.get_filename('c'))
        self.assertEqual('name3', fs.state.get_filename('d'))
        self.assertEqual('name2', fs.state.get_filename('e'))
        self.assertEqual('name6', fs.state.get_filename('f'))

if __name__ == '__main__':
    unittest.main()