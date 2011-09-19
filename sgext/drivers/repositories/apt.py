# -*- coding: utf-8 -*-
#
# © 2011 Paul D. Lathrop
# Author: Paul Lathrop <paul@tertiusfamily.net>
#

"""
Manage the apt family of package repositories using the repoman
API.
"""
import repoman.client as repo

from sgext.drivers import Repository


class Apt(Repository):
    """
    Driver for modeling and controlling apt repositories via the
    repoman API.
    """
    _driver_name = 'apt_repository'

    def __init__(self, name, url, **kwargs):
        Repository.__init__(self, name, **kwargs)
        self.set_attr(key='repository', subkey='url', value=url)

    @property
    def url(self):
        """
        Return the repository url.
        """
        return self.attr_value(key='repository', subkey='url')

    @property
    def dists(self):
        """
        Return a sorted list of dists in this repository.
        """
        return sorted(repo.request(''))

    def packages(self, dist):
        """
        Return a sorted list of packages in the given dist.
        """
        if dist not in self.dists:
            raise DistError('No such dist: %s' % dist, dist)
        return sorted(repo.request(dist))

    def package_versions(self, dist):
        """
        Return a list of (package, version) tuples for the packages in
        the given dist.
        """
        if dist not in self.dists:
            raise DistError('No such dist: %s' % dist, dist)
        return sorted([(p, self.package(p, dist)['Version'])
                       for p in self.packages(dist)])

    def package(self, pkg, dist):
        """
        Return the metadata for the given package in the given dist.
        """
        if dist not in self.dists:
            raise DistError('No such dist: %s' % dist, dist)
        result = repo.request('%s/%s' % (dist, pkg))
        if len(result) == 0:
            raise PackageError('No such package: %s in dist: %s' % (pkg, dist),
                               dist, pkg)
        return result

    def package_version(self, pkg, dist):
        """
        Return the version of the given package in the given dist.
        """
        return self.package(pkg, dist)['Version']

    def promote(self, pkg, src_dist, dst_dist, version=None):
        """
        Copy the specified version of the given package from the
        source dist to the destination dist. If version is None, just
        copy whatever is present in the source dist.
        """
        if src_dist not in self.dists:
            raise DistError('No such source dist: %s' % src_dist, src_dist)
        if dst_dist not in self.dists:
            raise DistError('No such destination dist: %s' % dst_dist,
                            dst_dist)
        # If no version is specified, use whatever version is in the
        # source dist.
        if version is None:
            version = self.package_version(pkg, src_dist)
        # If the requested version does not exist in the source dist,
        # it's a problem.
        if version != self.package_version(pkg, src_dist):
            raise PackageError('Version %s of package %s not found '
                               'in dist %s' % (version, pkg, src_dist),
                               src_dist, pkg)
        # If the requested version matches what is in the destination
        # dist, we're done!
        if version == self.package_version(pkg, dst_dist):
            return self.package(pkg, dst_dist)
        # Oh damn, we got this far, we have to actually do
        # something.
        repo.request('%s/%s/copy?dstdist=%s' % (src_dist, pkg, dst_dist),
                     method='POST')
        # We've promoted, so the version in the destination dist
        # should be correct. If not, complain loudly!
        if version != self.package_version(pkg, dst_dist):
            raise PackageError('Failed to promote %s to version %s '
                               'in dist %s' % (pkg, version, dst_dist),
                               dst_dist, pkg)


class RepoError(Exception):
    """
    Base class for repository errors.
    """
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

    def __str__(self):
        return repr(self.message)


class DistError(RepoError):
    """
    Errors related to dists.
    """
    def __init__(self, message, dist):
        RepoError.__init__(self, message)
        self.dist = dist


class PackageError(DistError):
    """
    Errors relating to packages.
    """
    def __init__(self, message, dist, package):
        DistError.__init__(self, message, dist)
        self.package = package
