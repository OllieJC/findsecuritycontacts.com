import shutil
import json
import os
import re
import sys

import ats

from multiprocessing import Pool

from jinja_helper import renderTemplate
from target import scan


dist: str = "dist/"
top_sites: str = "dist/top/"
gen_sites: str = "dist/gen/"
api: str = "dist/api/"
well_known: str = "dist/.well-known"


def setupDist():
    try:
        shutil.rmtree(dist)
    except Exception as e:
        print(e)

    os.mkdir(dist)
    os.mkdir(top_sites)
    os.mkdir(gen_sites)
    os.mkdir(api)
    os.mkdir(well_known)

    shutil.copytree("assets", f"{dist}assets", dirs_exist_ok=True)


def genSecurityTxtForDomain(
    x: str, topOrGen: str = top_sites, return_body: bool = False
) -> dict:
    details = scan(x)
    result = renderTemplate(
        "domain.html",
        {
            # "res_json": json.dumps(details, default=str, indent=2),
            "res": details,
            "dest_domain": details["target"] if "target" in details else "",
        },
    )

    if return_body:
        return result
    else:
        f = open(f"{topOrGen}{x}", "w")
        f.write(result)
        f.close()
        return details


def genStaticFiles(results: list, us_domains_dict: dict, gb_domains_dict: dict):

    us_results = []
    gb_results = []

    for r in results:
        if "target" in r and r["target"] in us_domains_dict:
            r["top_index"] = us_domains_dict[r["target"]]
            us_results.append(r)

        if "target" in r and r["target"] in gb_domains_dict:
            r["top_index"] = gb_domains_dict[r["target"]]
            gb_results.append(r)

    f = open(f"{dist}api/us.json", "w")
    json.dump(us_results, f, indent=2)
    f.close()

    f = open(f"{dist}api/gb.json", "w")
    json.dump(gb_results, f, indent=2)
    f.close()

    for x in [
        ["index.html", "top sites in United States", ["index.html", "us", "us.html"]],
        ["index.html", "valid top sites in United States", ["us-only-valid"]],
        ["index.html", "top sites in Great Britain", ["gb", "gb.html"]],
        ["index.html", "valid top sites in Great Britain", ["gb-only-valid"]],
        ["pending.html", "scanning"],
        ["gen-error.html", "error"],
        ["404.html", "not found"],
        ["error.html", "error"],
        ["query.html", "query", ["query", "query.html"]],
        ["security.txt", "", ["security.txt", ".well-known/security.txt"]],
        ["site.webmanifest", "", ["site.webmanifest", "manifest.json"]],
        ["robots.txt", ""],
    ]:
        params = {}
        if x[0] == "index.html":
            if len(results) == 0:
                continue

            if "us" in x[2] or "us-only-valid" in x[2]:
                total = len(us_results)
                has_contacts = sum(
                    1
                    for x in us_results
                    if (
                        "dnssecuritytxt" in x
                        and x["dnssecuritytxt"]["matching_domain"] is not None
                    )
                    or (
                        "http_security_txt" in x
                        and "has_contact" in x["http_security_txt"]
                        and x["http_security_txt"]["has_contact"]
                    )
                )
                no_contacts = total - has_contacts
                params = {
                    "country": "United States",
                    "results": us_results,
                    "total": total,
                    "has_contacts": has_contacts,
                    "no_contacts": no_contacts,
                    "country_short_code": "us",
                }
                if "us-only-valid" in x[2]:
                    params["only_valid"] = True

            if "gb" in x[2] or "gb-only-valid" in x[2]:
                total = len(gb_results)
                has_contacts = sum(
                    1
                    for x in gb_results
                    if (
                        "dnssecuritytxt" in x
                        and x["dnssecuritytxt"]["matching_domain"] is not None
                    )
                    or (
                        "http_security_txt" in x
                        and "has_contact" in x["http_security_txt"]
                        and x["http_security_txt"]["has_contact"]
                    )
                )
                no_contacts = total - has_contacts
                params = {
                    "country": "Great Britain",
                    "results": gb_results,
                    "total": total,
                    "has_contacts": has_contacts,
                    "no_contacts": no_contacts,
                    "country_short_code": "gb",
                }
                if "gb-only-valid" in x[2]:
                    params["only_valid"] = True

        if x[1]:
            params.update({"title": x[1]})
        result = renderTemplate(x[0], params)

        if len(x) == 2:
            paths = [x[0]]
        else:
            paths = x[2]

        for p in paths:
            f = open(f"{dist}{p}", "w")
            f.write(result)
            f.close()


def splitRankedDomain(x: str) -> dict:
    re_item = re.search("^(?P<num>.+?):(?P<val>.*)", x)
    num = int(re_item.group("num"))
    val = re_item.group("val")
    return {"rank": num, "domain": val}


if __name__ == "__main__":
    setupDist()
    lenArgs = len(sys.argv)

    if lenArgs == 2:
        domain = sys.argv[1]
        genSecurityTxtForDomain(domain, gen_sites)
    else:
        results = []
        us_domains_list = []
        gb_domains_list = []

        us_domains_dict = {}
        gb_domains_dict = {}

        if os.environ.get("GET_SEC_TXT", "false") == "true":
            us_domains_list = ats.getSites(250, "US")
            gb_domains_list = ats.getSites(250, "GB")

            domain_list = set()

            for x in us_domains_list:
                srd = splitRankedDomain(x)
                domain_list.add(srd["domain"])
                us_domains_dict[srd["domain"]] = srd["rank"]

            for x in gb_domains_list:
                srd = splitRankedDomain(x)
                domain_list.add(srd["domain"])
                gb_domains_dict[srd["domain"]] = srd["rank"]

            if len(domain_list) > 0:
                print("Got domain lists, counts:")
                print("Total -", len(domain_list))
                print("US -", len(us_domains_dict))
                print("GB -", len(gb_domains_dict))
            else:
                raise Exception("No domains")

            with Pool(int(os.environ.get("POOL_SIZE", "15"))) as p:
                results = p.map(genSecurityTxtForDomain, domain_list)

        genStaticFiles(results, us_domains_dict, gb_domains_dict)
