#!/usr/bin/env python3
"""Read the real Java server-list status on each contract game port."""
import json
import socket
import struct
from pathlib import Path


def varint(number):
    result=bytearray()
    while True:
        part=number & 127
        number >>= 7
        result.append(part | (128 if number else 0))
        if not number:
            return bytes(result)


def read_varint(sock):
    value=0
    for i in range(5):
        byte=sock.recv(1)
        if not byte:
            raise ConnectionError('Truncated VarInt')
        value |= (byte[0]&127) << (7*i)
        if byte[0]<128:
            return value
    raise ValueError('Oversized VarInt')


def exact(sock,length):
    result=bytearray()
    while len(result)<length:
        chunk=sock.recv(length-len(result))
        if not chunk:
            raise ConnectionError('Truncated status frame')
        result.extend(chunk)
    return bytes(result)


def status(port):
    host=b'127.0.0.1'
    payload=varint(0)+varint(777)+varint(len(host))+host+struct.pack('>H',port)+varint(1)
    with socket.create_connection(('127.0.0.1',port),8) as sock:
        sock.sendall(varint(len(payload))+payload)
        sock.sendall(b'\x01\x00')
        length=read_varint(sock)
        if length>1024*1024 or read_varint(sock)!=0:
            raise ValueError('Invalid status frame')
        return json.loads(exact(sock,read_varint(sock)))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result={name:status(port) for name,port in [('vanilla',25575),('pumpkin',25576)]}
    raw=json.dumps(result,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(raw)
    print(raw)
