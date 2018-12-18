#!/usr/bin/env python3

import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import os, pwd, grp

from cgroups import Cgroup

HOST_NAME = 'localhost'
PORT_NUMBER = 80

def drop_privileges(uid_name='nobody', gid_name='nobody'):
    if os.getuid() != 0:
        # We're not root so, like, whatever dude
        return

    # Get the uid/gid from the name
    running_uid = pwd.getpwnam(uid_name).pw_uid
    running_gid = grp.getgrnam(gid_name).gr_gid

    # Remove group privileges
    os.setgroups([])

    # Try setting the new uid/gid
    os.setgid(running_gid)
    os.setuid(running_uid)

    # Ensure a very conservative umask
    old_umask = os.umask(0o77)

class MyHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        paths = {
            '/': {'status': 200}
        }

        if self.path in paths:
            self.respond(paths[self.path])
        else:
            self.respond({'status': 500})

    def handle_http(self, status_code, path):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        return bytes("hello\n", 'UTF-8')

    def respond(self, opts):
        response = self.handle_http(opts['status'], self.path)
        self.wfile.write(response)

if __name__ == '__main__':
    server_class = HTTPServer
    httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
    print(time.asctime(), 'Server Starts - %s:%s' % (HOST_NAME, PORT_NUMBER))

    newpid = os.fork()
    if newpid == 0:
        # Drop capabilities
        print("=-" * 50)
        os.system("capsh --print")
        print("=-" * 50)
        drop_privileges()
        print("PRIVILEGES DROPPED")
        print("=-" * 50)
        os.system("capsh --print")
        print("=-" * 50)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        print(time.asctime(), 'Server Stops - %s:%s' % (HOST_NAME, PORT_NUMBER))
    else:
        # CGroups
        cg = Cgroup('charlie', user='nobody')
        cg.set_cpu_limit(0.1)
        cg.set_memory_limit(100, unit='megabytes')
        cg.add(newpid)
        print(os.getpid(), newpid)
