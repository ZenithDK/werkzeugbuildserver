#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import argparse
import ConfigParser
import appdirs
import sys
import os

APPLICATION = "WerkzeugBuildServer"
AUTHOR = "jof.guru"


class BuildClient:

    @staticmethod
    def abspath_from_list(path):
        """
        This is a static method of this class. For no good reason.
        """
        return os.path.abspath(os.path.join(*path))

    @staticmethod
    def request_build(hostname, port, key, project, target):
        buildserver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            buildserver_socket.connect((hostname, port))
            buildserver_socket.send("%s %s %s\n"%(key, project, target))
        except socket.error, e:
            sys.stderr.write("Connection error: %s\n"%e)
            sys.exit(1)
        finally:
            buildserver_socket.close()
        

if __name__ == "__main__":

    config_filename = appdirs.appdirs.user_config_dir(APPLICATION, AUTHOR)
    
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Werkzeug build-client",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-c",
        "--config",
        help="Specify configuration file to use",
        default="%s/buildclient.ini"%config_filename
    )

    parser.add_argument(
        "-r",
        "--remote",
        dest="remote",
        help="Remote hostname/ip for BuildServer",
        default="localhost"
    )

    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        help="Remote port for BuildServer",
        default="7654"
    )

    parser.add_argument(
        "-k",
        "--key",
        dest="key",
        help="Specify the authentication shared secret key",
    )

    parser.add_argument(
        "-t",
        "--target",
        help="The build target",
        default="all"
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

    path = ["."]
    root = os.path.abspath(os.sep)
    highest_svn = ""
    project_name = ""

    while os.path.abspath(os.path.join(*path)) != root:
        if os.path.isdir(os.path.join(BuildClient.abspath_from_list(path), ".svn")):
            highest_svn = BuildClient.abspath_from_list(path)
        path.append("..")

    if highest_svn == "":
        # WHERE'S YOUR GOD NOW???
        sys.stderr.write("Could not determine project/repo name\n")
        sys.exit(1)

    project_name = os.path.basename(highest_svn)

    BuildClient.request_build(
        config.get("defaults", "remote"),
        int(config.get(config.get("defaults", "remote"), "port")),
        config.get(config.get("defaults", "remote"), "key"),
        project_name,
        args.target
    )
