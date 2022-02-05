import sys
import json
import time


def log(target: str = None, error: Exception = None, obj: dict = {}):
    obj.update({"time": time.time()})

    if target is not None:
        obj.update({"target": target})

    if error is not None:
        obj.update({"error": str(error)})

    print(
        json.dumps(obj, default=str), file=sys.stdout if error is None else sys.stderr
    )
