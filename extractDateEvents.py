import json
import sys
import os

# takes a case with aws comprehend entities in json
# produces a json containing a list of events
# an event is a sentence containing a date entity - where the date entity is not in a part of the sentence enclosed by parenthesis
# e.g. "The judges oppinion is abc (see reference xyz from 10 June 2000)"
class EventDetector():
    def __init__(self, caseJson):
        if 'CaseName' not in caseJson \
            or 'CaseText' not in caseJson \
            or 'Entities' not in caseJson:
            raise Exception('wrong json format!')

        self._caseJson = caseJson

    # produces a json containing all events of the case
    def detectEvents(self):
        # start the return json
        eventsJson = dict()
        eventsJson['CaseName'] = self._caseJson['CaseName']
        eventsJson['CaseText'] = self._caseJson['CaseText']
        # start a list of detected events
        events = []
        eventIdCounter = 0
        for entity in self._caseJson['Entities']:
            if entity['Type'] == "DATE":
                event = dict()
                # use a running counter for the eventId
                eventIdCounter += 1
                event['Id'] = eventIdCounter
                # the date of the new event is the text where 
                # aws comprehend detected the entity 
                event['Date'] = entity['Text']
                # save the sentence that contains the date
                event['Sentence'] = self._extractSentence(entity['BeginOffset'], entity['EndOffset'])
                # a date surrounded by parenthesis is not an event
                # sentences must contain at least 15 characters to be considered events
                if event['Sentence'] is None or len(event['Sentence']) < 15:
                    continue
                # remove everything enclosed in parenthesis since this wont be relevant for the event
                event['Sentence'] = self._stripParenthesis(event['Sentence'])
                events.append(event)

        eventsJson['Events'] = events
        return eventsJson

    # extracts the sentence the marked term (the date) is part of
    # out of the current case text
    # if the date is part of a sentence enclosed by parenthesis this function returns None
    # because these are not events
    def _extractSentence(self, beginOffset, endOffset):
        caseText = self._caseJson['CaseText']
        # expand the sentence into both directions until a stop character is found
        expandLeft = True
        expandRight = True
        # count parenthesis since dates in parenthesis dont count as events
        openBraceCnt = 0
        closeBraceCnt = 0
        
        while expandLeft or expandRight:
            if expandLeft:
                if beginOffset == 0:
                    expandLeft = False
                else:
                    beginOffset -= 1
                # count the braces to determin if date is in eclosed part of sentence
                if caseText[beginOffset] == ")":
                    closeBraceCnt += 1
                if caseText[beginOffset] == "(":
                    openBraceCnt += 1

                if self._isStopChar(caseText[beginOffset], beginOffset):
                    beginOffset += 1
                    expandLeft = False

            if expandRight:
                if self._isStopChar(caseText[endOffset], endOffset):
                    expandRight = False
                    continue
                endOffset += 1
        # if there is an uneven number of braces on the left side of the date then it must be enclosed by braces
        if (openBraceCnt - closeBraceCnt) != 0:
            return None
        return caseText[beginOffset:endOffset] + "."

    # check whether a character in the text is a character marking the start/end of a sentence
    def _isStopChar(self, char, position):
        if char == ':' or char == ';' or position < 3:
            return True

        if not char == '.':
            return False 

        caseText = self._caseJson['CaseText']

        # enumeration counts as period
        if caseText[position-1] in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            return True
        # check for abbreviation or triple dots
        if caseText[position-2:position] == 'no' or \
           caseText[position-3:position] == 'nos' or \
           caseText[position-2] == ' ' or \
           caseText[position-1] == '.' or \
           caseText[position-2] == '.':
           return False

        if position+2 < len(caseText)-1:
            if caseText[position+1] == '.' or caseText[position+2] == '.':
                return False
            
        return True

    # remove text enclosed by parenthesis from a sentence
    # also removes the parenthesis
    def _stripParenthesis(self, sentence):
        # keep positions of the openeing and closing braces
        openIndex = -1
        closeIndex = -1
        charIndex = 0
        # go thorugh the sentence character by character
        for char in sentence:
            if char == "(":
                openIndex = charIndex
            if char == ")":
                if openIndex > -1:
                    closeIndex = charIndex
                if openIndex > -1 and openIndex < closeIndex:
                    # cut out the text between parenthesis (including parenthesis)
                    sentence = sentence[:openIndex] + sentence[closeIndex+1:]
                    # reset counters
                    charIndex -= closeIndex - openIndex + 1
                    openIndex = -1
                    closeIndex = -1
            charIndex += 1
        return sentence


if __name__ == "__main__":
    fileName = sys.argv[1]
    if not os.path.isfile(fileName):
        raise Exception(fileName + " does not exist")

    if not os.path.isdir("Events Json"):
        os.makedirs("Events Json")

    jsonData=open(fileName).read()
    caseJson = json.loads(jsonData)

    ed = EventDetector(caseJson)

    with open("Events Json/events-" + caseJson['CaseName'] + ".json", 'w+') as f:
        f.seek(0)
        f.write(json.dumps(ed.detectEvents(), indent=4))

