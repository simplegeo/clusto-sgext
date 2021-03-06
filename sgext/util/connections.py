# -*- coding: utf-8 -*-
#
# © 2011 SimpleGeo, Inc All rights reserved.
# Author: Ian Eure <ian@simplegeo.com>
#

"""Generic connection-handling code."""

import time
import socket
from functools import wraps
from contextlib import contextmanager
from collections import defaultdict
from operator import itemgetter

from decorator import decorator
from ostrich import stats


class throttle(object):

    """Throttle calls to a method by `factor'."""

    def __init__(self, factor, error_only=False):
        self.factor = factor
        self.error_only = error_only
        self.start_time = None

    def __enter__(self):
        """Enter the nested context."""
        self.start_time = time.time()

    def __exit__(self, type, value, traceback):
        """Exit the nested context."""
        if not self.error_only or (self.error_only and type):
            time.sleep(self.factor * (time.time() - self.start_time))
        return False

    def __call__(self, function):
        """Act as a decorator."""
        @wraps(function)
        def __inner__(*args, **kwargs):
            with self:
                return function(*args, **kwargs)

        return __inner__


def retry(max_=3, delay=0, exceptions=None):
    """Retry some number of times.

    WARNING: This decorator assumes the wrapped function is
    idempotent; that is, that it will perform the same operation when
    called multiple times, and that it does not mutate its arguments
    in such a way that this may be the case. Do not pass generators,
    iterators, or other lazy structures to functions wrapped by this,
    as failed segments will not be retried. Instead, create an outer
    loop which materializes segments into lists or tuples, and pass
    those.
    """
    exceptions = exceptions or (socket.error, socket.timeout)

    @decorator
    def __wrapper__(func, *args, **kwargs):
        attempts = 1
        while True:
            try:
                return func(*args, **kwargs)
            except exceptions, ex:
                stats.incr('%s_retry' % str(func))
                logging.warning("Caught %s on %s attempt %d/%d",
                              repr(ex), str(func), attempts, max_)
                time.sleep(delay)
                if max_ != -1 and attempts < max_:
                    attempts += 1
                    continue

                logging.exception("Retries of %s exceeded, giving up.",
                                  str(func))
                stats.incr('%s_retry_failure' % str(func))
                raise

    return __wrapper__


def backoff(limit=600, recent=10, exceptions=None):
    """Back off (delay) when errors occur.

    When the decorated function raises an exception listed in
    exceptions, this decorator will delay for an exponentially
    increasing amount of time, up to limit seconds. As the error rate
    drops, so does the delay. The original exception is raised after
    the delay.
    """
    exceptions = exceptions or (socket.error, socket.timeout)

    results = []

    def __delay__(duration, error=None):
        """Return the current delay."""
        results.append((duration, error))
        while len(results) > recent:
            results.pop(0)
        failures = len(filter(itemgetter(1), results))

        if failures:
            delay = min(pow(results[-1][0], failures), limit)
            # print "min(pow(%.2f, %d), %d) -> %.2f" % (
            #     results[-1][0], failures, limit, delay)
            # print " (%d/%d failures)-> Delaying for %.2fs" % (
            #     failures, len(results), delay)

        else:
            delay = 0

        return delay

    @decorator
    def __wrapper__(func, *args, **kwargs):
        start = time.time()
        try:
            retval = func(*args, **kwargs)
            time.sleep(__delay__(time.time() - start))
            return retval
        except exceptions, ex:
            time.sleep(__delay__(time.time() - start, ex))
            raise

    return __wrapper__


def ratelimit(sequence, ns):
    """Rate-limit consumption of sequence to n per second."""
    avg = 0
    for (n, elt) in enumerate(sequence, 1):
        start = time.time()
        yield elt
        avg = (avg * (n - 1) + (time.time() - start)) / n
        sleep = (1 - avg * ns) / ns
        if sleep > 0:
            time.sleep(sleep)


class failure_stats(object):

    """Record success/failure stats."""

    def __init__(self, name=None, stats_obj=None):
        self.name = '%s_' % name if name else ''
        self.stats = stats_obj or stats

    def __enter__(self):
        """Enter the nested context."""
        self.stats.incr('%scalls' % self.name)

    def __exit__(self, type, value, traceback):
        """Exit the nested context."""

        if type:
            self.stats.incr('%serrors' % self.name)
            self.stats.incr('%stypes_%s' % (self.name, type.__name__))
        else:
            self.stats.incr('%ssuccesses' % self.name)

        return False

    def __call__(self, function):
        """Act as a decorator."""
        @wraps(function)
        def __inner__(*args, **kwargs):
            with self:
                return function(*args, **kwargs)

        return __inner__


def make_suppress(exceptions, interval, threshold):
    """Return a context manager which manages exceptions."""

    __BUCKET_ERRORS = []

    def threshold_suppress():
        """Suppress errors as long as they stay below a threshold."""
        try:
            yield
        except exceptions, ex:
            ts = int(time.time())
            timebucket = ts - (ts % interval)
            if __BUCKET_ERRORS:
                (lastbucket, errors) = __BUCKET_ERRORS[0]
            else:
                lastbucket = None

            if lastbucket != timebucket:
                errors = defaultdict(int)
                __BUCKET_ERRORS.insert(0, (timebucket, errors))
                while len(__BUCKET_ERRORS) > 1:
                    __BUCKET_ERRORS.pop()

            errors[type(ex)] += 1
            if errors[type(ex)] < threshold:
                stats.incr('%s_suppressed' % type(ex).__name__)
                logging.exception("Suppressing error: %s", ex)
                return
            logging.debug("Too many %s errors, raising", type(ex))
            stats.incr('%s_suppress_failures' % type(ex).__name__)
            raise

    return contextmanager(threshold_suppress)
