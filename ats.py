import os
import requests

host = "ats.api.alexa.com"
endpoint = f"https://{host}"
method = "GET"
content_type = "application/json"
local_tz = "America/Los_Angeles"


def parse(content: dict) -> list:
    """
    Convert the response of AWS to a simple dictionary.
    """
    ranking = []

    entries = content["Ats"]["Results"]["Result"]["Alexa"]["TopSites"]["Country"][
        "Sites"
    ]["Site"]

    for e in entries:
        ranking.append(f'{e["Country"]["Rank"]}:{e["DataUrl"]}')

    return ranking


def getSites(count=100, cc="US") -> list:

    canonical_uri = "/api"
    canonical_querystring = "Action=Topsites&Output=json"
    canonical_querystring += "&" + f"Count={count}"
    canonical_querystring += "&" + f"CountryCode={cc}"
    canonical_querystring += "&" + "ResponseGroup=Country"
    canonical_querystring += "&" + "Start=1"

    headers = {
        "Accept": "application/json",
        "Content-Type": content_type,
        "x-api-key": os.environ.get("ATS_KEY"),
    }

    request_url = f"{endpoint}{canonical_uri}?{canonical_querystring}"
    r = requests.get(request_url, headers=headers)

    print(r.status_code)
    if r.status_code == 200:
        return parse(r.json())
    else:
        print(r.text)
        return []
