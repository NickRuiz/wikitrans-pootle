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

from django.conf import settings

from pootle.__version__ import sver

def pootle_context(request):
    """exposes settings to templates"""
    #FIXME: maybe we should expose relevant settings only?
    context = {
        'settings': {
            'TITLE': settings.TITLE,
            'DESCRIPTION': settings.DESCRIPTION,
            'CAN_REGISTER': settings.CAN_REGISTER,
            'CAN_CONTACT': settings.CAN_CONTACT and settings.CONTACT_EMAIL,
            'SCRIPT_NAME': settings.SCRIPT_NAME,
            'MEDIA_URL': settings.MEDIA_URL,
            'POOTLE_VERSION': sver,
            'CACHE_TIMEOUT': settings.CACHE_MIDDLEWARE_SECONDS,
        },
    }
    return context
