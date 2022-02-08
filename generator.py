import shutil
import json
import os
import re
import sys

import sites

from multiprocessing import Pool

from jinja_helper import renderTemplate
from target import scan
from json_logger import log


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
    x: tuple, topOrGen: str = top_sites, return_body: bool = False
) -> dict:

    details = {}
    try:
        details = scan(x[1])
    except Exception as e:
        log(x[1], e)
    details.update({"rank": x[0]})

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
        try:
            f = open(f"{topOrGen}{x[1]}", "w", encoding="utf-8")
            f.write(result)
            f.close()
        except Exception as e:
            log(x[1], e)

        if "target" in details:
            res_dict = {
                details["target"]: {
                    "rank": details["rank"],
                    "has_contact": details["has_contact"],
                    "has_dns_contact": True
                    if "dnssecuritytxt" in details
                    and details["dnssecuritytxt"]["security_contact"] is not None
                    else False,
                }
            }
            if "http_security_txt" in details and details["http_security_txt"] != {}:
                res_dict[details["target"]].update(
                    {
                        "status_code": details["http_security_txt"]["status_code"],
                        "http_valid_https": details["http_security_txt"]["valid_https"],
                        "http_valid_content_type": details["http_security_txt"][
                            "valid_content_type"
                        ],
                        "has_http_contact": True,
                        "has_http_type": details["http_security_txt"]["type"],
                    }
                )
            else:
                res_dict[details["target"]].update(
                    {
                        "status_code": 0,
                        "http_valid_https": False,
                        "http_valid_content_type": False,
                        "has_http_contact": False,
                        "has_http_type": None,
                    }
                )
            return res_dict
        else:
            return {}


def genStaticFiles(results: dict):
    f = open(f"{dist}api/top{len(results)}.json", "w", encoding="utf-8")
    json.dump(results, f, indent=2)
    f.close()

    for x in [
        ["index.html", "top sites", ["index.html"]],
        ["index.html", "valid top sites", ["only-valid"]],
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
            lenres = len(results)
            if lenres == 0:
                continue

            has_contacts = 0
            norm_results = {}
            for result in results:
                norm_results[results[result]["rank"]] = {
                    **{"target": result},
                    **results[result],
                }
                if results[result]["has_contact"]:
                    has_contacts += 1
            no_contacts = lenres - has_contacts
            params = {
                "country": "...",
                "results": norm_results,
                "total": lenres,
                "has_contacts": has_contacts,
                "no_contacts": no_contacts,
                "country_short_code": "..",
            }
            if "only-valid" in x[2]:
                params["only_valid"] = True

        if x[1]:
            params.update({"title": x[1]})
        result = renderTemplate(x[0], params)

        if len(x) == 2:
            paths = [x[0]]
        else:
            paths = x[2]

        for p in paths:
            f = open(f"{dist}{p}", "w", encoding="utf-8")
            f.write(result)
            f.close()


if __name__ == "__main__":
    setupDist()
    lenArgs = len(sys.argv)

    if lenArgs == 2:
        domain = sys.argv[1]
        genSecurityTxtForDomain((0, domain), gen_sites)
    else:
        domains_dict = {}

        if os.environ.get("GET_SEC_TXT", "false") == "true":
            domains_dict = (
                sites.top500
            )  # {nn: sites.top500[nn] for nn in list(sites.top500)[:10]}

            if len(domains_dict) > 0:
                print("Got domain lists, counts:")
                print("Total -", len(domains_dict))
            else:
                raise Exception("No domains")

            results_list = []
            with Pool(int(os.environ.get("POOL_SIZE", os.cpu_count()))) as p:
                results_list = p.map(genSecurityTxtForDomain, domains_dict.items())

        results_dict = {}
        for result in results_list:
            key = list(result.keys())[0]
            results_dict[key] = result[key]

        genStaticFiles(results_dict)
