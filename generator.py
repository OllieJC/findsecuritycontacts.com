from jinja_helper import renderTemplate
from securitytxt import getSecurityTxt
from multiprocessing import Pool
import shutil
import json
import os
import re


dist: str = "dist/"
top_sites: str = "dist/top/"
well_known: str = "dist/.well-known"


def setupDist():
    try:
        shutil.rmtree(dist)
    except Exception as e:
        print(e)

    os.mkdir(dist)
    os.mkdir(top_sites)
    os.mkdir(well_known)

    shutil.copytree("assets", f"{dist}assets", dirs_exist_ok=True)


def genSecurityTxtForDomain(x: dict) -> dict:
    print(f"Attempting to get security.txt for {x}")

    re_item = re.search("^(?P<num>.+?):(?P<val>.*)", x)
    num = int(re_item.group("num"))
    val = re_item.group("val")

    details = getSecurityTxt(val)
    details.update({"top_index": num})

    result = renderTemplate("domain.html", {"res": details})

    f = open(f"{top_sites}{val}", "w")
    f.write(result)
    f.close()

    return details


def genStaticFiles(results: list):
    for x in [
        ["index.html"],
        ["security.txt", ["security.txt", ".well-known/security.txt"]],
    ]:
        params = {}
        if x[0] == "index.html":
            total = len(results)
            has_contacts = sum(1 for x in results if x["has_contact"])
            no_contacts = total - has_contacts
            params = {
                "results": results,
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


if __name__ == "__main__":
    setupDist()

    domains_raw = []
    f = open("assets/top500Domains.txt")
    domains_raw = f.read().strip().split("\n")
    f.close()

    if domains_raw:
        domains_list = [f"{k+1}:{v}" for k, v in enumerate(domains_raw)]

        results = []

        with Pool(int(os.environ.get("POOL_SIZE", "8"))) as p:
            results = p.map(genSecurityTxtForDomain, domains_list)

        genStaticFiles(results)
