# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc. All rights reserved.
# Author: Paul Lathrop <paul@simplegeo.com>
#

"""Utility functions for AWS-related tasks."""

from getpass import getpass

import boto.pyami.config as boto_config


def get_credentials(batch=False):
    """Return a tuple (key, secret) of AWS credentials. Credentials
    are loaded via boto first (which checks the environment and a
    couple well-known files). If boto cannot find any credentials, and
    the 'batch' kwarg is set to False, this method will request
    credentials from the user interactively via the console."""
    config = boto_config.Config()
    key = config.get('Credentials', 'aws_access_key_id', False)
    secret = config.get('Credentials', 'aws_secret_access_key', False)
    if key and secret:
        return (key, secret)
    if batch:
        return None
    return prompt_for_credentials()


def prompt_for_credentials():
    """Prompt the user to enter their AWS credentials, and return them
    as a tuple of (key, secret)."""
    print 'Could not load AWS credentials from environment or boto configuration.'
    print 'Please enter your AWS credentials.'
    print
    key = raw_input('AWS Access Key ID: ')
    secret = getpass('AWS Secret Access Key: ')
    return (key, secret)
