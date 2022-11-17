import os
import sys
import dns
import dns.resolver
import requests
import ipaddress
import time
import json
import random
import urllib
import backoff
import re
import html
import httpx
import ssl

from urllib3.util import connection

from json_logger import log
from socket_checker import socket_check

NAMESERVERS = os.getenv("NAMESERVERS", default="").split(";")
DNS_TIMEOUT = int(os.getenv("DNS_TIMEOUT", "5"))
SOCKET_TIMEOUT = int(os.getenv("SOCKET_TIMEOUT", "5"))
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "5"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))
HTTP_USER_AGENT = os.getenv("HTTP_USER_AGENT", "findsecuritycontacts.com")
ALLOW_INTERNAL_IP = int(os.getenv("ALLOW_INTERNAL_IP", "0"))
CUSTOM_CIPHER_ADDITION = os.getenv("CUSTOM_CIPHER_ADDITION", ":HIGH:!DH:!aNULL")
CUSTOM_CIPHER_SET = os.getenv("CUSTOM_CIPHER_SET", "")

REDIRECT_REGEX = (
    r"(?:window\.location\.(?:href|replace)\s*?[=\(]\s*?|"
    + "http-equiv\s*?=\s*?['\"]?refresh.*?content\s*?=\s*?)"
    + "['\"](?:.*?\;)?(?:\s+)?(?:url\s*?=\s*?)?(?P<redirect>.+?)['\"]"
)

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

if CUSTOM_CIPHER_ADDITION:
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += CUSTOM_CIPHER_ADDITION
    CUSTOM_CIPHER_SET = requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS
elif CUSTOM_CIPHER_SET:
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = CUSTOM_CIPHER_SET
try:
    requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS = (
        CUSTOM_CIPHER_SET
    )
except AttributeError:
    # no pyopenssl support used / needed / available
    pass


resolver = dns.resolver.Resolver()
if NAMESERVERS != [""]:
    resolver.nameservers = NAMESERVERS
resolver.lifetime = resolver.timeout = DNS_TIMEOUT

dns_responses = {}


def get_dns_responses() -> dict:
    return dns_responses


def add_dns_response(d, a=None, cname=None, txt=None):
    if d:
        if d not in dns_responses:
            dns_responses[d] = {
                "a_records": [],
                "cname_records": [],
                "txt_records": [],
                "time": 0,
            }

        if a is not None and a not in dns_responses[d]["a_records"]:
            dns_responses[d]["a_records"].append(a)

        if cname is not None and cname not in dns_responses[d]["cname_records"]:
            dns_responses[d]["cname_records"].append(cname)

        if txt is not None and txt not in dns_responses[d]["txt_records"]:
            if txt.startswith("\\"):
                txt = txt.strip("\\")

            if txt.startswith('"'):
                txt = txt.strip('"')

            if txt.startswith("'"):
                txt = txt.strip("'")

            dns_responses[d]["txt_records"].append(txt)

        dns_responses[d]["dns_resolve_time"] = time.time()

    return


def targetparse(target: str) -> urllib.parse.ParseResult:
    if target and type(target) == str:
        target = target.strip()
        if "://" not in target:
            target = f"null://{target}"
        o = urllib.parse.urlparse(target)
        if o.hostname is None:
            return None
        else:
            return o
    return None


def parse_ip(target: str) -> dict:
    res = {"ip": None, "type": None, "is_ip": False}
    try:
        ip = ipaddress.ip_address(target)
        ip_type = None
        if type(ip) == ipaddress.IPv4Address:
            ip_type = "IPv4"
        elif type(ip) == ipaddress.IPv6Address:
            ip_type = "IPv6"
        if ip_type is not None:
            res.update(
                {
                    "ip": target,
                    "type": ip_type,
                    "is_ip": True,
                    "is_private": ip.is_private,
                }
            )
    except Exception as e:
        log(error=e)
    return res


def get_address_tuple(source_address):
    if type(source_address) == tuple:
        host, port = source_address
    else:
        host = source_address
        port = 0

    o = targetparse(host)
    if o is None:
        return None
    host = o.hostname

    if o.port:
        port = o.port
    if port is None:
        port = 0

    resolve_hostname = True

    ip = parse_ip(host)
    if ip["is_ip"]:
        resolve_hostname = False
        if not ALLOW_INTERNAL_IP and ip["is_private"]:
            return None

    if resolve_hostname:
        if host in dns_responses:
            # if the existing DNS response is less than an hour old
            if dns_responses[host]["dns_resolve_time"] >= (time.time() - 3600):
                resolve_hostname = False

        if resolve_hostname:
            try:
                dns_result = resolver.resolve(host, "A")
                for dns_val_raw in dns_result:
                    dns_val = dns_val_raw.to_text()
                    add_dns_response(host, a=dns_val)
            except Exception as e:
                log(host, error=e)

            try:
                dns_result = resolver.resolve(host, "CNAME")
                for dns_val_raw in dns_result:
                    dns_val = dns_val_raw.to_text()
                    add_dns_response(host, cname=dns_val)
            except Exception as e:
                log(host, error=e)

            try:
                dns_result = resolver.resolve(host, "TXT")
                for dns_val_raw in dns_result:
                    dns_val = dns_val_raw.to_text()
                    add_dns_response(host, txt=dns_val)
            except Exception as e:
                log(host, error=e)

        if host in dns_responses and "a_records" in dns_responses[host]:
            if len(dns_responses[host]["a_records"]) > 0:
                host = random.choice(dns_responses[host]["a_records"])

    return (host, port)


_orig_urllib3_create_connection = connection.create_connection


def patched_urllib3_create_connection(address, *args, **kwargs):
    return _orig_urllib3_create_connection(get_address_tuple(address), *args, **kwargs)


connection.create_connection = patched_urllib3_create_connection


def get_http_security_txt(hostname: str, port: int = None) -> dict:
    url_formats = {
        "https_well-known": "https://{0}/.well-known/security.txt",
        "https_root": "https://{0}/security.txt",
        "http_well-known": "http://{0}/.well-known/security.txt",
        "http_root": "http://{0}/security.txt",
    }

    res = {}

    for x in url_formats:
        log(hostname, f"get_http_security_txt: trying: {x}: {url_formats[x]}")
        res = getSecurityTxtFormat(hostname, port, url_formats[x])
        if "has_contact" in res and res["has_contact"]:
            res.update({"type": x})
            return res

    return {}


def parseResponse(
    headers: dict, body: str, url: str, status_code: int, http_version: str = None
) -> dict:
    has_contact = re.search("(?mi)^contact:", body) is not None

    res = {
        "url": url,
        "status_code": status_code,
        "has_contact": has_contact,
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
        "headers": {},
        "http_version": http_version,
    }

    for rh in headers:
        if rh in res["headers"]:
            res["headers"][rh] = f'{res["headers"][rh]};{str(headers[rh])}'
        else:
            res["headers"][rh] = str(headers[rh])

    if has_contact:
        res["full_text"] = html.escape(
            body.strip() if body and body is not None else ""
        )

        actual_body = str(res["full_text"])

        has_blocks = re.search("(?P<hyphens>\-\-+)", actual_body)
        if has_blocks:
            blocks = actual_body.split(has_blocks.groups("hyphens")[0])
            for block in blocks:
                if "contact:" in block.lower():
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


def getRedirectsFromReq(req, is_html_redirect: bool = False) -> dict:
    res = []
    counter = 0

    main_url = str(req.url)
    main_hv = req.http_version if "http_version" in dir(req) else "HTTP/1.X"

    for r in req.history:
        url = str(r.url)
        counter += 1
        rtype = "HTML" if counter == 1 and is_html_redirect else str(r.status_code)
        hv = r.http_version if "http_version" in dir(r) else "HTTP/1.X"
        res.append(
            {
                "type": rtype,
                "val": url,
                "https": (url.startswith("https://")),
                "http_version": hv,
            }
        )

    rtype = "HTML" if counter == 0 and is_html_redirect else str(req.status_code)
    res.append(
        {
            "type": rtype,
            "val": main_url,
            "https": (main_url.startswith("https://")),
            "http_version": main_hv,
        }
    )
    return res


def onlyHTTPSInRedirects(redirects):
    res = True
    for r in redirects:
        if not r["https"]:
            res = False
            break
    return res


@backoff.on_exception(
    backoff.expo,
    Exception,
    max_time=(HTTP_RETRIES * HTTP_TIMEOUT) + 1,
    max_tries=HTTP_RETRIES,
    giveup=lambda e: e.response is not None and e.response.status_code < 500,
)
def getSecurityTxtFormat(
    hostname: str,
    port: int,
    uf: str,
    url_override: str = None,
    html_redirect: bool = False,
    max_redirects: int = 5,
) -> dict:
    res = {}
    max_redirects -= 1
    if max_redirects <= 0:
        return res

    url = (
        url_override
        if url_override is not None
        else uf.format(hostname + ("" if port is None else f":{port}"))
    )

    try:
        headers = {"User-Agent": HTTP_USER_AGENT}

        req = None
        http1fb = False

        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.load_default_certs()
            client = httpx.Client(
                http2=True,
                verify=context,
                follow_redirects=True,
            )
            req = client.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        except Exception as e:
            log(hostname, message="httpx non-verify error", error=e)
            res["httpx_error"] = str(e)
            http1fb = True

        if http1fb:
            try:
                req = requests.get(
                    url, headers=headers, verify=True, timeout=HTTP_TIMEOUT
                )
            except requests.exceptions.SSLError as e:
                log(hostname, message="requests verify error", error=e)
                res["requests_https_failure"] = str(e)
                req = requests.get(
                    url, headers=headers, verify=False, timeout=HTTP_TIMEOUT
                )
            except Exception as e:
                log(hostname, message="requests error", error=e)
                res["requests_error"] = str(e)

        if req is None:
            return res

        res.update(
            parseResponse(
                req.headers,
                req.text,
                str(req.url),
                req.status_code,
                req.http_version if "http_version" in dir(req) else "HTTP/1.X",
            )
        )

        if not res["has_contact"] and req.text:
            redirect_res = re.search(REDIRECT_REGEX, req.text)
            if redirect_res is not None and redirect_res.group("redirect") is not None:
                possible_redirect = redirect_res.group("redirect").strip()
                if possible_redirect:
                    if possible_redirect.startswith("/"):
                        possible_redirect = "{0}://{1}{2}".format(
                            uf.split(":")[0], hostname, possible_redirect
                        )
                    if "://" in possible_redirect:
                        return getSecurityTxtFormat(
                            hostname, port, uf, url_override, True, max_redirects
                        )

        res["redirects"] = getRedirectsFromReq(req, html_redirect)
        res["valid_https"] = onlyHTTPSInRedirects(res["redirects"])
    except Exception as e:
        log(hostname, error=e)

    return res


def get_dnssecuritytxt(target: str = None) -> dict:
    res = {"security_contact": None, "security_policy": None, "matching_domain": None}

    if target:
        if target in dns_responses and "txt_records" in dns_responses[target]:
            for x in dns_responses[target]["txt_records"]:
                for y in ["security_contact", "security_policy"]:
                    if x.startswith(f"{y}="):
                        res["matching_domain"] = target
                        res[y] = x.replace(f"{y}=", "")

        if not target.startswith("_security") and res["matching_domain"] is None:
            sec_subdomain = f"_security.{target}"
            get_address_tuple(sec_subdomain)
            res = get_dnssecuritytxt(sec_subdomain)

    return res


def scan(target: str) -> dict:
    res = {"time": time.time(), "raw_target": target, "has_contact": False}

    parsed_target = targetparse(target)
    if parsed_target is None:
        res["error"] = "failed to parse target"
    else:
        res["target"] = parsed_target.hostname

    res["scan_type"] = "domain"

    ip = parse_ip(parsed_target.hostname)
    if ip["is_ip"]:
        res["scan_type"] = "ip"
        if not ALLOW_INTERNAL_IP and ip["is_private"]:
            res["error"] = "target is a private IP address"
            res["scan_type"] = None

    log(target, obj=res)

    resolved_target = None

    if res["scan_type"] == "domain":
        resolved_target, _ = get_address_tuple(
            (parsed_target.hostname, parsed_target.port)
        )
        res["domain_details"] = (
            dns_responses[parsed_target.hostname]
            if parsed_target.hostname in dns_responses
            else {}
        )

        res["dnssecuritytxt"] = get_dnssecuritytxt(parsed_target.hostname)

    elif scan_type == "ip":
        resolved_target = parsed_target.hostname
        res["domain_details"] = {}
        res["dnssecuritytxt"] = get_dnssecuritytxt()

    if resolved_target is None:
        return res

    if res["dnssecuritytxt"]["matching_domain"] is not None:
        res["has_contact"] = True

    scargs = {
        "target": parsed_target.hostname,
        "timeout": SOCKET_TIMEOUT,
        "custom_cipher_set": CUSTOM_CIPHER_SET,
    }
    if parsed_target.port is not None:
        scargs["ports"] = [parsed_target.port]
    scr = socket_check(**scargs)
    res.update(scr)

    if res["port"] is None:
        return res

    res["http_security_txt"] = get_http_security_txt(
        parsed_target.hostname, scr["port"]
    )

    if (
        "has_contact" in res["http_security_txt"]
        and res["http_security_txt"]["has_contact"]
    ):
        res["has_contact"] = True

    return res
