# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc. All rights reserved.
# Author: Paul Lathrop <paul@simplegeo.com>
#

"""Module for utility classes/functions."""

import types

from clusto.drivers.base.driver import Driver


class SGException(Exception):
    pass


def get_names(names_or_entities, exception_type=SGException, message=None):
    """Given a thing (or list of things) which are either stringlike
    or are clusto entities, return a list of strings representing the
    names of those things."""
    def _transform(thing):
        if isinstance(thing, types.StringTypes):
            return thing
        elif isinstance(thing, Driver):
            return thing.name
        else:
            raise exception_type(message) if message else exception_type()
    if not isinstance(names_or_entities, list):
        names_or_entities = [names_or_entities]
    return filter(None, map(_transform, names_or_entities))
