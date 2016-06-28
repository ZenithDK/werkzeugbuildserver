#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click
import ConfigParser
import os
import logging
import SocketServer
import subprocess
import sys
import threading

APPLICATION = "WerkzeugBuildServer"
AUTHOR = "jof.guru"

config_filename = click.get_app_dir(APPLICATION, AUTHOR)

# Initialize logging
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG# if debug else logging.ERROR if quiet else logging.INFO)
)
logger = logging.getLogger(__name__)

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
        usb_port,
        key
    ):
        SocketServer.TCPServer.__init__(
            self,
            server_address,
            RequestHandlerClass
        )
        self.adk_path = adk_path
        self.usb_port = usb_port
        self.key = key

# I broke this part up into a specific wrapper so I could later include/use it
# in the debugclient.py to make a special mode where it can run standalone (no
# TCP involved) if the user just wants to run it locally on his/her Wintendo machine.
class VmDebugLoggerWrapper():
    def __init__(self, adk_path=os.path.join("C:/", "ADK4.0.0"), usb_port=0):
        self.full_path = os.path.join(
                adk_path,
                "tools",
                "bin",
                "vmdebuglogger.exe"
                )
        self.usb_port = usb_port
        logger.info("SERVER - adk: {} - usb: {}".format(self.full_path, self.usb_port))

    def runDebug(self):
        self.process = subprocess.Popen(
            [self.full_path, "--usb", self.usb_port],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return self.process.stdout

    def terminate(self):
        # Check if process has terminated itself, if not, then terminate
        self.process.poll()
        logger.debug("VmDebugLoggerWrapper terminate - returncode: {}".format(self.process.returncode))
        if self.process.returncode == None:
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
            key = self.request.recv(1024).strip()
        except ValueError:
            self.wfile.write("Incorrect syntax\n")
            return

        if key != self.server.key:
            self.wfile.write("Incorrect key\n")
            return

        # Casting usb_port to int and back to string is just a basic simple
        # security check, make sure the parameter is only an int and not command
        # injection.
        vdlw = VmDebugLoggerWrapper(self.server.adk_path, self.server.usb_port)
        logger.info("DebugRequestHandler - handle - adk: {} - usb: {}".format(self.server.adk_path, self.server.usb_port))

        try:
            debug_stdout = vdlw.runDebug()
        except OSError:
            self.wfile.write("Could not run executable.\n")
            logger.error("Could not run executable")
            return

        debug_thread = DebugThread(self.wfile, debug_stdout)
        debug_thread.start()

        while True:
            try:
                client_data = self.request.recv(1024)

                if not client_data:
                    vdlw.terminate()
                    break
            except KeyboardInterrupt as e:
                logger.info('User interrupted execution, exiting')
                break

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('-c', '--config',
              type=click.Path(exists=False, dir_okay=False),
              help="Specify configuration file to use",
              default="{}/debugclient.ini".format(config_filename),
              required=False)
@click.option('-u', '--usb',
              help="CSR USBSPI port number",
              default=0,
              show_default=True,
              required=False)
@click.option('-a', '--adk',
              help="The base directory for the ADK",
              show_default=True,
              default=os.path.join("C:/", "ADK4.0.0"),
              required=False)
@click.option('-l', '--listen',
              help="Specify listening IP-address or hostname",
              show_default=True,
              default='127.0.0.1')
@click.option('-p', '--port',
              help="Remote port for DebugServer",
              show_default=True,
              default='7655')
@click.option('-k', '--key',
              help="Specify the authentication shared secret key")
@click.option('-s', '--save',
        help="Save the supplied configuration as default",
        default=False)
@click.pass_context
def main(ctx, config, usb, adk, listen, port, key, save):
    config_parser = ConfigParser.ConfigParser()
    config_parser.read(config)

    if not config_parser.has_section("server"):
        config_parser.add_section("server")

    # Click has no way of retrieving the default values for commands, so resort to this hackery
    default_dict = dict(zip([command.name for command in ctx.command.params], [command.default for command in ctx.command.params]))

    logger.info(ctx.params)

    for k, v in ctx.params.items():
        if k == "save" or k == "config":
            continue

        if v != default_dict[k] or not config_parser.has_option("server", k):
            config_parser.set("server", str(k), str(v))

    if config_parser.get("server", "key") in [None, "None"]:
        logger.error("Error: A shared secret key must be specified!")
        sys.exit(1)

    if save:
            try:
                os.makedirs(os.path.dirname(config))
            except:
                pass
            with open(config, "w") as configfile:
                config_parser.write(configfile)

    SocketServer.TCPServer.allow_reuse_address = True
    server = DebugRequestServer(
        (
            config_parser.get("server", "listen"),
            config_parser.getint("server", "port")
        ),
        DebugRequestHandler,
        config_parser.get("server", "adk"),
        config_parser.get("server", "usb"),
        config_parser.get("server", "key")
    )

    logger.info('debugserver now running - waiting for client to connect')
    try:
        server.serve_forever()
    except KeyboardInterrupt as e:
        logger.info('User interrupted execution, exiting')

if __name__ == "__main__":
    main()
