# -*- coding: windows-1252 -*-
"""
Takes "Filtered HTML" output from Word 2010 and parses it into chapters, then turns
all tagged types into classes. Ultimate goal: extract contents
of book into AsciiDoc format for rapid creation of seminar slides.
Uses "Builder" design pattern, also chain of responsibility
TODO: generate example output files, compile as test
"""
import re, glob, string, itertools, collections, bs4
from bs4 import BeautifulSoup, UnicodeDammit
from pprint import pprint, pformat
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

bookElementGrabbers = []

class BookBuilder(object):
  def __init__(self, soup):
    self.grabbers = list(bookElementGrabbers) # Copy
    self.book = []
    for tag in soup:
      self.transform(tag)

  def transform(self, tag):
    if type(tag) is bs4.element.NavigableString:
      if tag.string == u'\n': return
      return self.book.append(NavigableString(tag))
    if type(tag) is bs4.element.Tag:
      if tag.string == u'\n': return
      if tag.name == "h2":
        if tag.string == "Exercises":
          return self.book.append(ExerciseHeader())
        return self.book.append(Heading2(tag))
      if tag.name == "h3":
        return self.book.append(Heading3(tag))
      if tag.has_key("class"):
        for grab in list(self.grabbers):
          if grab(tag, self):
            return
    self.book.append(NotTag(tag)) # Catch all that don't match


############ BookElements ####################################


def addGrabber(BookElementClass):
  # Class decorator to automatically add grabber to builder
  def grabber(tag, bookBuilder):
    if BookElementClass.matchStr in tag['class']:
      bookBuilder.book.append(BookElementClass(tag))
      return True
    return False
  bookElementGrabbers.append(grabber)
  return BookElementClass

class BookElement(object):
  matchStr = "Non Matching"
  def __init__(self, tag): self.tag = tag
  def tagname(self): 
    return "\n[" + self.__class__.__name__ + "]\n"
  def __repr__(self): 
    return self.tagname() + repr(self.tag)
  def adoc(self):
    # Produce Asciidoc output for this element
    return repr(self.tag.get_text())

class Paragraph(BookElement):
  matchStr = "MsoNormal"
  def grabber(tag, bookBuilder):
    if Paragraph.matchStr in tag['class']:
      if len(tag.get_text().strip()):
        bookBuilder.book.append(Paragraph(tag))
      return True
    return False
  bookElementGrabbers.append(grabber)
  def adoc(self): 
    return "- " + repr(self.tag.get_text())


def testForCodeNumber(tag):
  return  type(tag) is bs4.element.Tag and \
          tag.name == "span" and \
          tag.has_key("class") and \
          "CodeNumber" in tag["class"]

class Code(BookElement):
  matchStr = "Code"
  def grabber(tag, bookBuilder):
    if Code.matchStr in tag['class']:
      if any(map(testForCodeNumber, tag)):
        bookBuilder.book.append(Example(tag))
        bookBuilder.grabbers.insert(0, exampleGrabber)
      else:
        bookBuilder.book.append(CodeFragment(tag))
        bookBuilder.grabbers.insert(0, codeFragmentGrabber)
      return True
    return False
  bookElementGrabbers.append(grabber)

def exampleGrabber(tag, bookBuilder):
  if Code.matchStr in tag['class']:
    if any(map(testForCodeNumber, tag)):
      bookBuilder.book[-1].lines.append(tag)
    return True
  else:
    bookBuilder.grabbers.pop(0) # Remove the exampleGrabber
    return False

class Example(BookElement):
  """
  Single contiguous block of code, appears a line-numbered example in the book.
  Stored without line numbers, xxx method will output with line numbers.
  """
  ltrim = 6
  def __init__(self, tag):
    super(Example,self).__init__(tag)
    self.lines = [tag]
    self.finished = ""

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
    return """[source,scala]
--------------------------------------""" + \
    self.finish() + \
    "--------------------------------------"

def codeFragmentGrabber(tag, bookBuilder):
  if Code.matchStr in tag['class']:
    if not any(map(testForCodeNumber, tag)):
      bookBuilder.book[-1].lines.append(tag)
    return True
  else:
    bookBuilder.grabbers.pop(0) # Remove the codeFragmentGrabber
    return False

class CodeFragment(Example):
  """
  Un-numbered text that appears in code font in the book, 
  as a standalone paragraph.
  """
  ltrim = 2
  def adoc(self):
    return "*+" + "\n".join(self.finish()) + "+*"

class ExerciseHeader(BookElement):
  matchStr = "Exercises"
  def __init__(self):
    super(ExerciseHeader,self).__init__(">>>>> Exercises <<<<<<<<")
  def __repr__(self): return "\n[>>>>> Exercises <<<<<<<<]"

@addGrabber
class Exercise(BookElement):
  matchStr = "Exercise"

@addGrabber
class Quote(BookElement):
  matchStr = "MsoQuote"

class NavigableString(BookElement): pass
class NotTag(BookElement): pass
class Heading2(BookElement): pass
class Heading3(BookElement): pass

@addGrabber
class SolnsLink(BookElement):
  matchStr = "SolnsLink"

@addGrabber
class Bullet(BookElement):
  matchStr = "Bulleted"
  def adoc(self): 
    return "  * " + repr(self.tag.get_text())

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
  bookElementGrabbers.append(grabber)

  @staticmethod
  def subsequentGrabber(tag, bookBuilder):
    bookBuilder.book[-1].items.append(tag)
    if "MsoListParagraphCxSpMiddle" in tag['class']:
      return True
    if "MsoListParagraphCxSpLast" in tag['class']:
      bookBuilder.grabbers.pop(0) # Remove the subsequentGrabber
      return True
    assert False, "bullet points out of synch"

  def finish(self, ltrim = 6):
    if self.finished: return self.finished
    result = ""
    for ln in self.items:
      cleanedLine = clean(ln.get_text())
      cleanedLine = cleanedLine[ltrim:]
      result += ". " + cleanedLine.strip() + "\n"
    self.finished = result.rstrip()
    return self.finished

  def __repr__(self):
    return self.tagname() + self.finish()

  def adoc(self):
    return self.finish()


####### End of BookElements ###################


class Chapter(object):

  def __init__(self, name, rawData):
    self.name = name
    # rawData = UnicodeDammit.detwingle(rawData).decode("utf8")
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
    # print >>file("Cleaned.txt", "w"), bookSource
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


if __name__ == "__main__":
  chapters = Chapter.chapterize(open("AtomicScalaCleaned.html", "rU").read())
  # test = chapters["Comprehensions"]
  # test = chapters["Functions as Objects"]
  # print test.header()
  # pprint(test.elements, trace)
  summarized = seminarSubset(chapters)
  for chap in summarized.values():
    print chap.header()
    for el in chap.elements:
      print el
      # if type(el) is Example or type(el) is CodeFragment:
      #   print el
  #print test.elements[25]
  # trace2 = file("_OutputTrace2.txt", "w")
  # for e in test.soup:
  #   print >>trace2, e
  # test.trace(file("_OutputTrace3.txt", "w"))
  # pprint(test.elements, file("Elements.txt", "w"))

  
# def selectCode(cand):
#   return (type(cand) is bs4.element.Tag and
#     cand.has_key("class") and
#     "CodeChar" in cand['class'] and
#     len(cand.get_text()) > 4)


# class Exercise(object):

#   def __init__(self, chapter, soup):
#     self.chapter = chapter
#     self.soup = soup
#     # Remove funky spaces:
#     self.soup.find("span", {"style":'font:7.0pt "Times New Roman"'}).replace_with(" ")
#     exn = self.soup.contents[0]
#     if isinstance(exn, bs4.element.Tag):
#       exn = exn.get_text()
#     self.exerciseNumber = exn.split('.')[0] # Remove trailing period

#     self.rawDescription = list(itertools.ifilterfalse(selectCode, self.soup.contents))
#     self.description = ""
#     for desc in self.rawDescription:
#       if isinstance(desc, bs4.element.Tag):
#         self.description += filter(lambda x: x in string.printable, desc.get_text())
#       else:
#         self.description += filter(lambda x: x in string.printable, desc)

#     self.codes = list(itertools.ifilter(selectCode, self.soup.contents))

#   def __repr__(self): 
#     return repr(self.description) + repr(self.codes)
