#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click
import ConfigParser
import os
import logging
import socket
import sys

from debugserver import VmDebugLoggerWrapper

APPLICATION = "WerkzeugBuildClient"
AUTHOR = "jof.guru"

config_filename = click.get_app_dir(APPLICATION, AUTHOR)
config_parser = ConfigParser.ConfigParser()

# Initialize logging
#logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
logging.basicConfig(format='%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG# if debug else logging.ERROR if quiet else logging.INFO)
)
logger = logging.getLogger(__name__)

class DebugClientRemote:
    debugserver_socket = None

    def request_debug(self, hostname, port, key):
        self.debugserver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_file = None

        logger.info('remote request_debug')
        try:
            self.debugserver_socket.connect((hostname, port))
            self.debugserver_socket.send("{}\n".format(key))
            self.socket_file = self.debugserver_socket.makefile()
        except socket.error as e:
            logger.error("Connection error: {}".format(e))
            sys.exit(1)

        return self.socket_file

    def stop_debug(self):
        logger.info('remote stop_debug')
        if self.debugserver_socket is not None:
            self.debugserver_socket.close()
            self.debugserver_socket = None
        if self.socket_file is not None:
            self.socket_file.close()
            self.socket_file = None

class DebugClientLocal:
    vdlw = None
    debug_stdout = None

    def request_debug(self, adk, usb):
        logger.info('DebugClientLocal.request_debug()')
        # Casting usb_port to int and back to string is just a basic simple
        # security check, make sure the parameter is only an int and not command
        # injection.
        self.vdlw = VmDebugLoggerWrapper(adk_path=adk, usb_port=usb)
        self.debug_stdout = self.vdlw.runDebug()

        return self.debug_stdout

    def stop_debug(self):
        logger.info('DebugClientLocal.stop_debug()')
        self.vdlw.terminate()
        self.debug_stdout = None


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-c', '--config',
              type=click.Path(exists=False, dir_okay=False),
              help="Specify configuration file to use",
              default="{}/debugclient.ini".format(config_filename),
              required=False)
@click.option('-s', '--save',
        help="Save the supplied configuration as default",
        default=False)
@click.option('--porcelain', is_flag=True)
@click.pass_context
def cli(ctx, config, save, porcelain):
    logger.info('CLI running')
    config_parser.read(config)

    if not config_parser.has_section("defaults"):
        config_parser.add_section("defaults")

    # TODO: This is done at the wrong time, needs to be done AFTER local/remote has been called
    # TODO: Need to check that the provided value is different from the default, if then, store value in config, only save if -s is provided
    # Generic config settings
    if save:
        try:
            os.makedirs(os.path.dirname(config_parser))
        except:
            pass
        with open(config_parser, "w") as configfile:
            config_parser.write(configfile)


@cli.command()
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
@click.pass_context
def local(ctx, usb, adk):
    logger.info('local running')

    # Click has no way of retrieving the default values for commands, so resort to this hackery
    #default_dict = dict(zip([command.name for command in ctx.command.params], [command.default for command in ctx.command.params]))
    #if usb != default_dict["usb"] and not config_parser.has_option("defaults", "usb"):
    if not config_parser.has_option("defaults", "usb"):
        config_parser.set("defaults", "usb", usb)

    #if adk != default_dict["adk"] and not not config_parser.has_option("defaults", "adk"):
    if not config_parser.has_option("defaults", "adk"):
        config_parser.set("defaults", "adk", adk)

    debug_client = DebugClientLocal()
    handle = debug_client.request_debug(adk, usb)
    logger.info('local done')
    process_handle(handle, debug_client)

@cli.command()
@click.option('-p', '--port',
              help="Remote port for DebugServer",
              show_default=True,
              default='7655')
@click.option('-k', '--key',
              help="Specify the authentication shared secret key")
@click.argument('ip_address',
              default="127.0.0.1",
              required=False)
@click.pass_context
def remote(ctx, port, key, ip_address):
    """Connect debugclient to remote debugserver.

    [IP_ADDRESS] specifies the hostname/ip of the remote debugserver."""
    logger.info('remote running')

    # Config settings for 'ip_address'
    if not config_parser.has_section(ip_address):
        config_parser.add_section(ip_address)

    if not config_parser.has_option("defaults", "remote"):
        config_parser.set("defaults", "remote", ip_address)

    if not config_parser.has_option(config_parser.get("defaults", "remote"), "port"):
        config_parser.set(ip_address, "port", port)

    if key != None:
        config_parser.set(ip_address, "key", key)

    if (not config_parser.has_option(config_parser.get("defaults", "remote"), "key")
        or config_parser.get(config_parser.get("defaults", "remote"), "key") in [None, "None"]):
        logger.error("A shared secret key must be specified!")
        sys.exit(1)

    debug_client = DebugClientRemote()
    handle = debug_client.request_debug(
        config_parser.get("defaults", "remote"),
        int(config_parser.get(config_parser.get("defaults", "remote"), "port")),
        config_parser.get(config_parser.get("defaults", "remote"), "key"))
    logger.info('remote done')
    process_handle(handle, debug_client)


def process_handle(handle, debug_client):
    logger.info('process_handle running')

    try:
        while True:
            line = handle.readline()
            if not line:
                logger.error("Socket closed.")
                sys.exit(1)
            logger.info(line.strip())
    except socket.error as e:
        logger.error("Connection error: {}".format(e))
    finally:
        handle.close()
        debug_client.stop_debug()

    logger.info('process_handle done')

if __name__ == "__main__":
    cli()