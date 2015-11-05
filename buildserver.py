#!/usr/bin/env python
# -*- coding: utf-8 -*-

import SocketServer
import subprocess
import argparse
import ConfigParser
import sys
import os

import appdirs

APPLICATION="WerkzeugBuildServer"
AUTHOR="jof.guru"


class BuildRequestServer(SocketServer.TCPServer):
    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        base_directory,
        key
    ):
        SocketServer.TCPServer.__init__(
            self,
            server_address,
            RequestHandlerClass
        )
        self.base_directory = base_directory
        self.key = key


class BuildRequestHandler(SocketServer.StreamRequestHandler):
    """
    Handles incoming TCP connections and executes a build on the proper
    project using Werkzeug.
    """

    def build(self, repo, target):
        """
        Execute the build target on the project at the specified path
        """
        configuration = {
            "application" : "application"
        }
        exception_config = ConfigParser.ConfigParser()
        exception_config.read("%s/exceptions.ini"%self.server.base_directory)
        if exception_config.has_section(repo):
            for config_key in configuration.keys():
                try:
                    configuration[config_key] = exception_config.get(repo, config_key)
                except ConfigParser.NoOptionError:
                    pass

        full_application_path = os.path.join(
            self.server.base_directory,
            repo,
            configuration["application"]
        )

        try:
            os.chdir(full_application_path)
        except OSError, e:
            yield "Error: Unable to chdir: %s\n"%e
            return

        try:
            process = subprocess.Popen(
                ["../werkzeug/wkz.exe", target],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        except OSError:
            yield "Could not find Werkzeug at the specified repo\n"
            return
        while True:
            stdout_line = process.stdout.readline()
            if not stdout_line:
                break
            yield stdout_line


    def handle(self):
        """
        Overidden method that gets executed on incoming connections.
        """
        try:
            key, repo, target = self.request.recv(1024).strip().split()
        except ValueError:
            self.wfile.write("Incorrect syntax\n")
            return

        if key != self.server.key:
            self.wfile.write("Incorrect key\n")
            return

        for outputline in self.build(repo, target):
            self.wfile.write(outputline)

if __name__ == "__main__":

    config_filename = appdirs.appdirs.user_config_dir(APPLICATION, AUTHOR)

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description="Werkseug build-server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        help="Specify configuration file to use",
        default="%s/buildserver.ini"%config_filename
    )

    parser.add_argument(
        "-b",
        "--base",
        dest="base",
        help="The base directory where you check out all your SVN repos",
        default="/Projects"
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
        default=7654
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

    if config.get("server", "key") == "None":
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
    server = BuildRequestServer(
        (
            config.get("server", "listen"),
            config.getint("server", "port")
        ),
        BuildRequestHandler,
        config.get("server", "base"),
        config.get("server", "key")
    )

    server.serve_forever()
