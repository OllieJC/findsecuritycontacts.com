import os
import requests

host = "ats.api.alexa.com"
endpoint = f"https://{host}"
method = "GET"
content_type = "application/json"
local_tz = "America/Los_Angeles"
AWS_MAX_COUNT = 100


def parse(content: dict) -> list:
    """
    Convert the response of AWS to a simple dictionary.
    """
    ranking = []

    try:
        entries = content["Ats"]["Results"]["Result"]["Alexa"]["TopSites"]["Country"][
            "Sites"
        ]["Site"]

        for e in entries:
            ranking.append(f'{e["Country"]["Rank"]}:{e["DataUrl"]}')
    except Exception as e:
        print(e)

    return ranking


def getSitesWithStart(start, count, cc) -> list:

    canonical_uri = "/api"
    canonical_querystring = "Action=Topsites&Output=json"
    canonical_querystring += "&" + f"Count={count}"
    canonical_querystring += "&" + f"CountryCode={cc}"
    canonical_querystring += "&" + "ResponseGroup=Country"
    canonical_querystring += "&" + f"Start={start}"

    headers = {
        "Accept": "application/json",
        "Content-Type": content_type,
        "x-api-key": os.environ.get("ATS_KEY"),
    }

    request_url = f"{endpoint}{canonical_uri}?{canonical_querystring}"
    r = requests.get(request_url, headers=headers)

    if r.status_code == 200:
        return parse(r.json())
    else:
        print(r.text)
        return []


def getSites(count=100, cc="US"):
    result = []

    start = 1

    for i in range(int(count / AWS_MAX_COUNT)):
        result.extend(getSitesWithStart(start, AWS_MAX_COUNT, cc))
        start += AWS_MAX_COUNT

    result.extend(getSitesWithStart(start, count % AWS_MAX_COUNT, cc))

    return result
