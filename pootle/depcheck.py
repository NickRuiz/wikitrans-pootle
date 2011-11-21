#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Pootle.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import subprocess
import sys
import os

from django.conf import settings


##########################
# test core dependencies #
##########################
def test_translate():
    try:
        from translate.__version__ import ver, sver
        if ver >= (1, 8, 0):
            return True, sver
        else:
            return False, sver
    except ImportError:
        return None, None

def test_sqlite():
    try:
        #TODO: work out if we need certain versions
        try:
            from sqlite3 import dbapi2
        except ImportError:
            from pysqlite2 import dbapi2
        return True
    except ImportError:
        return False

def test_django():
    from django import VERSION, get_version
    if VERSION >= (1, 2, 0):
        return True, get_version()
    else:
        return False, get_version()

##############################
# test optional dependencies #
##############################

def test_unzip():
    """test for unzip command"""
    try:
        subprocess.call('unzip', stdout=file(os.devnull), stderr=file(os.devnull))
        return True
    except:
        return False

def test_iso_codes():
    import gettext
    languages = (lang[0] for lang in settings.LANGUAGES)
    if not languages:
        # There are no UI languages, which is a problem, but we won't complain
        # about that here.
        languages = ['af', 'ar', 'fr']
    return len(gettext.find('iso_639', languages=languages, all=True)) > 0


def test_lxml():
    try:
        from lxml.etree import LXML_VERSION, __version__
        if LXML_VERSION >= (2, 1, 4, 0):
            return True, __version__
        else:
            return False, __version__
    except ImportError:
        return None, None

def test_levenshtein():
    try:
        import Levenshtein
        return True
    except ImportError:
        return False

def test_indexer():
    from translate.search.indexing import _get_available_indexers
    return [indexer.__module__.split('.')[-1] for indexer in _get_available_indexers()]

def test_gaupol():
    try:
        import aeidon
        return True
    except ImportError:
        try:
            import gaupol
            return True
        except ImportError:
            pass
        return False

######################
# test optimal setup #
######################
def test_mysqldb():
    try:
        import MySQLdb
        return True
    except ImportError:
        return False


def test_db():
    """test that we are not using sqlite3 as the django database"""
    return settings.DATABASE_ENGINE != 'sqlite3'

def test_cache():
    """test if cache backend is memcached"""
    #FIXME: maybe we shouldn't complain if cache is set to db or file?
    return settings.CACHE_BACKEND.startswith('memcached')

def test_memcache():
    try:
        import memcache
        return True
    except ImportError:
        return False

def test_memcached():
    """test if we can connect to memcache server"""
    from django.core.cache import cache
    return cache._cache.servers[0].connect()

def test_cached_db_session():
    """test that cached_db session is available"""
    try:
        import django.contrib.sessions.backends.cached_db
        return True
    except ImportError:
        return False

def test_session():
    """test that session backend is set to memcahce"""
    return settings.SESSION_ENGINE.split('.')[-1] in ('cache', 'cached_db')

def test_debug():
    return not settings.DEBUG

def test_webserver():
    """test that webserver is apache"""
    return 'apache' in sys.modules or '_apache' in sys.modules or 'mod_wsgi' in sys.modules

def test_livetranslation():
    return not settings.LIVE_TRANSLATION

def test_from_email():
    return bool(settings.DEFAULT_FROM_EMAIL)

def test_contact_email():
    return bool(settings.CONTACT_EMAIL)
