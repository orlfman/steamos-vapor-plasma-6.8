#!/usr/bin/env python3
"""Private GTK 3.24.52 Broadway geometry/transport replies, without user input.

Protocol checked against GTK 3.24.52 gdk/broadway/broadway.js. Share the existing
WebSocket transport, but keep GTK 3 character operations separate from GTK 4.
Images are exported by GTK/Cairo; this client does not render browser pixels.
"""
from pathlib import Path
import runpy
import struct

Transport=runpy.run_path(str(Path(__file__).resolve().with_name('broadway-test-client.py')))['FrameClient']


class FrameClient(Transport):
    def event(self,operation,*arguments):
        if operation==12:
            operation='d';arguments=arguments[:2]
        return super().event(ord(operation),*arguments)

    def configure(self,ident):
        self.event('w',ident,*self.surfaces[ident])

    def commands(self,payload):
        position=0
        def read(fmt):
            nonlocal position
            values=struct.unpack_from('<'+fmt,payload,position)
            position+=struct.calcsize('<'+fmt)
            return values[0] if len(values)==1 else values
        while position<len(payload):
            operation=chr(read('B'));self.serial=read('I')
            if operation=='s':
                ident,x,y,width,height,_temporary=read('HhhHHB')
                self.surfaces[ident]=[x,y,width,height];self.configure(ident)
            elif operation in ('S','H','r','R','d'):
                ident=read('H')
                if operation=='d':self.surfaces.pop(ident,None)
            elif operation=='p':read('HH')
            elif operation=='m':
                ident=read('H');flags=read('B');surface=self.surfaces[ident]
                if flags&1:surface[:2]=read('hh')
                if flags&2:surface[2:]=read('HH')
                self.configure(ident)
            elif operation=='b':
                read('HHH');size=read('I');position+=size;self.frames+=1
            elif operation=='g':read('HB');self.event('g')
            elif operation=='u':self.event('u')
            elif operation=='k':read('H')
            elif operation=='D':return
            else:raise ValueError('Unsupported GTK 3 Broadway operation '+repr(operation))
            if position>len(payload):raise ValueError('Truncated GTK 3 Broadway command')
