import json
import sys
import os
import boto3

# reads in a case file, breaks it up into pieces of under 5000 bytes
# runs it through aws comprehend
# produces a json including the casetext and all detected entities
class ComprehendCaseEntities():
    def __init__(self, fileName, caseName, awsregion, langCode):
        try:
            with open(fileName, encoding='utf-8') as f:
                caseText = f.read()
        except UnicodeDecodeError:
            with open(fileName) as f:
                caseText = f.read()
        self._caseName = caseName
        self._awsregion = awsregion
        self._language = langCode
        # --------- DO THIS MANUALLY FOR NOW -------------
        # skip everything before and including procedure and skip everything after "II. "
        # => only keep the procedure and the first part of the facts section which is "I. THE CIRCUMSTANCES OF THE CASE"
        #procedureIndex = caseText.find('\nPROCEDURE\n')
        #sectionTwoIndex = caseText.find('\nII. ', procedureIndex)
        #if sectionTwoIndex == -1:
        #    sectionTwoIndex = caseText.find('\nTHE LAW\n', procedureIndex)
        #if sectionTwoIndex == -1:
        #    sectionTwoIndex = caseText.find('\nRELEVANT DOMESTIC LAW\n', procedureIndex)
        #if procedureIndex == -1 or sectionTwoIndex == -1:
        #    raise Exception('No PROCEDURE or section "II. " in this file')
        #caseText = caseText[procedureIndex+9:sectionTwoIndex]
        self._caseText = caseText
        self._stringArray = self._4800bytesStringArray(caseText)
        
    # the case text broken up into strings of 5000 bytes
    def stringArray(self):
        return self._stringArray

    def caseText(self):
        return self._caseText

    def caseName(self):
        return self._caseName

    def caseJson(self):
        if hasattr(self, "_caseJson"):
            return self._caseJson
        else:
            raise Exception('No caseJson found. Run comprehend first!')

    # sends all elements of stringArray to aws comprehend
    # returns a json representing the whole case text
    def comprehend(self):
        if len(self._stringArray) == 0:
            raise Exception('Empty stringArray!')
        
        comprehend = boto3.client(service_name='comprehend', region_name=self._awsregion)
        # start a Json including the case name, empty case text and empty list of entities
        caseJson = self._startCaseJson()

        segmentCounter = 1
        totSegments = len(self._stringArray)
        for segment in self._stringArray:
            if len(segment) == 0: continue

            print('Sending segment (' + str(segmentCounter) +
                '/' + str(totSegments) + ') to aws comprehend.')
            segmentCounter += 1

            compResult = comprehend.detect_entities(Text=segment, LanguageCode=self._language)
            self._appendSegment(caseJson, segment, compResult['Entities'])

        # keep the json
        self._caseJson = caseJson
        return caseJson

    # break up a text into a string array each containing at maximum 5000 bytes
    # the last char of each element must be a "." or the last char of the text
    # (to not break in the middle of a sentence)
    def _4800bytesStringArray(self, text):
        currentSegment = ''
        stringArray = []
        while len(text) != 0:
            # add the next sentence
            nextSentence = self._getNextSentence(text)
            currentSegment += nextSentence
            # if there is still room for more
            if sys.getsizeof(currentSegment) < 4800:
                # remove the sentence from the remaining text
                text = text[len(nextSentence):]
            # if the element is full
            else:
                # remove the last sentence
                currentSegment = currentSegment[:-len(nextSentence)]
                print("Current segment size:" + str(sys.getsizeof(currentSegment)))
                stringArray.append(currentSegment)
                currentSegment = ''
        # fill the last element with the remaining text
        if len(currentSegment) > 0:
            stringArray.append(currentSegment)
        return stringArray

    # returns the substring from the start to the next "." in the text 
    # (including the colon)
    # if there is no "." the whole text is returned
    def _getNextSentence(self, text):
        colonIndex = text.find('.')
        if colonIndex == -1: return text
        return text[:colonIndex+1]

    # intitializes the output json with case name, empty case text and empty list of entities
    def _startCaseJson(self):
        caseJson = dict()

        caseJson['CaseName'] = self._caseName
        caseJson['CaseText'] = ''
        caseJson['Entities'] = []

        return caseJson
    
    # appends the segment and entities list to the caseJson
    def _appendSegment(self, caseJson, segment, entities):
        for entity in entities:
            # adjust the character offets
            caseTextlen = len(caseJson['CaseText'])
            entity['BeginOffset'] += caseTextlen
            entity['EndOffset'] += caseTextlen

            caseJson['Entities'].append(entity)

        caseJson['CaseText'] += segment

if __name__ == "__main__":
    caseName = sys.argv[1]
    fileName = "Cases/" + caseName + ".txt"

    if not os.path.isdir("Cases"):
        os.makedirs("Cases")

    if not os.path.isfile(fileName):
        raise Exception(fileName + " does not exist")

    if not os.path.isdir("Comprehend Json"):
        os.makedirs("Comprehend Json")
    c = ComprehendCaseEntities(fileName, caseName, 'eu-west-1', 'en')
    with open("Comprehend Json/comprehend-" + caseName + ".json", 'w+') as f:
        f.seek(0)
        f.write(json.dumps(c.comprehend(), indent=4))
