import requests
import time
import html
import re

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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
connect_timeout = 0.1
read_timeout = 3
retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    method_whitelist=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)


def getSecurityTxt(domain: str):
    https_error = False
    http_error = False
    
    res = None
    
    for x in url_formats:
        if not https_error and not http_error:
            res = getSecurityTxtFormat(domain, url_formats[x])

            if "error" in res and url_formats[x].startswith("https:"):
                https_error = True

            if "error" in res and url_formats[x].startswith("http:"):
                http_error = True

            if res["has_contact"]:
                res.update({"sectxt_type": x})
                break

    return res


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
    errorString = None
    
    try:
        headers = {"User-Agent": "python requests - gotsecuritytxt.com"}
        req = http.get(
            uf.format(domain), headers=headers, verify=True, timeout=(connect_timeout, read_timeout)
        )
        redirects = getRedirectsFromReq(req)

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
                    
                    if "://" in possible_redirect:
                        req2 = http.get(
                            possible_redirect,
                            headers=headers,
                            verify=True,
                            timeout=(connect_timeout, read_timeout),
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
    except requests.exceptions.SSLError as e:
        errorString = "TLS/SSL error"
    except requests.exceptions.RetryError as e:
        errorString = "Retry error"
    except requests.exceptions.Timeout as e:
        errorString = "Timeout error"
    except Exception as e:
        errorString = str(e)
        
    print("getSecurityTxtFormat:error:", errorString)
    pr = parseResponse({}, "", domain, "", 404)
    pr["error"] = errorString
    return pr


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
