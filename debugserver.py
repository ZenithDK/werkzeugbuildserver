#!/usr/bin/env python
# -*- coding: utf-8 -*-

import SocketServer
import subprocess
import argparse
import ConfigParser
import threading
import sys
import os

import appdirs

APPLICATION = "WerkzeugBuildServer"
AUTHOR = "jof.guru"


class DebugThread(threading.Thread):
    def __init__(self, socket_file, stdout_file):
        threading.Thread.__init__(self)

        self.socket_file = socket_file
        self.stdout_file = stdout_file


    def run(self):
        while True:
            stdout_byte = self.stdout_file.read(1)
            if not stdout_byte:
                break
            self.socket_file.write(stdout_byte)


class DebugRequestServer(SocketServer.TCPServer):
    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        adk_path,
        key
    ):
        SocketServer.TCPServer.__init__(
            self,
            server_address,
            RequestHandlerClass
        )
        self.adk_path = adk_path
        self.key = key

# I broke this part up into a specific wrapper so I could later include/use it
# in the debugclient.py to make a special mode where it can run standalone (no
# TCP involved) if the user just wants to run it locally on his/her Wintendo machine.
class VmDebugLoggerWrapper():
    def __init__(self, adk_path="C:\\ADK4.0.0\\tools\\bin\\vmdebuglogger.exe", usb_port=0):
        self.full_path = os.path.join(
                adk_path,
                "tools",
                "bin",
                "vmdebuglogger.exe"
                )
        self.usb_port = usb_port

    def runDebug(self):
        self.process = subprocess.Popen(
            [self.full_path, "--usb", "%d"%self.usb_port],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return self.process.stdout

    def terminate(self):
        self.process.terminate()



class DebugRequestHandler(SocketServer.StreamRequestHandler):
    """
    Handles incoming TCP connections and executes a build on the proper
    project using Werkzeug.
    """

    def handle(self):
        """
        Overidden method that gets executed on incoming connections.
        """
        try:
            key, usb_port = self.request.recv(1024).strip().split()
        except ValueError:
            self.wfile.write("Incorrect syntax\n")
            return

        if key != self.server.key:
            self.wfile.write("Incorrect key\n")
            return

        # Casting usb_port to int and back to string is just a basic simple
        # security check, make sure the parameter is only an int and not command
        # injection.
        vdlw = VmDebugLoggerWrapper(self.server.adk_path, int(usb_port))

        try:
            debug_stdout = vdlw.runDebug()
        except OSError:
            self.wfile.write("Could not run executable.\n")
            return

        debug_thread = DebugThread(self.wfile, debug_stdout)
        debug_thread.start()

        while True:
            client_data = self.request.recv(1024)
            if not client_data:
                vdlw.terminate()
                break

if __name__ == "__main__":

    config_filename = appdirs.appdirs.user_config_dir(APPLICATION, AUTHOR)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Werkseug debug-server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        help="Specify configuration file to use",
        default="%s/debugserver.ini"%config_filename
    )

    parser.add_argument(
        "-a",
        "--adk",
        dest="adk",
        help="The base directory for the ADK",
        default="/ADK4.0.0"
    )

    parser.add_argument(
        "-l",
        "--listen",
        dest="listen",
        help="Specift listening IP-address or hostname",
        default="localhost"
    )

    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        help="Specify listening port",
        default=7655
    )

    parser.add_argument(
        "-k",
        "--key",
        dest="key",
        help="Specify the authentication shared secret key",
    )

    parser.add_argument(
        "-s",
        "--save",
        dest="save",
        action="store_true",
        help="Save the supplied configuration as default",
        default=False,
        
    )
    args = parser.parse_args(sys.argv[1:])

    config = ConfigParser.ConfigParser()
    config.read(args.config)

    if not config.has_section("server"):
        config.add_section("server")

    for k, v in args.__dict__.items():
        if k == "save" or k == "config":
            continue

        if v != parser.get_default(k) or not config.has_option("server", k):
            config.set("server", str(k), str(v))

    if config.get("server", "key") in [None, "None"]:
        sys.stderr.write("Error: A shared secret key must be specified!\n")
        sys.exit(1)

    if args.save:
            try:
                os.makedirs(os.path.dirname(args.config))
            except:
                pass
            with open(args.config, "w") as configfile:
                config.write(configfile)

    SocketServer.TCPServer.allow_reuse_address = True
    server = DebugRequestServer(
        (
            config.get("server", "listen"),
            config.getint("server", "port")
        ),
        DebugRequestHandler,
        config.get("server", "adk"),
        config.get("server", "key")
    )

    server.serve_forever()
