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

**Final Note**: The program takes the HTML output of a specific book and reformats it to
slides. The point was to do as much as possible automatically, but ultimately the material
must be hand-edited (in particular, to cut the prose down to bullet points). If I was going
to do more, I'd go back and refactor and redesign, but right now the goal was to produce the
output so I can move to the next step. I've learned a great deal about the problem in
the process of solving it, and you see here a lot of the dross from that learning process. If I were to redesign it things would be cleaner.

Finally, a lot of the hackiness comes from my lack of complete knowledge of BeautifulSoup and also the various character encodings -- I often just hacked my way through to tolerable output rather than figuring out how to solve the problem fundamentally. Both BS and encodings have been an ongoing challenge.

Hope you get some value from it...
