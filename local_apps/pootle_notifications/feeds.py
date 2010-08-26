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

from django.core.exceptions import PermissionDenied
from django.contrib.syndication.feeds import Feed
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from pootle_misc.baseurl import l
from pootle_app.models import Directory
from pootle_app.models.permissions import get_matching_permissions, check_permission
from pootle_profile.models import get_profile

from pootle_notifications.models import Notice
from pootle_notifications.views import directory_to_title

def view(request, path):
    pootle_path = '/%s' % path
    directory = get_object_or_404(Directory, pootle_path=pootle_path)

    request.permissions = get_matching_permissions(get_profile(request.user), directory)
    if not check_permission('view', request):
        raise PermissionDenied

    feedgen = NoticeFeed(pootle_path, request, directory).get_feed(path)
    response = HttpResponse(mimetype=feedgen.mime_type)
    feedgen.write(response, 'utf-8')
    return response

class NoticeFeed(Feed):
    title_template = "notice_title.html"
    description_template = "notice_body.html"
    def __init__(self, slug, request, directory):
        self.link = l(directory.pootle_path)
        self.directory = directory
        self.recusrive = request.GET.get('all', False)
        super(NoticeFeed, self).__init__(slug, request)

    def get_object(self, bits):
        return self.directory

    def title(self, directory):
        return directory_to_title(self.request, directory)

    def items(self, directory):
        if self.recusrive:
            return Notice.objects.filter(directory__pootle_path__startswith=directory.pootle_path).select_related('directory')[:30]
        else:
            return Notice.objects.filter(directory=directory).select_related('directory')[:30]

    def item_pubdate(self, item):
        return item.added
