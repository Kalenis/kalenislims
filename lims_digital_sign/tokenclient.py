# -*- coding: utf-8 -*-
# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import json
import xmlrpc.client


class EchoClient():

    def __init__(self, listen, origin, target):
        self.listen = listen
        self.origin = origin
        self.target = target
        self.server = self._get_server(self.listen)

    def _get_server(self, listen):
        host, port = listen.split(':')
        return xmlrpc.client.Server('http://%s:%s/' % (host, port))

    def signDoc(self):
        data = json.dumps({
            'origin': self.origin,
            'target': self.target,
            })
        self.server.signDoc(data)


class GetToken():

    def __init__(self, listen, origin, target):
        self.listen = listen
        self.origin = origin
        self.target = target

    def signDoc(self, main=False):
        client = EchoClient(self.listen, self.origin, self.target)
        client.signDoc()
        return True
