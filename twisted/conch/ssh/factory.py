# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
A Factory for SSH servers, along with an OpenSSHFactory to use the same
data sources as OpenSSH.

Maintainer: Paul Swartz
"""

from __future__ import absolute_import, division

import random

from functools import cmp_to_key

from twisted.internet import protocol
from twisted.python import log
from twisted.python.compat import cmp

from twisted.conch import error
from twisted.conch.ssh import _kex, transport, userauth, connection



class SSHFactory(protocol.Factory):
    """
    A Factory for SSH servers.

    @ivar services: THe services this factory offers.
    @type services: L{dict} with L{str} keys and
        L{twisted.conch.ssh.service.SSHService} values.
    """
    protocol = transport.SSHServerTransport

    services = {
        'ssh-userauth': userauth.SSHUserAuthServer,
        'ssh-connection': connection.SSHConnection
    }
    def startFactory(self):
        """
        Check for public and private keys.
        """
        if not hasattr(self, 'publicKeys'):
            self.publicKeys = self.getPublicKeys()
        if not hasattr(self, 'privateKeys'):
            self.privateKeys = self.getPrivateKeys()
        if not self.publicKeys or not self.privateKeys:
            raise error.ConchError('no host keys, failing')
        if not hasattr(self, 'primes'):
            self.primes = self.getPrimes()


    def buildProtocol(self, addr):
        """
        Create an instance of the server side of the SSH protocol.

        @type addr: L{twisted.internet.interfaces.IAddress} provider
        @param addr: The address at which the server will listen.

        @rtype: L{twisted.conch.ssh.SSHServerTransport}
        @return: The built transport.
        """
        t = protocol.Factory.buildProtocol(self, addr)
        t.supportedPublicKeys = self.privateKeys.keys()
        if not self.primes:
            log.msg('disabling non-fixed-group key exchange algorithms '
                    'because we cannot find moduli file')
            t.supportedKeyExchanges = [
                kexAlgorithm for kexAlgorithm in t.supportedKeyExchanges
                if _kex.isFixedGroup(kexAlgorithm)]
        return t


    def getPublicKeys(self):
        """
        Called when the factory is started to get the public portions of the
        servers host keys.  Returns a dictionary mapping SSH key types to
        public key strings.

        @rtype: C{dict}
        """
        raise NotImplementedError('getPublicKeys unimplemented')


    def getPrivateKeys(self):
        """
        Called when the factory is started to get the  private portions of the
        servers host keys.  Returns a dictionary mapping SSH key types to
        L{twisted.conch.ssh.keys.Key} objects.

        @rtype: C{dict}
        """
        raise NotImplementedError('getPrivateKeys unimplemented')


    def getPrimes(self):
        """
        Called when the factory is started to get Diffie-Hellman generators and
        primes to use.  Returns a dictionary mapping number of bits to lists
        of tuple of (generator, prime).

        @rtype: C{dict}
        """


    def getDHPrime(self, bits):
        """
        Return a tuple of (g, p) for a Diffe-Hellman process, with p being as
        close to bits bits as possible.

        @type bits: C{int}
        @rtype:     C{tuple}
        """
        primesKeys = list(self.primes.keys())
        primesKeys.sort(key=cmp_to_key(
            lambda x, y: cmp(abs(x - bits), abs(y - bits))))
        realBits = primesKeys[0]
        return random.choice(self.primes[realBits])


    def getService(self, transport, service):
        """
        Return a class to use as a service for the given transport.

        @type transport:    L{transport.SSHServerTransport}
        @type service:      C{str}
        @rtype:             subclass of L{service.SSHService}
        """
        if service == 'ssh-userauth' or hasattr(transport, 'avatar'):
            return self.services[service]
