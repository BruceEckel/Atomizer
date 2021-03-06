# -*- coding: windows-1252 -*-
"""
Takes "Filtered HTML" output from Word 2010 and pre-cleans
it to prepare for use by Atomizer.py
"""
import re, glob, string, itertools, collections, bs4
from bs4 import BeautifulSoup, UnicodeDammit
from pprint import pprint, pformat
import sys
sys.stdout = file("AtomicScalaCleaned.html", 'w')

if __name__ == "__main__":
    book = open(glob.glob("AtomicScala*.htm")[0], "rU").read()
    soup = BeautifulSoup(book, from_encoding="windows-1252")
    for tag in soup.findAll('span'):
        if tag.br and tag.br.has_key("style") and \
            "page-break-before:always" in tag.br["style"]:
            tag.extract()

    for tag in soup.findAll('br'):
        if tag.has_key("style") and "page-break-before:always" in tag["style"]:
            tag.extract()

    for tag in soup.findAll('p'): # Remove all empty paragraphs
        if not tag.text.strip():
            tag.extract()

    print soup.encode("windows-1252")
