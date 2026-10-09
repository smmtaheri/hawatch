"""Exercise the actual production Nginx configs with a strict Host upstream."""
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4
import pytest


@pytest.mark.parametrize('surface',['gateway','web'])
def test_short_link_preserves_public_host_and_redirect(surface,tmp_path):
    if not shutil.which('docker') or subprocess.run(['docker','info'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        pytest.skip('Real proxy regression test requires local Docker')
    seen=[]
    class Backend(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append((self.path,self.headers.get('Host'),self.headers.get('X-Forwarded-Proto')))
            self.send_response(400 if self.headers.get('Host')!='hawatch.ir' else 302 if self.path=='/p/validCode' else 404)
            if self.path=='/p/validCode':self.send_header('Location','/routes/tochal-darband?date=2026-10-09&start_time=12%3A00&speed=medium')
            self.send_header('Cache-Control','no-store')
            self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Backend)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    backend_port=server.server_port
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    root=Path(__file__).resolve().parents[3]
    if surface=='gateway':
        config=(root/'infra/nginx/nginx.conf').read_text().replace('listen 80;',f'listen {port};').replace('server api:8000;',f'server 127.0.0.1:{backend_port};').replace('server web:5173;',f'server 127.0.0.1:{backend_port};')
    else:
        config='events {}\nhttp { include /etc/nginx/mime.types;\n'+(root/'apps/web/nginx.conf').read_text().replace('listen 5173;',f'listen {port};').replace('api:8000',f'127.0.0.1:{backend_port}')+'\n}'
    path=tmp_path/'nginx.conf';path.write_text(config)
    name='hawatch-share-check-'+uuid4().hex[:8]
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*args):return None
    opener=build_opener(NoRedirect)
    try:
        subprocess.run(['docker','run','--rm','-d','--name',name,'--network','host','-v',f'{path}:/etc/nginx/nginx.conf:ro','nginx:1.27-alpine'],check=True,stdout=subprocess.DEVNULL)
        deadline=time.monotonic()+15
        while True:
            try:
                try:response=opener.open(Request(f'http://127.0.0.1:{port}/p/validCode',headers={'Host':'hawatch.ir','X-Forwarded-Proto':'https'}),timeout=2)
                except HTTPError as error:response=error
                break
            except URLError:
                if time.monotonic()>deadline:raise
                time.sleep(.1)
        assert response.code==302
        assert response.headers['Location']=='/routes/tochal-darband?date=2026-10-09&start_time=12%3A00&speed=medium'
        assert response.headers['Cache-Control']=='no-store'
        assert seen[-1][1]=='hawatch.ir'
        if surface=='gateway':assert seen[-1][2]=='https'
        with pytest.raises(HTTPError) as error:opener.open(Request(f'http://127.0.0.1:{port}/p/missing',headers={'Host':'hawatch.ir'}))
        assert error.value.code==404 and error.value.headers['Cache-Control']=='no-store'
    finally:
        subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        server.shutdown();server.server_close()
