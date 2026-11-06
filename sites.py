# Fetch top500 sites from https://moz.com/top500 with fallback to cache file
import csv
import json
import time
import os
import urllib.request
import urllib.error

from json_logger import log


class Sites:
    TOP_SITES_SOURCE = "https://moz.com/top-500/download?table=top500Domains"
    USER_AGENT = "Mozilla/5.0 (OllieJC/findsecuritycontacts.com)"
    CACHE_FILE = "top500.json"
    CACHE_MAX_AGE = 64800  # 18 hours

    def __init__(self):
        self.top500 = {}

    def __str__(self) -> str:
        return f"{json.dumps(self.getTop500())}"

    def getTop500(self) -> dict:
        if self.cacheAge() > Sites.CACHE_MAX_AGE:
            self.refreshCache()
        else:
            self.readFromCache()
        return self.top500

    def cacheAge(self) -> int:
        """Return the age of the cache file if available; otherwise assumes expired cache"""
        try:
            return time.time() - os.path.getmtime(Sites.CACHE_FILE)
        except (OSError, Exception) as e:
            log(
                target="WARNING",
                message="cache file age not found; assume no cache",
                error=e,
            )
            return Sites.CACHE_MAX_AGE + 1

    def readFromCache(self):
        """Reads the site list from the cache"""
        try:
            log(
                target="INFO",
                message=f"reading sites from cache {Sites.CACHE_FILE}",
            )
            with open(Sites.CACHE_FILE, "r") as cachefile:
                self.top500 = {
                    int(k): str(v) for k, v in dict(json.load(cachefile)).items()
                }
        except ValueError as e:
            log(target="ERROR", message="unexpected cache file content", error=e)
        except (OSError, Exception) as e:
            log(target="ERROR", message="loading of cache file failed", error=e)

    def updateCache(self):
        """Writes the current site list to the cache file"""
        try:
            log(
                target="INFO",
                message=f"saving updated top500 list as {Sites.CACHE_FILE}",
            )
            with open(Sites.CACHE_FILE, "w+") as cachefile:
                json.dump(self.top500, cachefile, indent=2)
                cachefile.write("\n")
        except (OSError, Exception) as e:
            log(target="ERROR", error=e)

    def refreshCache(self):
        """Fetches the site list from the Internet and updates the cache"""
        try:
            log(target="INFO", message=f"updating top500 from {Sites.TOP_SITES_SOURCE}")

            req = urllib.request.Request(
                Sites.TOP_SITES_SOURCE,
                data=None,
                headers={"User-Agent": Sites.USER_AGENT},
            )
            resp = urllib.request.urlopen(req)
            sites = csv.DictReader([l.decode("utf-8") for l in resp.readlines()])

            for site in sites:
                try:
                    self.top500[int(site["Rank"])] = site["Root Domain"]
                except ValueError as e:
                    log(target="ERROR", error=e)

            if len(self.top500) > 0:
                self.updateCache()
            else:
                log(
                    target="WARNING",
                    message="fetched list empty; falling back to cache file",
                )
                self.readFromCache()

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            urllib.error.ContentTooShortError,
            KeyError,
        ) as e:
            if isinstance(e, KeyError):
                log(target="ERROR", message="feched unexcepted content", error=e)
            else:
                log(target="ERROR", message="fetching top sites failed", error=e)
            log(target="INFO", message=f"falling back to cache file {Sites.CACHE_FILE}")
            self.readFromCache()


if __name__ == "__main__":
    """Print the resulting top500 dictionary when called directly"""
    sites = Sites()
    print(sites)
