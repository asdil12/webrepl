#!/usr/bin/python3

import sys
import select
import termios, tty
import argparse
import textwrap

import websocket # requires python3-websocket_client

ap = argparse.ArgumentParser()
ap.add_argument('host', type=str, help=textwrap.dedent('''\
    The host to connect to.
    The port is optional and defaults to 8266.
    These formats are accepted:
      1.2.3.4, 1.2.3.4:8266, [fdff:abc::1], [fe80::1%%eth0]:8266, foobar.de:8266,
      ws://1.2.3.4/, wss://foobar.de:443/
'''))
ap.add_argument('-p', dest='password', type=str, help=textwrap.dedent('''\
    Password for authentication.
    Will be requested interactively by remote if omitted.
'''))
args = ap.parse_args()

default_port = "8266"

if args.host.startswith('ws://') or args.host.startswith('wss://'):
    url = args.host
elif ']' in args.host:
    if ':' in args.host.split(']')[1]:
        # we got ipv6 address like [2000::123]:8266 or [fe80::123%eth0]:8266
        url = f"ws://{args.host}/"
    else:
        # we got ipv6 address like [2000::123] or [fe80::123%eth0]
        url = f"ws://{args.host}:{default_port}/"
elif args.host.count(':') > 1:
    # we got ipv6 address like 2000::123 or fe80::123%eth0
    url = f"ws://[{args.host}]:{default_port}/"
elif ':' in args.host:
    # we got ipv4 address like 1.2.3.4:8266 or hostnmae like foo.de:8266
    url = f"ws://{args.host}/"
else:
    # we got ipv4 address like 1.2.3.4 or hostnmae like foo.de
    url = f"ws://{args.host}:{default_port}/"

ws = websocket.WebSocket()
ws.connect(url)
print(f"Connected to '{url}'. Exit with Ctrl+]")

password_sent = False
old_settings = termios.tcgetattr(0)
try:
    tty.setraw(sys.stdin.fileno())
    while True:
        readable, _, _ = select.select([ws.sock.fileno(), sys.stdin.fileno()], [], [])
        for s in readable:
            if s == ws.sock.fileno():
                r = ws.recv()
                sys.stdout.write(r)
                sys.stdout.flush()
                if r == "Password: " and args.password and not password_sent:
                    print('*'*len(args.password))
                    ws.send(f"{args.password}\n")
                    password_sent = True
            elif s == sys.stdin.fileno():
                c = sys.stdin.buffer.read(1)
                if c == b'\x1d':
                    termios.tcsetattr(0, termios.TCSADRAIN, old_settings)
                    sys.exit()
                ws.send(c)
finally:
    termios.tcsetattr(0, termios.TCSADRAIN, old_settings)
