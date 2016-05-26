#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import argparse
import ConfigParser
import appdirs
import sys
import os
import re
from colored import fg, attr

APPLICATION = "WerkzeugBuildServer"
AUTHOR = "jof.guru"


class DebugClient:

    def __init__(self, disable_color=False, state_debug_only=False):
        self.disable_color = disable_color
        self.state_debug_only = state_debug_only

    def handleWarnInfo(self, line):
        colors = {
            "ERROR:" : 9,
            "WARN:" : 11,
            "INFO:" : 2,
        }
        if self.disable_color:
            sys.stderr.write(line)
        else:
            sys.stderr.write("%s%s%s"%(fg(colors[line.split()[0]]), line, attr(0)))
        sys.stderr.flush()

    def handleOnCharChannel(self, line):
        clean_line  = re.sub('[^\x20-\x7e\n\r]', '', line.strip())
        if len(clean_line) > 0:
            if self.state_debug_only:
                if re.match("^&[a-z]:", clean_line):
                    print clean_line
            else:
                if len(clean_line.strip()) > 0:
                    sys.stdout.write("%s\n"%clean_line)
            sys.stdout.flush()


    def request_debug(self, hostname, port, key, usb_port, verbose=False):
        printf_keywords = {
            #"On ch" : self.handleOnCharChannel,
            "WARN:" : self.handleWarnInfo,
            "INFO:" : self.handleWarnInfo,
            "ERROR" : self.handleWarnInfo
        }
        debugserver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            debugserver_socket.connect((hostname, port))
            debugserver_socket.send("%s %s\n"%(key, usb_port))
            socket_file = debugserver_socket.makefile()
            while True:
                current_buffer = []
                while True:
                    line = socket_file.readline()
                    if not line:
                        sys.stderr.write("Error: Socket closed.\n")
                        sys.exit(1)
                    if len(line.strip()) == 0:
                        break
                    current_buffer.append(line)

                if verbose:
                    for current_line in current_buffer:
                        sys.stdout.write(current_line)
                else:
                    plain_buffer = []
                    html_chunk = False
                    while len(current_buffer) > 0:
                        current_line = current_buffer.pop(0)
                        if not html_chunk and current_line[:5] in printf_keywords.keys():
                            printf_keywords[current_line[:5]](current_line)
                        elif not html_chunk and "font color" in current_line:
                            html_chunk = True
                            continue
                        elif html_chunk and "/font" in current_line:
                            html_chunk = False
                            continue
                        elif html_chunk:
                            continue
                        elif "On" in current_line and "channel" in current_line and "0x" in current_line:
                            current_line = current_line.replace("On char channel: 0x0 ", "")
                            line_split = current_line.split()
                            if line_split[0] == "On" and line_split[2] == "channel:" and line_split[3][:2] == "0x":
                                continue
                            else:
                                plain_buffer.append(current_line)
                        else:
                            plain_buffer.append(current_line)
                    for current_line in plain_buffer:
                        self.handleOnCharChannel(current_line)

        except socket.error, e:
            sys.stderr.write("Connection error: %s\n"%e)
            sys.exit(1)
        finally:
            debugserver_socket.close()
        

if __name__ == "__main__":

    config_filename = appdirs.appdirs.user_config_dir(APPLICATION, AUTHOR)
    
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Werkzeug debug-client",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-u",
        "--usb",
        dest="usb",
        help="CSR USBSPI port number",
        default="0"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",        
        help="Print all available debug information",
        default=False
    )

    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Quiet. Suppress all output on stdout except state-event debug messages.",
        default=False
    )

    parser.add_argument(
        "-d",
        "--disable",
        dest="disable_color",
        action="store_true",
        help="Disable VT100 colors in output",
        default=False
    )

    parser.add_argument(
        "-c",
        "--config",
        help="Specify configuration file to use",
        default="%s/debugclient.ini"%config_filename
    )

    parser.add_argument(
        "-r",
        "--remote",
        dest="remote",
        help="Remote hostname/ip for DebugServer",
        default="localhost"
    )

    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        help="Remote port for DebugServer",
        default="7654"
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
        default=False
    )

    args = parser.parse_args(sys.argv[1:])

    config = ConfigParser.ConfigParser()
    config.read(args.config)

    if not config.has_section("defaults"):
        config.add_section("defaults")

    if not config.has_section(args.remote):
        config.add_section(args.remote)

    if args.remote != parser.get_default("remote") or not config.has_option("defaults", "remote"):
        config.set("defaults", "remote", args.remote)

    # Please ignore next few lines. I'll format this properly. Like.. Never.
    if args.port != parser.get_default("port") or not config.has_option(config.get("defaults", "remote"), "port"):
        config.set(args.remote, "port", args.port)

    if args.key != None:
        config.set(args.remote, "key", args.key)

    if not config.has_option(config.get("defaults", "remote"), "key") or config.get(config.get("defaults", "remote"), "key") in [None, "None"]:
        sys.stderr.write("Error: A shared secret key must be specified!\n")
        sys.exit(1)

    if args.save:
        try:
            os.makedirs(os.path.dirname(args.config))
        except:
            pass
        with open(args.config, "w") as configfile:
            config.write(configfile)

    debugClient = DebugClient(args.disable_color, args.quiet)
    debugClient.request_debug(
        config.get("defaults", "remote"),
        int(config.get(config.get("defaults", "remote"), "port")),
        config.get(config.get("defaults", "remote"), "key"),
        args.usb,
        args.verbose
    )
