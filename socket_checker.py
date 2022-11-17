import socket
import struct
import ssl
import OpenSSL.crypto
import pytz
from datetime import datetime

from json_logger import log


def socket_check(
    target: str,
    ports: list = [443, 80],
    timeout: int = 2,
    custom_cipher_set: str = "",
) -> dict:
    port = None
    cert = None
    raw_cert = None

    for p in ports:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        if custom_cipher_set:
            ctx.set_ciphers(custom_cipher_set)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        sock.settimeout(timeout)

        is_break = False

        try:
            result_of_check = 1
            with ctx.wrap_socket(sock, server_hostname=target) as sock:
                result_of_check = sock.connect((target, p))
                bcert = sock.getpeercert(binary_form=True)
                if bcert:
                    cert = get_certificate_info(bcert)

            if result_of_check is None:
                port = p
                is_break = True

        except ssl.SSLError as e:
            port = p
            is_break = True
            log(target, error=e, obj={"port": p, "error_type": "sslerror"})

        except Exception as e:
            log(target, error=e, obj={"port": p, "error_type": "socket"})

        sock.close()

        if is_break:
            break

    return {"port": port, "certificate": cert}


def get_certificate_info(bcert):
    res = None
    cert = None
    try:
        fcert = ssl.DER_cert_to_PEM_cert(bcert)
        c = OpenSSL.crypto
        cert = c.load_certificate(c.FILETYPE_PEM, fcert)

        if cert is not None:
            date_format, encoding = "%Y%m%d%H%M%SZ", "ascii"

            not_before = datetime.strptime(
                cert.get_notBefore().decode(encoding), date_format
            ).replace(tzinfo=pytz.UTC)

            not_after = datetime.strptime(
                cert.get_notAfter().decode(encoding), date_format
            ).replace(tzinfo=pytz.UTC)

            new_date_format = "%Y-%m-%d %H:%M:%S %Z"

            res = {
                "issuer": x509name_tostring(cert.get_issuer()),
                "notAfter": datetime.strftime(not_after, new_date_format),
                "notBefore": datetime.strftime(not_before, new_date_format),
                "serialNumber": cert.get_serial_number(),
                "subject": x509name_tostring(cert.get_subject()),
            }

            for n in range(0, cert.get_extension_count()):
                ce = cert.get_extension(n)
                if ce and "get_data" in dir(ce) and "get_short_name" in dir(ce):
                    short_name = ce.get_short_name().decode("utf-8")
                    data = None

                    if short_name == "subjectAltName":
                        sadata = ce._subjectAltNameString().split(", ")
                        data = {}
                        for isad in sadata:
                            k = isad.partition(":")[0]
                            v = isad.partition(":")[2]
                            if k not in data:
                                data[k] = []
                            data[k].append(v)
                    else:
                        try:
                            sdata = str(ce).split("\n")
                            data = []
                            for isd in sdata:
                                if isd:
                                    isd = isd.strip()
                                    if isd and isd not in data:
                                        if "URI" in isd:
                                            k = isd.partition(":")[0]
                                            v = isd.partition(":")[2]
                                            data.append({k: v})
                                        else:
                                            data.append(isd)
                        except Exception:
                            data = str(ce.get_data())

                    res.update({short_name: data})
    except Exception as e:
        log(target, error=e, obj={"port": p, "error_type": "get_certificate_info"})
    return res


def x509name_tostring(x509name):
    if "get_components" in dir(x509name):
        c = x509name.get_components()
        res = ""
        for x in c:
            key = x[0].decode("ascii")
            value = x[1].decode("ascii")
            res += f"/{key}={value}"
        return res
    else:
        return None
