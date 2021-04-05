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
        headers = {"User-Agent": "python requests - gotsecuritytxt.com"}
        req = requests.get(uf.format(domain), headers=headers, verify=True, timeout=2)
        pr = parseResponse(req.headers, req.text, domain, req.url, req.status_code)
        return pr
    except:
        return parseResponse({}, "", domain, "", 404)


def parseResponse(headers: dict, body: str, domain: str, url: str, status_code: int):
    has_contact = re.search("(?mi)^contact:", body) is not None

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

        actual_body = str(res["full_text"])

        has_blocks = re.search("(?P<hyphens>\-\-+)", actual_body)
        if has_blocks:
            blocks = actual_body.split(has_blocks.groups("hyphens")[0])
            for block in blocks:
                if "contact:" in block:
                    actual_body = block
                    break

        res["min_text"] = ""

        for line in actual_body.split("\n"):
            stripped_line = line.strip()
            line_search = re.search(
                r"^(?: +)?(?P<key>[A-Za-z\-]+)\:\s?(?P<value>.+?)$", stripped_line,
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
                    if x.lower() in line_search.group("key").lower():

                        if x == "Acknowledgments":
                            x = "Acknowledgements"

                        val = line_search.group("value")

                        res["min_text"] += f"{x}: {val}\n"

                        if type(res["items"][x]) == list:
                            res["items"][x].append(val)
                        else:
                            res["items"][x] = val

    return res
