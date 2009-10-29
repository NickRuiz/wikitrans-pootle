#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008 Zuza Software Foundation
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

"""Some code helpers."""


def lazy(result_name):
    """This is used to create an attribute whose value is
    lazily computed. The parameter names an object variable that
    will be used to hold the lazily computed value. At the start,
    this variable should hold the value undefined.

    TODO: Replace this with a nice Python descriptor.

    class Person(object):
        def __init__(self):
            self.name = 'John'
            self.surname = 'Doe'

        @lazy('_fullname')
        def _get_fullname(self):
            return self.name + ' ' + self.surname
    """

    def lazify(f):
        def evaluator(self):
            try:
                return getattr(self, result_name)
            except AttributeError:
                result = f(self)
                setattr(self, result_name, result)
                return result
        return evaluator
    return lazify

def lazy_property(name, getter):
    def deleter(self):
        delattr(self, name)

    return property(lazy(name)(getter), None, deleter)


from django.db import models
class RelatedManager(models.Manager):
    """Model manager that always does full joins on relations, saves
    us lots of database queries later"""
    def get_query_set(self):
        return super(RelatedManager, self).get_query_set().select_related(depth=1)
