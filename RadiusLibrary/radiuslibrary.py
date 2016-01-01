"""RobotFramework Radius Module"""
import select
import socket
from pyrad import packet, dictionary, tools
import six
import robot
from robot.libraries.BuiltIn import BuiltIn

#class ClientConnection:
#    def __init__(self,sock,address,port,secret,raddict):
#        self._sock = sock
#        self.address = address
#        self.port = port
#        self.secret = secret
#        self.raddict =  dictionary.Dictionary(raddict)
#        self.close = self._sock.close

class BasePacketAdapter(object):
    def __setitem__(self, key, val):
        return self.packet.__setitem__(key,val)

    def __getattr__(self, attr):
        """Everything else is delegated to the object"""
        return getattr(self.packet, attr)

class AcctPacketAdapter(BasePacketAdapter):
    def __init__(self, **kwargs):
        if 'packet' in kwargs:
            pkt = packet.AcctPacket(secret=kwargs['secret'],dict=kwargs['dict'],packet=kwargs['packet'])
        else:
            pkt = packet.AcctPacket(code=kwargs.get('code',0),secret=kwargs['secret'],dict=kwargs['dict'])

        for key, value in kwargs.items():
            if key in ['code','dict','secret','packet']:
                continue
            else:
                dict_values = kwargs['dict'].attributes[str(key)].values
                value_type = kwargs['dict'].attributes[str(key)].type
                if not isinstance(value,list):
                    print "no instance list {}".format(value)
                    value = [value]
                    print "no instance list {}".format(value)

                for val in value:
                #value_encrypt = kwargs['dict'].attributes[str(key)].encrypt
                    if value_type == 'string' and not dict_values:
                        value = str(value)
                    elif value_type == 'integer' and not dict_values:
                        value = int(value)

                    pkt.AddAttribute(key, val)

        print pkt
        self.packet = pkt

    def __getitem__(self,key):
        #encrypt = self.packet.dict.attributes[key].encrypt
        #value_type = self.packet.dict.attributes[key].type
        print key
        #key = self.packet.dict.attrindex.GetForward(key)
        #if encrypt == 1:
        #    return  [self.packet.PwDecrypt(v) for v in self.packet[key]]
        #elif encrypt == 2 and value_type == 'integer':
        #    return [tools.DecodeInteger(k) for k in self.packet[key]]
        #else:
        #    return self.packet[key]
        return self.packet[str(key)]

class AuthPacketAdapter(BasePacketAdapter):
    "ada"
    def __init__(self, **kwargs):
        if 'packet' in kwargs:
            pkt = packet.AuthPacket(secret=kwargs['secret'],dict=kwargs['dict'],packet=kwargs['packet'])
        else:
            pkt = packet.AuthPacket(code=kwargs.get('code',0),secret=kwargs['secret'],dict=kwargs['dict'])

        for key, value in kwargs.items():
            print key, value
            if key in ['code','dict','secret','packet']:
                continue
            else:
                value_type = kwargs['dict'].attributes[str(key)].type
                value_encrypt = kwargs['dict'].attributes[str(key)].encrypt
                if not isinstance(value,list):
                    print "no instance list {}".format(value)
                    value = [value]
                    print "no instance list {}".format(value)

                for val in value:
                    print "val listitem: {}".format(val)
                    if value_type == 'string':
                        val = str(val)
                    elif value_type == 'integer':
                        val = int(val)

                    if value_encrypt == 1:
                        val = pkt.PwCrypt(val)
                    print "val before adding {}".format(val)
                    print pkt
                    pkt.AddAttribute(str(key), val)
                    print pkt
        self.packet = pkt

    def __getitem__(self,key):
        encrypt = self.packet.dict.attributes[key].encrypt
        value_type = self.packet.dict.attributes[key].type
        key = self.packet.dict.attrindex.GetForward(key)

        if encrypt == 1:
            return  [self.packet.PwDecrypt(v) for v in self.packet[key]]
        elif encrypt == 2 and value_type == 'integer':
            return [tools.DecodeInteger(k) for k in self.packet[key]]
        else:
            print "will retutn {}".format(self.packet[key])
            return self.packet[key]

class RadiusLibrary(object):
    """Main Class"""

    ROBOT_LIBRARY_SCOPE = 'TEST CASE'

    def __init__(self):
        self._client = robot.utils.ConnectionCache('No Clients Created')

        self._server = robot.utils.ConnectionCache('No Servers Created')

        self.builtin = BuiltIn()


    def create_client(self, alias, address, port,
                      secret, raddict='dictionary',
                      authenticator=True):
        """Creates client"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', 0))
        sock.settimeout(3.0)
        sock.setblocking(0)
        request = robot.utils.ConnectionCache('No Client Sessions Created')
        session = {'sock': sock,
                   'address': str(address),
                   'port': int(port),
                   'secret': six.b(str(secret)),
                   'dictionary': dictionary.Dictionary(raddict),
                   'authenticator': authenticator,
                   'request': request}

        self._client.register(session, alias=alias)
        return session

    def create_access_request(self,alias=None):
        client = self._get_session(self._client,alias)
        request = packet.AuthPacket(code=packet.AccessRequest,secret=client['secret'],dict=client['dictionary'])
        client['request'].register(request, str(request.id))
        return request

    def create_accounting_request(self,alias=None):
        client = self._get_session(self._client,alias)
        request = packet.AuthPacket(code=packet.AccountingRequest,secret=client['secret'],dict=client['dictionary'])
        client['request'].register(request, str(request.id))
        return request

    ### Request sesction
    def add_request_attribute(self, key, value, alias=None):
        key = str(key)
        client = self._get_session(self._client,alias)
        request = client['request'].get_connection(alias)
        request.AddAttribute(key,value)

    def send_request(self, alias=None):
        client = self._get_session(self._client,alias)
        request = client['request'].get_connection(alias)
        pdu =  request.RequestPacket()
        client['sock'].sendto(pdu, (client['address'], client['port']))
        return request

    ### Auth request section


    def add_response_attribute(self, key, value, alias=None):
        key = str(key)
        client = self._get_session(self._client,alias)
        request = client['request'].get_connection(alias)
        request.AddAttribute(key,value)

    def send_response(self, alias=None):
        server = self._get_session(self._server, alias)
        request = server['request'].get_connection(alias)
        response = server['response'].get_connection(alias)
        pdu =  response.ReplyPacket()
        server['sock'].sendto(pdu, request.addr)
        return request


    def receive_access_accept(self, alias=None, timeout=1):
        """Receives access accept"""
        client = self._get_session(self._client, alias)
        ready = select.select([client['sock']], [], [], float(timeout))

        pkt = None
        if ready[0]:
            data, addr = client['sock'].recvfrom(1024)

            pkt = AuthPacketAdapter(secret=client['secret'], packet=data,
                                    dict=client['dictionary'])
            client['request'].get_connection(str(pkt.id))

            self.builtin.log(pkt.code)
            if pkt.code != packet.AccessAccept:
                self.builtin.log('Expected {0}, received {1}'.format(packet.AccessRequest, pkt.code))
                raise Exception("received {}".format(pkt.code))
        if pkt is None:
            raise Exception("Did not receive any answer")

        return pkt

    def receive_accounting_response(self, alias=None, timeout=1):
        """Receives access accept"""
        client = self._get_session(self._client, alias)
        ready = select.select([client['sock']], [], [], float(timeout))

        pkt = None
        if ready[0]:
            data, addr = client['sock'].recvfrom(1024)

            pkt = AuthPacketAdapter(secret=client['secret'], packet=data,
                                    dict=client['dictionary'])
            client['request'].get_connection(str(pkt.id))

            self.builtin.log(pkt.code)
            if pkt.code != packet.AccountingResponse:
                self.builtin.log('Expected {0}, received {1}'.format(packet.AccessRequest, pkt.code))
                raise Exception("received {}".format(pkt.code))
        if pkt is None:
            raise Exception("Did not receive any answer")

        return pkt

    def receive_access_reject(self, alias=None, timeout=1):
        """Receives access accept"""
        client = self._get_session(self._client, alias)
        ready = select.select([client['sock']], [], [], float(timeout))

        pkt = None
        if ready[0]:
            data, addr = client['sock'].recvfrom(1024)

            pkt = AuthPacketAdapter(secret=client['secret'], packet=data,
                                    dict=client['dictionary'])
            client['request'].get_connection(str(pkt.id))

            self.builtin.log(pkt.code)
            if pkt.code != packet.AccessAccept:
                self.builtin.log('Expected {0}, received {1}'.format(packet.AccessRequest, pkt.code))
                raise Exception("received {}".format(pkt.code))
        if pkt is None:
            raise Exception("Did not receive any answer")

        return pkt

    def receive_accounting_request(self, alias=None, timeout=1):
        """Receives access request"""
        server = self._get_session(self._server, alias)
        ready = select.select([server['sock']], [], [], float(timeout))

        pkt = None
        if ready[0]:
            data, addr = server['sock'].recvfrom(1024)

            pkt = packet.AcctPacket(secret=server['secret'], packet=data,
                                    dict=server['dictionary'])
            server['request'].register(pkt, str(pkt.id))
            pkt.addr = addr
            self.builtin.log(pkt.code)
            if pkt.code != packet.AccountingRequest:
                self.builtin.log('Expected {0}, received {1}'.format(packet.AccessRequest, pkt.code))
                raise Exception("received {}".format(pkt.code))
        if pkt is None:
            raise Exception("Did not receive any answer")

        return pkt

    def receive_access_request(self, alias=None, timeout=1):
        """Receives access request"""
        server = self._get_session(self._server, alias)
        ready = select.select([server['sock']], [], [], float(timeout))

        pkt = None
        if ready[0]:
            data, addr = server['sock'].recvfrom(1024)

            pkt = AuthPacketAdapter(secret=server['secret'], packet=data,
                                    dict=server['dictionary'])
            server['request'].register(pkt, str(pkt.id))
            pkt.addr = addr
            self.builtin.log(pkt.code)
            if pkt.code != packet.AccessRequest:
                self.builtin.log('Expected {0}, received {1}'.format(packet.AccessRequest, pkt.code))
                raise Exception("received {}".format(pkt.code))
        if pkt is None:
            raise Exception("Did not receive any answer")

        return pkt


    def _get_session(self, cache, alias):
        # Switch to related client alias
        if alias:
            return cache.switch(alias)
        else:
            return cache.get_connection()

    def send_access_request(self, alias=None, **attributes):
        session=self._get_session(self._client,alias)
        print session
        print attributes
        self.builtin.log(attributes)
        pkt = AuthPacketAdapter(code=packet.AccessRequest,
                                secret=session['secret'],
                                dict=session['dictionary'],
                                **attributes)

        session['request'].register(pkt, str(pkt.id))
        pkt.authenticator = pkt.CreateAuthenticator()

        pdu = pkt.RequestPacket()

        session['sock'].sendto(pdu, (session['address'], session['port']))
        return pkt

    def create_accounting_response(self, alias=None):
        """Send Response"""
        session = self._get_session(self._server,alias)
        request = session['request'].get_connection(alias)

        reply = request.CreateReply()
        reply.code = packet.AccountingResponse

        pdu = reply.ReplyPacket()
        session['sock'].sendto(pdu, request.addr)
        session['response'].register(reply,str(reply.code))
        #todo: deregister request
        return reply

    def create_access_accept(self, alias=None):
        """Send Response"""
        session = self._get_session(self._server,alias)
        request = session['request'].get_connection(alias)

        reply = request.CreateReply()
        reply.code = packet.AccessAccept

        pdu = reply.ReplyPacket()
        session['sock'].sendto(pdu, request.addr)
        session['response'].register(reply,str(reply.code))
        #todo: deregister request
        return reply

    def send_accounting_request(self, alias=None, **attributes):
        session=self._get_session(self._client, alias)

        pkt = AcctPacketAdapter(code=packet.AccountingRequest, secret=session['secret'],
                                dict=session['dictionary'], **attributes)

        pkt.authenticator = pkt.CreateAuthenticator()
        pdu = pkt.RequestPacket()

        session['request'].register(pkt, str(pkt.id))
        session['sock'].sendto(pdu, (session['address'], session['port']))

        return pkt

    def send_accounting_response(self, alias=None, **attributes):
        session=self._get_session(self._server, alias)

        pkt = session['request'].get_connection()
        reply_pkt = pkt.CreateReply(**attributes)
        reply_pkt.code = packet.AccountingResponse
        pdu = reply_pkt.ReplyPacket()
        session['sock'].sendto(pdu, pkt.addr)
        return reply_pkt

    def _receive_auth(self,session, code, timeout):
        ready = select.select([session['sock']], [], [], float(timeout))
        pkt = None
        if ready[0]:
            data, addr = session['sock'].recvfrom(1024)

            pkt = AuthPacketAdapter(secret=session['secret'], packet=data,
                                    dict=session['dictionary'])
            session['request'].register(pkt, str(pkt.id))
            pkt.addr = addr
            self.builtin.log(pkt.code)
            if pkt.code != code:
                self.builtin.log('Expected {0}, received {1}'.format(code, pkt.code))
                raise Exception("received {}".format(pkt.code))
        if pkt is None:
            raise Exception("Did not receive any answer")

        return pkt

    def _receive_acct(self,session, code, timeout, **attributes):
        ready = select.select([session['sock']], [], [], float(timeout))
        pkt = None
        if ready[0]:
            data, addr = session['sock'].recvfrom(1024)

            pkt = AcctPacketAdapter(secret=session['secret'], packet=data,
                                    dict=session['dictionary'])
            for key,value in attributes.items():
                if pkt[key] != value:

                    raise BaseException('{} != {}'.format(pkt[key],value))

            session['request'].register(pkt, str(pkt.id))
            pkt.addr = addr
            self.builtin.log(pkt.code)
            if pkt.code != code:
                self.builtin.log('Expected {0}, received {1}'.format(code, pkt.code))
                raise Exception("received {}".format(pkt.code))
        if pkt is None:
            raise Exception("Did not receive any answer")

        return pkt


    #def create_server(self, alias=u'default', address='127.0.0.1', port=0, secret='secret', raddict='dictionary'):
    def create_server(self, alias=None, address='127.0.0.1', port=0, secret='secret', raddict='dictionary'):
        """Creates Radius Server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((address, int(port)))
        #sock.settimeout(3.0)
        sock.setblocking(0)
        request = robot.utils.ConnectionCache('No Server Requests Created')
        response = robot.utils.ConnectionCache('No Server Responses Created')
        server = {'sock': sock,
                  'secret': six.b(str(secret)),
                  'dictionary': dictionary.Dictionary(raddict),
                  'request':request,
                  'response':response}

        self._server.register(server, alias=alias)
        return server

    def destroy_server(self,alias):
        session = self._server.switch(alias)
        session['sock'].close()
        self._server.empty_cache()

    def should_contain_attribute(self, pckt, key=None, val=None):
        """Test if attribute exists"""
        if pckt.dict.attrindex.HasBackward(key):
            numkey = pckt.dict.attrindex.GetBackward(key)
        elif pckt.dict.attrindex.HasForward(key):
            numkey = pckt.dict.attrindex.GetForward(key)
        elif isinstance(key,int):
            numkey = int(key)

        if key and not val:
            return pckt[numkey]

        elif key and val:
            if val in pckt[key.encode('ascii')]:
                return
            else:
                raise BaseException('value "{}" does not contain: {}'.format(pckt[key.encode('ascii')],val))
        else:
            raise BaseException('invalid arguments')
