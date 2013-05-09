Atomizer
========

Python/BeautifulSoup extracts data from Word 2010 filtered HTML. Custom application, not a general tool.

This is a tool created for the Atomic Scala book (http://www.AtomicScala.com), to automatically create a starting point for the seminar
presentation material. It outputs Asciidoc Slidy format.

I'm just storing this here as an experiment, and in case anyone gets some benefit from the code.

There are some clever things here; the best is probably the builder pattern combined with chain of responsibility. Also
possibly the use of the class decorator. There are also some hacky things where I've started on one approach and 
then another approach has been slowly emerging but not refactored back into the design. I think most of the hacky
things are in the BookElement hierarchy.

Hope you get some value by reading it...
