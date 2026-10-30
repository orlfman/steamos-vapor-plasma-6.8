#!/usr/bin/env python3
"""Test-only GTK 4 Broadway transport client, verified against GTK 4.24.1.

Connects only to the runner's private Unix socket. Acknowledges surface/frame
messages so native widgets can finish layout/animation ticks without a browser.
Does not render a browser image or send keyboard/mouse/application actions.
Unknown protocol operations fail explicitly. No third-party dependencies.
"""
import base64
import hashlib
import os
import socket
import struct
import threading


class FrameClient:
    def __init__(self, path, scale=1):
        self.path = str(path)
        self.scale = scale
        self.socket = None
        self.thread = None
        self.stopping = False
        self.errors = []
        self.surfaces = {}
        self.serial = 0
        self.frames = 0

    def receive(self, size):
        result = bytearray()
        while len(result) < size:
            block = self.socket.recv(size-len(result))
            if not block:
                raise EOFError('Private display closed')
            result.extend(block)
        return bytes(result)

    def send_frame(self, payload, opcode=2):
        length = len(payload)
        header = bytes([0x80|opcode])
        if length < 126:header += bytes([0x80|length])
        elif length < 65536:header += bytes([0xfe])+struct.pack('!H',length)
        else:header += bytes([0xff])+struct.pack('!Q',length)
        mask = os.urandom(4)
        self.socket.sendall(header+mask+bytes(v^mask[i%4] for i,v in enumerate(payload)))

    def event(self, operation, *arguments):
        # Upstream broadway.js leaves lastTimeStamp at zero until a real input
        # event; this client emits transport replies only, not user input.
        stamp = 0
        values = (operation,self.serial,stamp,*arguments)
        self.send_frame(struct.pack('!'+'I'*len(values),*(v & 0xffffffff for v in values)))

    def configure(self, ident):
        self.event(11,ident,*self.surfaces[ident])

    def commands(self, payload):
        position = 0
        def read(fmt):
            nonlocal position
            values = struct.unpack_from('<'+fmt,payload,position)
            position += struct.calcsize('<'+fmt)
            return values[0] if len(values)==1 else values
        while position < len(payload):
            operation=read('B');self.serial=read('I')
            if operation==2:
                ident,x,y,width,height=read('HhhHH')
                self.surfaces[ident]=[x,y,width,height];self.configure(ident)
            elif operation in (3,4,5,6,7):
                ident=read('H')
                if operation==7:self.surfaces.pop(ident,None)
            elif operation==8:
                ident=read('H');flags=read('B')
                surface=self.surfaces[ident]
                if flags & 1:surface[:2]=read('hh')
                if flags & 2:surface[2:]=read('HH')
                self.configure(ident)
            elif operation==9:read('HH')
            elif operation==10:return
            elif operation==12:read('H')
            elif operation==13:
                read('I');size=read('I');position += size
            elif operation==14:read('I')
            elif operation==15:
                read('H');size=read('I');position += size*4
            elif operation==16:
                ident=read('H');tag=read('I');self.event(14,ident,tag);self.frames += 1
            elif operation==0:
                read('HB');self.event(9)
            elif operation==1:self.event(10)
            else:raise ValueError(f'Unsupported Broadway operation {operation}; update test client for this GTK version.')
            if position > len(payload):raise ValueError('Truncated Broadway command')

    def run(self):
        fragmented=bytearray()
        try:
            while not self.stopping:
                first,second=self.receive(2)
                length=second & 0x7f
                if length==126:length=struct.unpack('!H',self.receive(2))[0]
                elif length==127:length=struct.unpack('!Q',self.receive(8))[0]
                if length > 64*1024*1024:raise ValueError('Oversized private-display message')
                if second & 0x80:raise ValueError('Unexpected masked server frame')
                payload=self.receive(length);opcode=first & 0xf
                if opcode==8:return
                if opcode==9:self.send_frame(payload,10);continue
                if opcode==10:continue
                if opcode not in (0,2):raise ValueError('Expected binary Broadway data')
                fragmented.extend(payload)
                if first & 0x80:
                    self.commands(fragmented);fragmented.clear()
        except BaseException as error:
            if not self.stopping:self.errors.append(error)

    def __enter__(self):
        self.socket=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.socket.settimeout(5)
        try:
            self.socket.connect(self.path)
            key=base64.b64encode(os.urandom(16)).decode()
            request=('GET /socket HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n'
                     'Connection: Upgrade\r\nSec-WebSocket-Version: 13\r\n'
                     'Sec-WebSocket-Protocol: broadway\r\nSec-WebSocket-Key: '+key+'\r\n\r\n')
            self.socket.sendall(request.encode())
            response=bytearray()
            while not response.endswith(b'\r\n\r\n'):
                response.extend(self.receive(1))
                if len(response)>8192:raise ValueError('Invalid private-display handshake')
            expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
            if not response.startswith(b'HTTP/1.1 101') or expected.lower() not in bytes(response).lower():
                raise ValueError('Private-display WebSocket handshake failed')
            self.socket.settimeout(None)
            self.event(12,1600,1200,self.scale)
            self.thread=threading.Thread(target=self.run,name='vapor-private-display',daemon=True)
            self.thread.start()
            return self
        except BaseException:
            self.socket.close();raise

    def __exit__(self,kind,value,traceback):
        self.stopping=True
        try:self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:pass
        self.socket.close()
        if self.thread:
            self.thread.join(timeout=5)
            if self.thread.is_alive():raise RuntimeError('Private-display client did not stop')
        if self.errors and kind is None:raise RuntimeError(f'Private-display protocol failed: {self.errors}')
