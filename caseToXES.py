import os
import sys
import ntpath
import json
import spacy
from datetime import datetime

import comprehend
import extractDateEvents

OBJECTS = ["dobj", "attr", "oprd", "obj", "acomp"]

# checks whether a token has a neg as a child and returns the token text with the negation text in front
# otherwise returns only the token text
def checkNeg(token):
    for child in token.children:
        if child.dep_ == "neg":
            return child.text + " " + token.text
    return token.text

# selects a label for a sentence consisting of subject - verb - object
def selectLabel(nlp, sentence):
    doc = nlp(sentence)
    subject = ""
    verb = ""
    _object = ""
    for token in doc:
        if token.dep_ == "ROOT":
            verb = checkNeg(token)
            for child in token.children:
                if child.dep_ == "nsubj" or child.dep_ == "nsubjpass":
                    subject += " " + checkNeg(child)
                # if the subject is in passive form add the auxiliary word: "Kennedy _was_ killed"
                if child.dep_ == "auxpass":
                    verb = checkNeg(child) + " " + verb
                # if the subject is a causal subject add the complete clause as subject
                if child.dep_ == "csubj" or child.dep_ == "csubjpass":
                    for left in child.lefts:
                        subject = checkNeg(left)
                    subject += " " + checkNeg(child)
                    for right in child.rights:
                        subject = subject + " " + checkNeg(right)
                # if the object is a clausal complement ("I am sure _that he did it_") or an open clausal complement 
                # take the complete clause as object
                if child.dep_ == "ccomp" or child.dep_ == "xcomp":
                    for left in child.lefts:
                        _object = checkNeg(left)
                    _object += " " + checkNeg(child)
                    for right in child.rights:
                        _object = _object + " " + checkNeg(right) 

                if child.dep_ in OBJECTS:
                    _object = _object + checkNeg(child)
    return "" + subject.strip().lower() + " - " + verb.lower() + " - " + _object.lower()

# takes a date in form of a string and converts it to datetime object
def getDatetime(date):
    try:
        # it can be either day month year
        dt = datetime.strptime(date, '%d %B %Y')
    except ValueError:
        try:
            # or only year
            dt = datetime.strptime(date, '%Y')
        except ValueError:
            # or month year
            try:
                dt = datetime.strptime(date, '%B %Y')
            except ValueError:
                # TODO: relative time descriptions "Two days later"
                return None
    return dt

# remove newlines and replace quotes in sentences
def cleanString(_string):
    _string = _string.replace('\n', '')
    _string = _string.replace('"', "'")
    _string = _string.strip()
    _string = _string.encode('unicode-escape').decode('utf-8')
    return _string

# return an xes trace for a given case - makes use of spacy functionality to find event labels
def caseToXES(caseJson, nlp):
    # start a trace
    XES = "\n<trace>\n"
    # name of the trace is the name of the case
    XES += '\t<string key="concept:name" value="' + caseJson['CaseName'] + '"/>\n' 
    for event in caseJson['Events']:
        XES += "\n<event>\n"
        # use spacy functionality to find an event label out of the sentence
        XES += '\t<string key="concept:name" value="' + selectLabel(nlp, cleanString(event['Sentence'])) + '"/>\n' 
        # the date needs to be converted to the right format
        # keep also the date object for sorting events
        event['Dateobject'] = getDatetime(event['Date'])
        if event['Dateobject'] is not None:
            XES += '\t<date key="time:timestamp" value="' + event['Dateobject'].strftime("%Y-%m-%dT00:00:00.000+01:00") + '"/>\n'
        # keep the sentence as XES attribute
        XES += '\t<string key="sentence" value="' + cleanString(event['Sentence']) + '"/>\n'
        XES += "</event>\n"
    XES += "</trace>\n"
    return XES

# ------- Start of main script ----------

fileName = sys.argv[1]
xesFile = sys.argv[2] # case is added as a trace to this xes
caseName = ntpath.basename(fileName)[:-4] # remove .txt

if not os.path.isfile(fileName):
    raise Exception(fileName + " does not exist")
# run through comprehend
print("Sending case to AWS comprehend")
c = comprehend.ComprehendCaseEntities(fileName, caseName, 'eu-west-1', 'en')
caseJson = c.comprehend()
print("Done")
print("Extracting sentences and dates")
# extract sentences based on date entities
ed = extractDateEvents.EventDetector(caseJson)
caseJson = ed.detectEvents()
print("Done")
print("Loading spacy")
# load spacy
nlp = spacy.load('en')
print("Done")

with open(xesFile, mode='a', encoding='utf-8') as f:
    print("Saving XES")
    f.write(caseToXES(caseJson, nlp))
