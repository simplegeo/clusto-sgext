# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc. All rights reserved.
# Author: Paul Lathrop <paul@simplegeo.com>
#

"""Utility functions for AWS-related tasks."""

from getpass import getpass
import os

import boto.pyami.config as boto_config


def has_aws_environment():
    """
    Return True if the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
    environment variables are both set.
    """
    key = os.environ.has_key('AWS_ACCESS_KEY_ID')
    secret = os.environ.has_key('AWS_SECRET_ACCESS_KEY')
    return key and secret


def credentials_from_boto():
    config = boto_config.Config()
    key = config.get('Credentials', 'aws_access_key_id', False)
    secret = config.get('Credentials', 'aws_secret_access_key', False)
    return (key, secret)


def get_credentials(batch=False):
    """
    Return a dictionary of AWS credentials.

    Credentials are loaded from the AWS_ACCESS_KEY_ID and
    AWS_SECRET_ACCESS_KEY environment variables first. If these
    variables are not set, then the boto configuration is checked. If
    boto cannot find any credentials, and the 'batch' kwarg is set to
    False, this method will request credentials from the user
    interactively via the console.
    """
    if has_aws_environment():
        return {'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
                'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY']}
    key, secret = credentials_from_boto()
    if key and secret:
        return {'aws_access_key_id': key,
                'aws_secret_access_key': secret}
    if batch:
        return None
    return prompt_for_credentials()


def prompt_for_credentials():
    """
    Prompt the user to enter their AWS credentials, and return them
    as a dictionary.
    """
    print 'Could not load AWS credentials from environment or boto configuration.'
    print 'Please enter your AWS credentials.'
    print
    key = raw_input('AWS Access Key ID: ')
    secret = getpass('AWS Secret Access Key: ')
    return {'aws_access_key_id': key,
            'aws_secret_access_key': secret}
