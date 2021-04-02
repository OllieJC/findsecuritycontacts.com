import jinja2
import colorsys
import os
import html
import re
import time
import subresource_integrity as integrity


def colourFromLetter(letter: str = "") -> str:
    if not letter:
        num = random.randint(65, 90)
    elif len(letter) > 1:
        letter = letter[0]
    if letter:
        num = ord(letter.upper())

    perc = (num - 61) / 30
    hexval = colorsys.hsv_to_rgb(perc, 34 / 100, 39 / 100)
    return "".join("%02X" % round(i * 255) for i in hexval)


def pb(boolIn: bool) -> str:
    if boolIn:
        return "Yes"
    else:
        return "No"


def makeLink(v: str) -> str:
    v = v.strip().replace("<", "").replace(">", "")
    v = html.escape(v)
    v = v.replace("&amp;", "&")

    res = v

    try:
        if v.startswith("mailto:"):
            v_re = re.search("^mailto:(?P<val>.+?)(?:\<|$)", v)
            actual = v_re.group("val")
            res = f'<a href="mailto:{actual}">{actual}</a>'

        if v.startswith("https://"):
            v_re = re.search("^(?P<val>https:\/\/.+?)(?:\<|$)", v)
            actual = v_re.group("val")
            res = f'<a href="{actual}">{actual}</a>'

    except Exception as e:
        res += "<!-- weird error during makeLink... -->"

    return res


asset_sris: dict = {}


def getOrSetAssetSRI(filename: str) -> str:
    global asset_sris

    if filename not in asset_sris:
        f = open(filename, "rb")
        fbs = f.read()
        hash = integrity.render(fbs)
        asset_sris[filename] = hash

    return asset_sris[filename]


def renderTemplate(filename: str, params: dict = {}, domain: str = "") -> str:
    params.update({"filename": filename})
    params.update({"updated_at": time.strftime("%H:%M:%S%z on %d %B %Y")})

    if domain:
        params.update({"domain": domain})

    for x in [
        ["bs_min_css_hash", "assets/css/bootstrap.min.css"],
        ["bs_table_css_hash", "assets/css/bootstrap-table.min.css"],
        ["main_css_hash", "assets/css/_main_1617388203.css"],
        ["font_awesome_css_hash", "assets/css/all.css"],
        ["jq_js_hash", "assets/js/jquery.min.js"],
        ["bsb_js_hash", "assets/js/bootstrap.bundle.min.js"],
        ["bs_table_js_hash", "assets/js/bootstrap-table.min.js"],
        ["main_js_hash", "assets/js/_main.js"],
    ]:
        params.update({x[0]: getOrSetAssetSRI(x[1])})

    templateLoader = jinja2.FileSystemLoader(searchpath="./templates")
    templateEnv = jinja2.Environment(loader=templateLoader)

    templateEnv.globals["colourFromLetter"] = colourFromLetter
    templateEnv.globals["pb"] = pb
    templateEnv.globals["makeLink"] = makeLink

    template = templateEnv.get_template(filename)
    return template.render(params)
