Flickr Photoset Backup and Downloader
=====================================

Introduction
------------

Hosted photo services are great, but don't rely soley on them for your precious photos - keep a local backup!

The script will maintain a folder with all you flickr photosets as subfolders,
which can be useful if you wish to backup the data you add to flickr.
Files will be named so that they sort the same way as you have organized your
files in the photoset.
If you run the script multiple times in the same folder only new files will
be downloaded.


Requirements
------------

This script requires Python 3 to run.
The flickr API Python library must also be installed.
You can install it by running

```
pip install flickrapi
```


Configuration
-------------

The script requires a config file named `flickr-downloader.config` in the assigned working directory.
Example contents:

```
[flickr]
usename: your-username-here
api_key: your-api-key-here
api_secret: your-api-secret-here
```

You can generate an API key here: https://www.flickr.com/services/apps/create/apply/


Running
-------

To run the script, simply type the command

```
python flickr-set-downloader.py path/to/folder/where/photos/should/be/stored
```


Contact
-------

Feel free to post questions, feedback and contributions on the GitHub page:


License
-------

This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
If a copy of the MPL was not distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.