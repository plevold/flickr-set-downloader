# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import pickle
import uuid

FSYS_STATE_FILENAME = './filesystem-state.pickle'


class FilesystemState:
    def __init__(self, dirname):
        path = os.path.join(dirname, FSYS_STATE_FILENAME)
        if os.path.exists(path):
            data = pickle.load(open(path, 'rb'))
            self.filenames = data['filenames']
            self.identifiers = data['identifiers']
        else:
            self.filenames = {}
            self.identifiers = {}
        self.dirname = dirname
        self.clear_temporary_filenames()
        self.clear_touched_filenames()


    def save(self):
        path = os.path.join(self.dirname, FSYS_STATE_FILENAME)
        data = {'filenames': self.filenames, 'identifiers': self.identifiers}
        pickle.dump(data, open(path, 'wb'))


    def add(self, identifier, filename, temporary=False):
        if self.has_identifier(identifier):
            raise RuntimeError('Cannot add <{}, {}> - identifier already exists'
                                .format(identifier, filename))
        if self.has_filename(filename):
            raise RuntimeError('Cannot add <{}, {}> - filename already exists'
                                .format(identifier, filename))

        self.filenames[identifier] = filename
        self.identifiers[filename] = identifier
        if not temporary:
            self.touched_filenames.add(filename)
        else:
            self.temporary_filenames.add(filename)


    def touch(self, identifier, filename):
        if not self.has_identifier(identifier):
            raise RuntimeError('Cannot touch <{}, {}> - identifier doesn\'t exists'
                                .format(identifier, filename))
        if not self.has_filename(filename):
            raise RuntimeError('Cannot touch <{}, {}> - filename doesn\'t exists'
                                .format(identifier, filename))
        self.touched_filenames.add(filename)


    def remove_identifier(self, identifier):
        if not self.has_identifier(identifier):
            raise RuntimeError('No such identifier: {}'.format(identifier))
        filename = self.filenames[identifier]
        self.identifiers.pop(filename)
        self.filenames.pop(identifier)
        self.touched_filenames.discard(filename)


    def remove_filename(self, filename):
        if not self.has_filename(filename):
            raise RuntimeError('No such filename: {}'.format(filename))
        identifier = self.identifiers[filename]
        self.identifiers.pop(filename)
        self.filenames.pop(identifier)
        self.touched_filenames.discard(filename)


    def get_identifier(self, filename):
        if not self.has_filename(filename):
            raise RuntimeError('No such filename: {}'.format(filename))
        return self.identifiers[filename]


    def get_filename(self, identifier):
        if not self.has_identifier(identifier):
            raise RuntimeError('No such identifier: {}'.format(identifier))
        return self.filenames[identifier]


    def has_filename(self, filename):
        return filename in self.identifiers.keys()


    def has_identifier(self, identifier):
        return identifier in self.filenames.keys()


    def get_untouched_filenames(self):
        filenames = set(self.filenames.values())
        return filenames.difference(self.touched_filenames)


    def clear_touched_filenames(self):
        self.touched_filenames = set()


    def clear_temporary_filenames(self):
        self.temporary_filenames = set()


class FilesystemOperations:
    def __init__(self):
        self.exists = os.path.exists
        self.mkdir = os.mkdir
        self.rename = os.rename
        self.delete = os.unlink


class Filesystem:
    def __init__(self, dirname, fsops=None):
        self.dirname = dirname
        self.fsops = fsops or FilesystemOperations()
        if not self.fsops.exists(dirname):
            self.fsops.mkdir(dirname)
        self.state = FilesystemState(dirname)


    def add(self, identifier, filename, creator):
        path = os.path.join(self.dirname, filename)
        if self.state.has_identifier(identifier):
            # Identifier already exists. Move file to temporary filename
            if not self.fsops.exists(path):
                # File has been deleted since last run, download again
                self.state.remove_identifier(identifier)
                self.create(identifier, filename, creator)
            else:
                self.move(identifier, filename)
        elif self.state.has_filename(filename):
            # Filename already exists, but not identifier.
            # Give file temporary name and create the new file
            other_identifier = self.state.get_identifier(filename)
            self.move_temporary(other_identifier)
            self.create(identifier, filename, creator)
        else:
            # Neither filename nor identifier exists. Create file
            self.create(identifier, filename, creator)


    def create(self, identifier, filename, creator):
        path = os.path.join(self.dirname, filename)
        self.state.add(identifier, filename)
        try:
            creator(path)
        except Exception as e:
            # File is probably incomplete if exception is raised during creation
            self.state.remove_identifier(identifier)
            self.fsops.delete(path)
            raise e


    def move(self, identifier, new_filename, temporary=False):
        if self.state.has_filename(new_filename):
            other_identifier = self.state.get_identifier(new_filename)
            if identifier == other_identifier:
                self.state.touch(identifier, new_filename)
                return
            else:
                self.move_temporary(other_identifier)
        old_filename = self.state.get_filename(identifier)
        old_path = os.path.join(self.dirname, old_filename)
        new_path = os.path.join(self.dirname, new_filename)
        self.state.remove_identifier(identifier)
        self.state.add(identifier, new_filename, temporary=temporary)
        self.fsops.rename(old_path, new_path)


    def move_temporary(self, identifier):
        temp_filename = str(uuid.uuid4())
        self.move(identifier, temp_filename, temporary=True)


    def finish_sync(self):
        untouched_filenames = self.state.get_untouched_filenames()
        for filename in untouched_filenames:
            path = os.path.join(self.dirname, filename)
            self.state.remove_filename(filename)
            self.fsops.delete(path)
        self.state.clear_touched_filenames()
        for filename in self.state.temporary_filenames:
            path = os.path.join(self.dirname, filename)
            if self.state.has_filename(filename):
                self.state.remove_filename(filename)
            self.fsops.delete(path)
        self.state.clear_temporary_filenames()


    def save(self):
        self.state.clear_touched_filenames()
        for filename in self.state.temporary_filenames:
            path = os.path.join(self.dirname, filename)
            self.state.remove_filename(filename)
            self.fsops.delete(path)
        self.state.clear_temporary_filenames()
        self.state.save()