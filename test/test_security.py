import os
import sys
import json

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from securitytxt import parseResponse

def test_parseResponse():
    f = open("fixtures/example2-security.txt", "r")
    contents = f.read()
    f.close()

    actual = parseResponse({}, contents, "", "", 200)

    print(json.dumps(actual, indent=2))

test_parseResponse()
