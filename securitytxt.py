import requests
import time
import html
import re


url_formats = {
    1: "https://{0}/.well-known/security.txt",
    2: "https://{0}/security.txt",
    3: "http://{0}/.well-known/security.txt",
    4: "http://{0}/security.txt",
}


def getSecurityTxt(domain: str):
    res = {}

    for x in url_formats:
        res = getSecurityTxtFormat(domain, url_formats[x])
        res.update({"sectxt_type": x})
        if res["has_contact"]:
            break

    return res


def getSecurityTxtFormat(domain: str, uf: str):
    try:
        req = requests.get(uf.format(domain), verify=True, timeout=2)
        pr = parseResponse(req.headers, req.text, domain, req.url, req.status_code)
        return pr
    except:
        return parseResponse({}, "", domain, "", 404)


def parseResponse(headers: dict, body: str, domain: str, url: str, status_code: int):
    lower_body = body.lower().strip()

    has_contact = "contact:" in lower_body

    res = {
        "domain": domain,
        "url": url,
        "status_code": status_code,
        "has_contact": has_contact,
        "valid_content_type": (
            "Content-Type" in headers and headers["Content-Type"] == "text/plain"
        ),
        "full_text": "",
        "min_text": "",
        "items": {
            "Acknowledgements": [],
            "Canonical": [],
            "Contact": [],
            "Encryption": [],
            "Preferred-Languages": "",
            "Expires": "",
            "Hiring": [],
            "Policy": [],
        },
    }

    if has_contact:
        res["full_text"] = html.escape(body.strip())

        actual_body = str(lower_body)

        has_blocks = re.search("(?P<hyphens>\-\-+)", actual_body)
        if has_blocks:
            blocks = actual_body.split(has_blocks.groups("hyphens")[0])
            for block in blocks:
                if "contact:" in block:
                    actual_body = block
                    break

        actual_body = html.escape(actual_body.strip())

        res["min_text"] = ""

        for line in actual_body.split("\n"):
            stripped_line = line.strip()
            line_search = re.search(
                r"^(?: +)?(?P<key>[a-z\-]+)\:\s?(?P<value>.+?)$", stripped_line,
            )
            if line_search:
                for x in [
                    "Acknowledgements",
                    "Acknowledgments",
                    "Canonical",
                    "Contact",
                    "Encryption",
                    "Preferred-Languages",
                    "Expires",
                    "Hiring",
                    "Policy",
                ]:
                    if x.lower() in line_search.group("key"):

                        if x == "Acknowledgments":
                            x = "Acknowledgements"

                        res["min_text"] += f"{stripped_line}\n"
                        if type(res["items"][x]) == list:
                            res["items"][x].append(line_search.group("value"))
                        else:
                            res["items"][x] = line_search.group("value")

    return res
