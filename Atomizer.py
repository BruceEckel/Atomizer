# -*- coding: windows-1252 -*-
"""
Takes "Filtered HTML" output from Word 2010 and parses it into chapters, then turns
all tagged types into classes. Ultimate goal: extract contents
of book into AsciiDoc format for rapid creation of seminar slides.
Uses "Builder" design pattern, also chain of responsibility
TODO: generate example output files, compile as test
"""
import re, string, collections, bs4, os, os.path
from bs4 import BeautifulSoup
import sys
sys.stdout = file("OutputTrace.txt", 'w')

def clean(line):
    line = repr(line)
    line = line.replace(r"\u2026", "...")
    line = line.replace(r"\xa0", " ")
    line = line.replace(r"\'", "'")
    line = line.replace(r"\\", "_dblbackslsh_")
    line = line.replace(r"\n", " ")
    line = line.replace("_dblbackslsh_", "\\")
    return line[:-1]


class BookBuilder(object):
    grabbers = []
    def __init__(self, soup):
        self.grabbers = list(BookBuilder.grabbers) # Copy
        self.book = []
        for tag in soup:
            self.transform(tag)

    def transform(self, tag):
        if type(tag) is bs4.element.NavigableString:
            if tag.string == u'\n': return
        if type(tag) is bs4.element.Tag:
            if tag.string == u'\n': return
            if tag.name == "h2":
                return self.book.append(Heading2(tag))
            if tag.name == "h3":
                return self.book.append(Heading3(tag))
            if tag.has_key("class"):
                for grab in list(self.grabbers):
                    if grab(tag, self):
                        return
        self.book.append(NotTag(tag)) # Catch all that don't match


############ BookElements ####################################

class BookElement(object):
    matchStr = "Non Matching"

    def __init__(self, tag): self.tag = tag

    def tagname(self):
        return "\n[" + self.__class__.__name__ + "]\n"

    def __repr__(self):
        return self.tagname() + repr(self.tag)

    def adoc(self):
        # Produce Asciidoc output for this element
        return Paragraph.clean(repr(self.tag.get_text())) + "\n"    


class Paragraph(BookElement):
    matchStr = "MsoNormal"

    @staticmethod
    def clean(s, ltrim=2, rtrim=1): # Outputs asciidoc markup
        s = s[ltrim:][:-rtrim]
        s = s.replace(r"\xa0", " ")
        s = s.replace(r"\n", " ")
        s = s.replace("\u201c", "``") # Left double quote
        s = s.replace("\u201d", "''") # Right double quote
        s = s.replace("\u2018", "`") # Left single quote
        s = s.replace("\u2019", "'") # Right single quote
        s = s.replace("\u2013", "&#151;") # Em-dash
        s = s.replace("\u2026", "...") # Ellipse
        s = s.replace(r"\'", "'") # Ellipse
        s = " ".join(s.split()) # remove multiple spaces
        return s

    @staticmethod
    def cleanToWindows(s):
        s = s[2:][:-1]
        s = s.replace(r"\xa0", " ")
        s = s.replace(r"\n", " ")
        s = s.replace("\u201c", "\x93") # Left double quote
        s = s.replace("\u201d", "\x94") # Right double quote
        s = s.replace("\u2018", "\x91") # Left single quote
        s = s.replace("\u2019", "\x92") # Right single quote
        s = s.replace("\u2013", "\x97") # Em-dash
        s = s.replace("\u2026", "\x85") # Ellipse
        s = s.replace(r"\'", "'") # Ellipse
        s = " ".join(s.split()) # remove multiple spaces
        return s

    def grabber(tag, bookBuilder):
        if Paragraph.matchStr in tag['class']:
            if len(tag.get_text().strip()): # No empty paragraphs
                bookBuilder.book.append(Paragraph(tag))
            return True
        return False
    BookBuilder.grabbers.append(grabber)

    def adoc(self):
        result = []
        for piece in self.tag:
            if type(piece) is bs4.element.Tag:
                if piece.name == "span" and piece.has_key("class") and \
                    "XrefChar" in piece["class"]:
                    piece = "[yellow]*" + piece.get_text() + "*"
            r = repr(piece)
            if r.startswith("u'"):
                result.append(Paragraph.clean(r))
            else:
                if r.startswith("<i>"):
                    result.append("'" + Paragraph.clean(r, 3, 4) + "'")
                elif r.startswith("<b>"):
                    result.append("`" + Paragraph.clean(r, 3, 4) + "`")
        return " ".join(result).rstrip() + "\n"    


class Code(BookElement):
    matchStr = "Code"

    @staticmethod
    def testForCodeNumber(tag):
        return  type(tag) is bs4.element.Tag and \
                tag.name == "span" and \
                tag.has_key("class") and \
                "CodeNumber" in tag["class"]

    def grabber(tag, bookBuilder):
        if Code.matchStr in tag['class']:
            if any(map(Code.testForCodeNumber, tag)):
                bookBuilder.book.append(Example(tag))
                bookBuilder.grabbers.insert(0, Example.grabber)
            else:
                bookBuilder.book.append(CodeFragment(tag))
                bookBuilder.grabbers.insert(0, CodeFragment.grabber)
            return True
        return False
    BookBuilder.grabbers.append(grabber)


class Example(BookElement):
    """
    Single contiguous block of code, appears as line-numbered example in the book.
    Stored without line numbers.
    """
    ltrim = 6
    source = "[source,scala, numbered]"

    def __init__(self, tag):
        super(Example,self).__init__(tag)
        self.lines = [tag]
        self.finished = ""

    @staticmethod
    def grabber(tag, bookBuilder):
        if Code.matchStr in tag['class']:
            if any(map(Code.testForCodeNumber, tag)):
                bookBuilder.book[-1].lines.append(tag)
            return True
        else:
            bookBuilder.grabbers.pop(0) # Remove the grabber
            return False

    def finish(self, ltrim = 6):
        if self.finished: return self.finished
        result = ""
        for ln in self.lines:
            cleanedLine = clean(ln.get_text())
            cleanedLine = cleanedLine[self.__class__.ltrim:]
            result += cleanedLine + "\n"
        self.finished = result.rstrip()
        return self.finished

    def __repr__(self):
        return self.tagname() + self.finish()

    def adoc(self):
        return self.__class__.source + "\n" + \
        "--------------------------------------\n" + \
        self.finish() + \
        "\n--------------------------------------\n"


class CodeFragment(Example):
    """
    Un-numbered text that appears in code font in the book,
    as a standalone paragraph.
    """
    ltrim = 2
    source = "[source,scala]"

    @staticmethod
    def grabber(tag, bookBuilder):
        if Code.matchStr in tag['class']:
            if not any(map(Code.testForCodeNumber, tag)):
                bookBuilder.book[-1].lines.append(tag)
            return True
        else:
            bookBuilder.grabbers.pop(0) # Remove the grabber
            return False


class Exercise(BookElement):
    matchStr = "Exercise"

    def grabber(tag, bookBuilder):
        if Exercise.matchStr in tag['class']:
            bookBuilder.book.append(Exercise(tag))
            return True
        return False
    BookBuilder.grabbers.append(grabber)

    def adoc(self):
        result = ""
        funkySpaces = self.tag.find("span", {"style":'font:7.0pt "Times New Roman"'})
        if funkySpaces:
            funkySpaces.replace_with(" ")
        exn = self.tag.contents[0]
        if isinstance(exn, bs4.element.Tag):
          exn = exn.get_text()
        exerciseNumber = exn.split('.')[0] # Remove trailing period
        result += exerciseNumber + ". "
        for element in self.tag.contents[1:]:
            print repr(element)
            print
            if type(element) is bs4.element.NavigableString:
                result += Paragraph.clean(repr(element))
            elif type(element) is bs4.element.Tag:
                if element.name == 'b':
                    result += " `" + Paragraph.clean(repr(element.get_text())) + "` "
                elif element.name == 'i':
                    result += " '" + Paragraph.clean(repr(element.get_text())) + "' "
                elif element.name == "span" and element.has_key("class"):
                    if "CodeChar" in element["class"]:
                        codeBlock = Paragraph.clean(repr(element.get_text())).replace("<br/>","")
                        result += "\n[source,scala]\n" + \
                            "--------------------------------------\n" + \
                            repr(element.get_text())[2:][:-1].replace(r"\n", "\n").replace(r"\xa0", " ") + \
                            "\n--------------------------------------\n"
                    if "XrefChar" in element["class"]:
                        result += " *" + Paragraph.clean(repr(element.get_text())) + "* "
            else:
                result += repr(element)
        result = result.replace(" ,", ", ").replace(" .", ". ")
        result = result.replace("( ", "(").replace(" )", ")")
        return result


class NumberedList(BookElement):
    matchStr = "MsoListParagraphCxSpFirst"
    def __init__(self, tag):
        super(NumberedList,self).__init__(tag)
        self.items = [tag]
        self.finished = ""

    def grabber(tag, bookBuilder):
        if NumberedList.matchStr in tag['class']:
            bookBuilder.book.append(NumberedList(tag))
            bookBuilder.grabbers.insert(0, NumberedList.subsequentGrabber)
            return True
        return False
    BookBuilder.grabbers.append(grabber)

    @staticmethod
    def subsequentGrabber(tag, bookBuilder):
        bookBuilder.book[-1].items.append(tag)
        if "MsoListParagraphCxSpMiddle" in tag['class']:
            return True
        if "MsoListParagraphCxSpLast" in tag['class']:
            bookBuilder.grabbers.pop(0) # Remove the subsequentGrabber
            return True
        assert False, "bullet points out of synch"

    def finish(self, ltrim = 3):
        if self.finished: return self.finished
        result = ""
        for ln in self.items:
            cleanedLine = Paragraph.clean(repr(ln.get_text()))
            cleanedLine = cleanedLine[ltrim:]
            result += ". " + cleanedLine.strip() + "\n\n"
        self.finished = result
        return self.finished

    def __repr__(self):
        return self.tagname() + self.finish()

    def adoc(self):
        return self.finish()


class NotTag(BookElement): pass


class Heading2(BookElement):
    sep = '-'
    def adoc(self):
        title = repr(self.tag.get_text())[2:][:-1]
        return title + "\n" + self.__class__.sep * len(title) + "\n"


class Heading3(Heading2):
    sep = '~'


def addGrabber(BookElementClass):
    # Class decorator to automatically add grabber to builder
    def grabber(tag, bookBuilder):
        if BookElementClass.matchStr in tag['class']:
            bookBuilder.book.append(BookElementClass(tag))
            return True
        return False
    BookBuilder.grabbers.append(grabber)
    return BookElementClass


@addGrabber
class Bullet(BookElement): # Don't need to make this work like NumberedList
    matchStr = "Bulleted"

    def adoc(self):
        return "  * " + Paragraph.clean(repr(self.tag.get_text())) + "\n"


@addGrabber
class Quote(BookElement):
    matchStr = "MsoQuote"


@addGrabber
class SolnsLink(BookElement):
    matchStr = "SolnsLink"
    def adoc(self): return ""


####### End of BookElements ###################


class Chapter(object):

    def __init__(self, name, rawData):
        self.name = name
        self.soup = BeautifulSoup(rawData, from_encoding="windows-1252")
        self.elements = BookBuilder(self.soup).book

    @staticmethod
    def chapterize(bookSource):
        """
        Break book into Chapter objects, return ordered dictionary
        of Chapters, keyed by chapter name
        """
        # Cleanup:
        bookSource = bookSource.replace("<br>", "<br/>").replace("</br>", "<br/>")
        bookSource = bookSource.replace("<p class=MsoNormal>&nbsp;</p>\n", "")
        # Split into chapter titles and contents:
        pieces = re.split("<h1>(.*?)</h1>", bookSource, flags=re.DOTALL)
        odict = collections.OrderedDict()
        odict[u"Front Matter"] = Chapter(u"Front Matter", pieces[0])
        del pieces[0] # Remove material up to first <h1>
        def chapterName(glop):
            name = BeautifulSoup(glop, from_encoding="windows-1252").get_text().strip()
            name = filter(lambda x: x in string.printable, name)
            name = " ".join(map(string.strip, name.split()))
            return name
        odict.update([(name, Chapter(name, rawData))
          for name, rawData in zip(map(chapterName, pieces[::2]), pieces[1::2])])
        return odict

    def __repr__(self): return self.name

    def header(self):
        return "\n" + "=" * 40 + "\n" + self.name + "\n" + "=" * 40


def seminarSubset(chapters):
    summarized = collections.OrderedDict(chapters)
    for cn in summarized.keys():
        if cn == "Summary 1": break
        del summarized[cn]
    for cn in summarized.keys()[1:]:
        if cn == "Summary 2": break
        del summarized[cn]
    for cn in reversed(summarized.keys()):
        if cn == "Appendix B: Calling Scala from Java": break
        del summarized[cn]
    return summarized

def slideChapterHeader(title):
    return title + "\n" + '=' * len(title) + \
"""
:author: From "Atomic Scala" +
by Bruce Eckel & Dianne Marsh. (c)2013 Mindview LLC. +
Not for distribution
:copyright: 2013 MindView LLC
:backend:   slidy
:max-width: 30em
:data-uri:
:source-highlighter: pygments
:icons:
:deckjs_theme: neon
:deckjs_transition: fade
:pygments:
:pygments_style: friendly
:scrollable:

== %s
""" % title
# good with swiss: *borland, manni, perldoc, tango, autumn, bw
# good with neon: monokai, manni, *perldoc, *default, *vs, *trac, 
#                 *fruity, *autumn, emacs, **friendly, native


def buildSeminar(chapters):
    if not os.path.exists("slides"):
        os.mkdir("slides")
    for n, (name, chap) in enumerate(chapters.items()):
        basename = "%02d-%s" % (n, "".join(name.split()))
        basename = basename.split(':')[0].replace('&', 'And')
        fname = os.path.join("slides", "%s.slidy" % basename)
        with file(fname, "w") as chapSlides:
            print >>chapSlides, slideChapterHeader(name)
            for el in chap.elements:
                # if type(el) is Exercise:
                #     print >>chapSlides, el
                #     print >>chapSlides
                #     for piece in el.tag:
                #         print >>chapSlides, repr(piece).replace("<br/>","")
                #         print >>chapSlides
                #     print el.adoc()
                #     print
                print >>chapSlides, el.adoc().replace(" ,", ",")


if __name__ == "__main__":
    chapters = Chapter.chapterize(open("AtomicScalaCleaned.html", "rU").read())
    summarized = seminarSubset(chapters)
    buildSeminar(summarized)
