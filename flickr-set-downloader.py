# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import math
import os
import pickle
import urllib
import requests
import configparser
import argparse
import logging

import flickrapi

import filesystem

FORMAT = '%(asctime)-15s - %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('flickr-set-downloader')


def first_line(string):
    return string.split(os.linesep)[0]


# The flickr API can be a bit flaky at times. We use this decorator to retry
# API calls that fail a few times. Usually it's enough to try once more for each call.
def retry(ExceptionsToCheck, tries=4):
    def real_decorator(func):
        def f_retry(*args, **kwargs):
            mtries = tries
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except ExceptionsToCheck as e:
                    mtries -= 1
                    msg = "{} failed with '{}', retrying... ({} attempts left)"             \
                          .format(func.__name__, first_line(str(e)), mtries)
                    print(msg)
            return func(*args, **kwargs)
        return f_retry
    return real_decorator


# Network exceptions could be worth retrying
NETWORK_EXCEPTIONS = (requests.exceptions.BaseHTTPError,
                      requests.exceptions.ConnectionError,
                      flickrapi.exceptions.FlickrError,
                      urllib.error.HTTPError)


class AlbumDownloadSpec:
    def __init__(self, name, identifier):
        self.name = name
        self.identifier = identifier
        self.photos = []


class PhotoDownloadSpec:
    def __init__(self, flickr, name, identifier, filetype):
        self._flickr = flickr
        self.name = name
        self.identifier = identifier
        self.filetype = filetype


    @retry(NETWORK_EXCEPTIONS)
    def get_url(self):
        sizes = self._flickr.photos.getSizes(photo_id = self.identifier)
        return sizes.findall('.//size[@label="Original"]')[0].get('source')


def get_file_id(photoset_id, photo_id):
    return '{}-{}'.format(photoset_id, photo_id)


def get_photo_filename(photo_name, filetype, idx, num_photos, photoset_title):
    width = math.floor(math.log10(num_photos)) + 2
    filename = '{idx:0{width}d} - {photo_name}.{suffix}'                                        \
                .format(idx = idx, photo_name = photo_name, suffix = filetype, width = width)
    return os.path.join(photoset_title, filename)


def get_download_spec(config):
    flickr = flickrapi.FlickrAPI(config['api_key'], config['api_secret'],
                                 username = config['username'])
    download_spec = []
    for photoset in flickr.walk_photosets():
        download_spec.append(get_album_spec(flickr, photoset))

    return download_spec

@retry(NETWORK_EXCEPTIONS)
def get_album_spec(flickr, photoset):
    photoset_id = photoset.get('id')
    photoset_title = photoset.find('title').text.strip()
    primary_photo = photoset.get('primary')

    album_spec = AlbumDownloadSpec(photoset_title, photoset_id)
    print("Scanning photoset: {}".format(photoset_title))
    logger.debug("album identifier is {}".format(photoset_id))
    for photo in flickr.walk_set(photoset_id):
        album_spec.photos.append(get_photo_spec(flickr, photo))
    return album_spec


@retry(NETWORK_EXCEPTIONS)
def get_photo_spec(flickr, photo):
    photo_id = photo.get('id')
    photo_name = photo.get('title')
    logger.debug("Found photo: {} - {}".format(photo_id, photo_name))
    photo_info = flickr.photos.getInfo(photo_id = photo_id).getchildren()[0]
    filetype = photo_info.get('originalformat')
    return PhotoDownloadSpec(flickr, photo_name, photo_id, filetype)


def download(working_directory, config):
    download_spec = get_download_spec(config)
    fs = filesystem.Filesystem(working_directory)
    try:
        for album in download_spec:
            dirname = os.path.join(working_directory, album.name)
            if not os.path.exists(dirname):
                print ("Making directory {}".format(dirname))
                os.mkdir(dirname)

            num_photos = len(album.photos)
            for idx, photo in enumerate(album.photos, 1):
                filename = get_photo_filename(photo.name, photo.filetype, idx, num_photos, album.name)
                file_identifier = get_file_id(album.identifier, photo.identifier)

                @retry(NETWORK_EXCEPTIONS)
                def download(url, path):
                    urllib.request.urlretrieve(url, path)

                def creator(path, try_num=0):
                    print(" -- Downloading {}".format(path))
                    download(photo.get_url(), path)
                fs.add(file_identifier, filename, creator)
        fs.finish_sync()
    except KeyboardInterrupt:
        pass
    finally:
        print('Saving filesystem state')
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
    parser.add_argument('--debug', action='store_true',
                        help='Enable debugging output')
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
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Logger level set to debug")
    config = parse_configuration(args.working_directory)
    download(args.working_directory, config)


if __name__ == '__main__':
    main()