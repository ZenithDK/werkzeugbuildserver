#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os.path
import time
from subprocess import call

if len(sys.argv) < 2:
    sys.stderr.write("Usage: %s <dir-to-watch>\ņ"%sys.argv[0])
    sys.exit(1)

run_file = "%s/run.txt"%sys.argv[1]
build_file = "%s/build.txt"%sys.argv[1]

def getctime(filename):
    try:
        return time.ctime(os.path.getmtime(filename))
    except:
        return 0


def do_build():
    print "Starting build."
    call("../werkzeug/wkz.exe")
    print "Build completed."

def do_run():
    print "Running xIDE"
    call("../werkzeug/wkz.exe xide")
    print "xIDE finished"

run_modified = getctime(run_file)
build_modified = getctime(build_file)




while True:

    if getctime(run_file) != run_modified:
        run_modified = getctime(run_file)
        do_run()

    if getctime(build_file) != build_modified:
        build_modified = getctime(build_file)
        do_build()

    time.sleep(1)
