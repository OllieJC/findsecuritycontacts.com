import os
import requests
import boto3
import botocore
import json
import pytz

from datetime import datetime, timedelta

utc = pytz.UTC

s3 = boto3.client("s3")
s3r = boto3.resource("s3")

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

    print(f"Running getSitesWithStart, {start} : {count} : {cc}")

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

    # check for s3://gotsecuritytxt.com/api/ats/{cc}/{count}-sites.json
    # if sites is less than one month old, use that, else, get/set an updated list

    bucket = "gotsecuritytxt.com"
    key = f"api/ats/{cc}/{count}-sites.json"
    past = utc.localize(datetime.now() - timedelta(days=30))

    valid = False

    try:
        head = s3.head_object(Bucket=bucket, Key=key)
        print(f"Found {key}, checking if valid: {head['LastModified']}")
        if "json" in head["ContentType"]:
            if head["LastModified"] >= past:
                print(f"{key} is still valid!")
                valid = True
            else:
                print(f"{key} is no longer valid...")
        else:
            print(f"Weird content type found ({head['ContentType']}) so skipping")
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] != "404":
            # Something else has gone wrong.
            raise

    s3Obj = s3r.Object(bucket, key)
    results = []

    if not valid:
        start = 1

        for i in range(int(count / AWS_MAX_COUNT)):
            results.extend(getSitesWithStart(start, AWS_MAX_COUNT, cc))
            start += AWS_MAX_COUNT

        results.extend(getSitesWithStart(start, count % AWS_MAX_COUNT, cc))
        s3Obj.put(
            Body=json.dumps(results).encode("utf-8"), ContentType="application/json"
        )
        print(f"{key} setting results: {len(results)}")
    else:
        body_str = s3Obj.get()["Body"].read().decode()
        results = json.loads(body_str)
        print(f"{key} loaded results: {len(results)}")

    return results
