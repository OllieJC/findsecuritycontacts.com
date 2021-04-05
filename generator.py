from jinja_helper import renderTemplate
from securitytxt import getSecurityTxt
from multiprocessing import Pool
import shutil
import json
import os
import ats
import re
import sys


dist: str = "dist/"
top_sites: str = "dist/top/"
gen_sites: str = "dist/gen/"
well_known: str = "dist/.well-known"


def setupDist():
    try:
        shutil.rmtree(dist)
    except Exception as e:
        print(e)

    os.mkdir(dist)
    os.mkdir(top_sites)
    os.mkdir(gen_sites)
    os.mkdir(well_known)

    shutil.copytree("assets", f"{dist}assets", dirs_exist_ok=True)


def genSecurityTxtForDomain(
    x: str, topOrGen: str = top_sites, return_body: bool = False
) -> dict:
    print(f"Attempting to get security.txt for {x}")
    details = getSecurityTxt(x)

    result = renderTemplate("domain.html", {"res": details})

    if return_body:
        return result
    else:
        f = open(f"{topOrGen}{x}", "w")
        f.write(result)
        f.close()
        return details


def genStaticFiles(results: list, us_domains_list: list, gb_domains_list: list):

    us_results = []
    gb_results = []

    for r in results:
        for x in us_domains_list:
            srd = splitRankedDomain(x)
            if r["domain"] == srd["domain"]:
                y = dict(r)
                y.update({"top_index": srd["rank"]})
                us_results.append(y)

        for x in gb_domains_list:
            srd = splitRankedDomain(x)
            if r["domain"] == srd["domain"]:
                y = dict(r)
                y.update({"top_index": srd["rank"]})
                gb_results.append(y)

    for x in [
        ["index.html", ["index.html", "us", "us.html"]],
        ["index.html", ["gb", "gb.html"]],
        ["pending.html"],
        ["gen-error.html"],
        ["query.html", ["query", "query.html"]],
        ["security.txt", ["security.txt", ".well-known/security.txt"]],
        ["site.webmanifest", ["site.webmanifest", "manifest.json"]],
        ["robots.txt"],
    ]:
        params = {}
        if x[0] == "index.html":
            if len(results) == 0:
                continue

            if "us" in x[1]:
                total = len(us_results)
                has_contacts = sum(1 for x in us_results if x["has_contact"])
                no_contacts = total - has_contacts
                params = {
                    "country": "United States",
                    "results": us_results,
                    "total": total,
                    "has_contacts": has_contacts,
                    "no_contacts": no_contacts,
                }

            if "gb" in x[1]:
                total = len(gb_results)
                has_contacts = sum(1 for x in gb_results if x["has_contact"])
                no_contacts = total - has_contacts
                params = {
                    "country": "Great Britain",
                    "results": gb_results,
                    "total": total,
                    "has_contacts": has_contacts,
                    "no_contacts": no_contacts,
                }

        result = renderTemplate(x[0], params)

        if len(x) == 1:
            paths = [x[0]]
        else:
            paths = x[1]

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

        if os.environ.get("GET_SEC_TXT", "false") == "true":
            us_domains_list = ats.getSites(250, "US")
            gb_domains_list = ats.getSites(250, "GB")

            domain_list = set()

            for x in us_domains_list:
                srd = splitRankedDomain(x)
                domain_list.add(srd["domain"])

            for x in gb_domains_list:
                srd = splitRankedDomain(x)
                domain_list.add(srd["domain"])

            if len(domain_list) > 0:
                print("Got domain lists, counts:")
                print("Total -", len(domain_list))
                print("US -", len(us_domains_list))
                print("GB -", len(gb_domains_list))
            else:
                raise Exception("No domains")

            with Pool(int(os.environ.get("POOL_SIZE", "15"))) as p:
                results = p.map(genSecurityTxtForDomain, domain_list)

        genStaticFiles(results, us_domains_list, gb_domains_list)
