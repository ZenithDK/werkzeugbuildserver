#!/bin/bash

CURRENTPATH="."
DEEPESTSVN=""

while [ $(realpath ${CURRENTPATH}) != "/" ]
do
    if [ -d "${CURRENTPATH}/.svn" ]
    then
        DEEPESTSVN="${CURRENTPATH}"
    fi
    CURRENTPATH="${CURRENTPATH}/.."
done

if [ "${DEEPESTSVN}" == "" ]
then
    echo "Could not determine project folder."
else
    touch "${DEEPESTSVN}/build.txt"
fi
