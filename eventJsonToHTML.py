import json
import sys
import os

fileName = sys.argv[1]
if not os.path.isfile(fileName):
    raise Exception(fileName + " does not exist")

if not os.path.isdir("Marked events"):
    os.makedirs("Marked events")

jsonData=open(fileName).read()
eventsJson = json.loads(jsonData)

with open("Marked events/" + eventsJson['CaseName'] + ".html", 'w+') as f:
    f.seek(0)
    f.write("<html>\n")
    f.write("<head>\n")
    f.write(eventsJson['CaseName'] + "<br> \n")

    caseText = eventsJson['CaseText']
    for event in eventsJson['Events']:
        sentence = event['Sentence']
        eventPosition = caseText.find(sentence)
        eventLength = len(sentence)
        caseText = caseText[:eventPosition] + '<b>' + sentence + '</b>' + \
            caseText[eventPosition+eventLength:]
    f.write(caseText.replace("\n", "<br> \n"))
    f.write("</head>\n")
    f.write("</html>")
