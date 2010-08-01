#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Pootle.
#
# Pootle is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Pootle is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pootle; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from django import forms
try:
    from django.core.validators import EMPTY_VALUES
except ImportError:
    from django.forms.fields import EMPTY_VALUES


class GroupedModelChoiceField(forms.ModelChoiceField):
    def __init__(self, querysets, *args, **kwargs):
        super(GroupedModelChoiceField, self).__init__(*args, **kwargs)
        self.querysets = querysets

    def _get_choices(self):
        orig_queryset = self.queryset
        orig_empty_label = self.empty_label
        if self.empty_label is not None:
            yield (u"", self.empty_label)
            self.empty_label = None

        for title, queryset in self.querysets:
            self.queryset = queryset
            if title is None:
                for choice in super(GroupedModelChoiceField, self).choices:
                    yield choice
            else:
                yield (title, [choice for choice in super(GroupedModelChoiceField, self).choices])

        self.queryset = orig_queryset
        self.empty_label = orig_empty_label
    choices = property(_get_choices, forms.ModelChoiceField._set_choices)


class LiberalModelChoiceField(forms.ModelChoiceField):
    """
    a ModelChoiceField that doesn't complain about choices not present in the queryset.

    this is essentially a hack for admin pages. to be able to exclude
    currently used choices from dropdowns without failing validation.
    """

    def clean(self, value):
        if value in EMPTY_VALUES:
            return None
        try:
            key = self.to_field_name or 'pk'
            value = self.queryset.model.objects.get(**{key: value})
        except self.queryset.model.DoesNotExist:
            raise forms.ValidationError(self.error_messages['invalid_choice'])
        return value
