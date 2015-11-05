#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import sys
import os

path = ["."]
root = os.path.abspath(os.sep)
highest_svn = ""
project_name = ""

def abspath_from_list(path):
    return os.path.abspath(os.path.join(*path))

while os.path.abspath(os.path.join(*path)) != root:
    if os.path.isdir(os.path.join(abspath_from_list(path), ".svn")):
        highest_svn = abspath_from_list(path)
    path.append("..")

project_name = os.path.basename(highest_svn)
