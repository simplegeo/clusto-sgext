# -*- coding: utf-8 -*-
#
# © 2011 Paul D. Lathrop
# Author: Paul Lathrop <paul@tertiusfamily.net>
#

"""Module for managing a repository of things."""

from clusto.drivers.base import Driver


class Repository(Driver):
    """
    A Repository is a collection of logical things (as opposed to
    physical things).
    """

    _clustotype = 'repository'
    _driver_name = 'repository'

