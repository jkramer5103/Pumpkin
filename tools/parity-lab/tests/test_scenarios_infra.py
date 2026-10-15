"""Infrastructure invariants: framing, private config, and non-destructive seeding."""
import gzip
from pathlib import Path
import socket
import struct
import tempfile
import threading
import unittest
from infra.flat_world import seed_pumpkin_flat
from infra.provision import pumpkin_config,vanilla_config,unit
from infra.rcon_probe import Rcon
import tomllib


def packet(rid,kind,body):
    raw=struct.pack('<ii',rid,kind)+body.encode()+b'\0\0'
    return struct.pack('<i',len(raw))+raw

class InfrastructureTests(unittest.TestCase):
    def test_config_root_keys_do_not_accidentally_land_in_a_table(self):
        cfg=tomllib.loads(pumpkin_config('test-password'))
        self.assertEqual(cfg['seed'],'123456789')
        self.assertEqual(cfg['default_level_name'],'world')
        self.assertEqual(cfg['networking']['java']['address'],'127.0.0.1:25576')
        self.assertEqual(cfg['networking']['rcon']['address'],'127.0.0.1:25586')
        self.assertFalse(cfg['networking']['bedrock']['enabled'])
        self.assertFalse(cfg['telemetry']['enabled'])
        self.assertFalse(cfg['networking']['rcon']['logging']['commands'])
        properties=vanilla_config('test-password')
        self.assertIn('server-ip=127.0.0.1\n',properties)
        self.assertIn('level-type=minecraft:flat\n',properties)
        self.assertIn('rcon.port=25585\n',properties)

    def test_service_only_writes_its_own_runtime_directory_and_has_caps(self):
        for name in ['vanilla','pumpkin']:
            text=unit(name)
            self.assertIn('MemoryMax=3G',text)
            self.assertIn('CPUQuota=150%',text)
            self.assertIn('NoNewPrivileges=yes',text)
            writable=[s for s in text.splitlines() if s.startswith('ReadWritePaths=')]
            self.assertEqual(len(writable),1)
            self.assertTrue(writable[0].endswith('/runtime/'+name))
            self.assertNotIn('password',text)

    def test_flat_seed_refuses_replacement_and_creates_no_chunks(self):
        with tempfile.TemporaryDirectory() as temporary:
            world=Path(temporary)/'world'
            seed_pumpkin_flat(world)
            files={str(p.relative_to(world)) for p in world.rglob('*') if p.is_file()}
            self.assertEqual(files,{'level.dat','data/minecraft/world_gen_settings.dat'})
            before=(world/'level.dat').read_bytes()
            self.assertIn(b'minecraft:flat',gzip.decompress((world/'data/minecraft/world_gen_settings.dat').read_bytes()))
            with self.assertRaises(FileExistsError):
                seed_pumpkin_flat(world)
            self.assertEqual((world/'level.dat').read_bytes(),before)

    def test_probe_handles_fragmentation_and_multi_frame_response(self):
        listener=socket.socket()
        listener.bind(('127.0.0.1',0));listener.listen(1)
        errors=[]
        def serve():
            try:
                with listener.accept()[0] as connection:
                    def exact(n):
                        raw=b''
                        while len(raw)<n:
                            part=connection.recv(n-len(raw))
                            if not part: raise ConnectionError()
                            raw+=part
                        return raw
                    def request():
                        size,=struct.unpack('<i',exact(4))
                        raw=exact(size)
                        return struct.unpack('<ii',raw[:8])+(raw[8:-2].decode(),)
                    self.assertEqual(request(),(1,3,'test-password'))
                    for byte in packet(1,0,'')+packet(1,2,''):
                        connection.sendall(bytes([byte]))
                    rid,kind,body=request()
                    self.assertEqual((kind,body),(2,'probe'))
                    connection.sendall(packet(rid,0,'first'))
                    fence,kind,body=request()
                    self.assertEqual((kind,body),(2,'list'))
                    for byte in packet(rid,0,'second')+packet(fence,0,'players'):
                        connection.sendall(bytes([byte]))
            except BaseException as exc:
                errors.append(exc)
        thread=threading.Thread(target=serve,daemon=True);thread.start()
        client=Rcon({'host':'127.0.0.1','port':listener.getsockname()[1],'password':'test-password'})
        try:
            self.assertEqual(client.command('probe'),'firstsecond')
        finally:
            client.close();thread.join(3);listener.close()
        self.assertFalse(thread.is_alive())
        if errors: raise errors[0]

if __name__=='__main__':
    unittest.main()
