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
redirect_value = (
    r"(?:window\.location\.(?:href|replace)\s*?[=\(]\s*?|"
    + "http-equiv\s*?=\s*?['\"]?refresh.*?content\s*?=\s*?)"
    + "['\"](?:.*?\;)?(?:\s+)?(?:url\s*?=\s*?)?(?P<redirect>.+?)['\"]"
)
request_timeout = 2


def getSecurityTxt(domain: str):
    for x in url_formats:
        res = getSecurityTxtFormat(domain, url_formats[x])
        if res["has_contact"]:
            res.update({"sectxt_type": x})
            return res

    return parseResponse({}, "", domain, "", 404)


def getRedirectsFromReq(req, is_html_redirect=False):
    res = []
    counter = 0

    for r in req.history:
        counter += 1
        rtype = str(r.status_code)
        if counter == 1 and is_html_redirect:
            rtype = "HTML"
        res.append({"type": rtype, "val": r.url, "https": ("https" in r.url)})

    reqtype = str(req.status_code)
    if counter == 0 and is_html_redirect:
        reqtype = "HTML"
    res.append({"type": reqtype, "val": req.url, "https": ("https" in req.url)})
    return res


def onlyHTTPSInRedirects(redirects):
    res = True
    for r in redirects:
        if not r["https"]:
            res = False
            break
    return res


def getSecurityTxtFormat(domain: str, uf: str):
    try:
        headers = {"User-Agent": "python requests - gotsecuritytxt.com"}
        req = requests.get(
            uf.format(domain), headers=headers, verify=True, timeout=request_timeout
        )
        redirects = getRedirectsFromReq(req)
        # print("----")
        # print(req.headers, req.text, domain, req.url, req.status_code)

        pr = parseResponse(req.headers, req.text, domain, req.url, req.status_code)

        if not pr["has_contact"] and req.text:
            redirect_res = re.search(redirect_value, req.text)
            if redirect_res is not None:
                possible_redirect = redirect_res.group("redirect").strip()
                if possible_redirect:
                    if possible_redirect.startswith("/"):
                        possible_redirect = "{0}://{1}{2}".format(
                            uf.split(":")[0], domain, possible_redirect
                        )

                    req2 = requests.get(
                        possible_redirect,
                        headers=headers,
                        verify=True,
                        timeout=request_timeout,
                    )
                    pr2 = parseResponse(
                        req2.headers, req2.text, domain, req2.url, req2.status_code
                    )

                    if pr2["has_contact"]:
                        redirects = redirects + getRedirectsFromReq(req2, True)
                        pr2["redirects"] = redirects
                        pr2["valid_https"] = onlyHTTPSInRedirects(redirects)
                        return pr2

        pr["redirects"] = redirects
        pr["valid_https"] = onlyHTTPSInRedirects(redirects)
        return pr
    except Exception as e:
        print("getSecurityTxtFormat:error:", e)
        return parseResponse({}, "", domain, "", 404)


def parseResponse(headers: dict, body: str, domain: str, url: str, status_code: int):
    has_contact = re.search("(?mi)^contact:", body) is not None

    res = {
        "domain": domain,
        "url": url,
        "status_code": status_code,
        "has_contact": has_contact,
        "content_type": html.escape(headers["Content-Type"])
        if "Content-Type" in headers
        else "",
        "valid_https": False,
        "valid_content_type": (
            "Content-Type" in headers
            and headers["Content-Type"].startswith("text/plain")
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
        "redirects": [],
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
                r"^(?: +)?(?P<key>[A-Za-z\-]+)\:\s?(?P<value>.+?)$",
                stripped_line,
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
