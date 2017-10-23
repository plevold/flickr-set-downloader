# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import math
import os
import pickle
import urllib
import configparser
import argparse

import filesystem

def get_photos(flickr, photoset_id):
    return [photo for photo in flickr.walk_set(photoset_id)]


def get_photo_url(flickr, photo_id):
    sizes = flickr.photos.getSizes(photo_id = photo_id)
    return sizes.findall('.//size[@label="Original"]')[0].get('source')


def get_file_id(photoset_id, photo_id):
    return '{}-{}'.format(photoset_id, photo_id)


def get_photo_filename(photo, photo_url, idx, num_photos, photoset_title):
    width = math.floor(math.log10(num_photos)) + 2
    title = photo.get('title')
    suffix = os.path.splitext(photo_url.split('/')[-1])[-1].replace('.', '')
    filename = '{idx:0{width}d} - {title}.{suffix}'.format(idx = idx, title = title, suffix = suffix, width = width)
    return os.path.join(photoset_title, filename)


def download(working_directory, config):
    # Import flickrapi when we need it so that help text may be shown without installing dependencies
    import flickrapi
    flickr = flickrapi.FlickrAPI(config['api_key'], config['api_secret'],
                                 username = config['username'])
    fs = filesystem.Filesystem(working_directory)
    try:
        for photoset in flickr.walk_photosets():
            photoset_id = photoset.get('id')
            photoset_title = photoset.find('title').text.strip()
            primary_photo = photoset.get('primary')

            print("Scanning photoset: {}".format(photoset_title))
            if not os.path.exists(photoset_title):
                print (" -- Making directory {}".format(photoset_title))
                os.mkdir(photoset_title)

            photos = get_photos(flickr, photoset_id)
            num_photos = len(photos)
            for idx, photo in enumerate(photos, 1):
                photo_id = photo.get('id')
                photo_url = get_photo_url(flickr, photo_id)
                filename = get_photo_filename(photo, photo_url, idx, num_photos, photoset_title)

                def creator(path):
                    print(" -- Downloading {}".format(path))
                    urllib.request.urlretrieve(photo_url, path)
                identifier = get_file_id(photoset_id, photo_id)
                fs.add(identifier, filename, creator)
    except KeyboardInterrupt:
        pass
    fs.finish_sync()
    fs.save()

# Based on https://stackoverflow.com/a/11415816/265249
class writable_dir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir = values
        if not os.path.isdir(prospective_dir):
            raise argparse.ArgumentTypeError("{} is not a valid directory".format(prospective_dir))
        if os.access(prospective_dir, os.W_OK):
            setattr(namespace, self.dest, prospective_dir)
        else:
            raise argparse.ArgumentTypeError("{} is not a readable directory".format(prospective_dir))


def parse_arguments():
    helptext = \
'''Flickr Photoset Backup and Downloader
=====================================

The script will maintain a folder with all you flickr photosets as subfolders,
which can be useful if you wish to backup the data you add to flickr.
Files will be named so that they sort the same way as you have organized your
files in the photoset.
If you run the script multiple times in the same folder only new files will
be downloaded.

Requirements
------------

This script requires the flickr API Python library. Install it by running

pip install flickrapi

Configuration
-------------

The script requires a config file named flickr-downloader.config in the
assigned working directory. Example contents:
[flickr]
usename: your-username-here
api_key: your-api-key-here
api_secret: your-api-secret-here

You can generate an API key here: https://www.flickr.com/services/apps/create/apply/
'''
    parser = argparse.ArgumentParser(description=helptext, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('working_directory', type=str, action=writable_dir,
                        help='Path to folder where photos should be stored')
    return parser.parse_args()


def parse_configuration(working_directory):
    config = configparser.ConfigParser()
    config.read(os.path.join(working_directory, 'flickr-downloader.config'))
    try:
        username = config.get('flickr', 'username')
        api_key = config.get('flickr', 'api_key')
        api_secret = config.get('flickr', 'api_secret')
    except configparser.NoOptionError as e:
        print('Error while reading config file: {}'.format(e.message))
        print('')
        print('For help, please see the readme file or execute script with --help argument')
    return {'username': username, 'api_key': api_key, 'api_secret': api_secret}


def main():
    args = parse_arguments()
    config = parse_configuration(args.working_directory)
    download(args.working_directory, config)


if __name__ == '__main__':
    main()