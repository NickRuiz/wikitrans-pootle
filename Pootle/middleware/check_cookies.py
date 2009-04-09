#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
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

class CheckCookieMiddleware(object):
    def process_request(self, request):
        # If the user is logged in, then we know for sure that she had
        # cookies enabled.
        #
        # If she's not logged in, then we set a test cookie with each
        # request which is used by the login system to determine if she
        # has cookies enabled.
        if not request.user.is_authenticated():
            request.session.set_test_cookie()
