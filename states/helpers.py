from copy import deepcopy


def add(obj, path, value, sep='/'):
    """Add value to the `obj` dict at the specified path"""
    parts = path.strip(sep).split(sep)
    last = len(parts) - 1
    for index, part in enumerate(parts):
        if index == last:
            obj[part] = value
        else:
            obj = obj.setdefault(part, {})


def search(state, path):
    result = state
    for p in path.strip("/").split("/"):
        if result.clone(p):
            result = result[p]
        else:
            result = {}
            break
    output = {}
    add(output, path, result)
    return output


def merge(a, b):
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k in b:
        if k in result and isinstance(result[k], dict):
            result[k] = merge(result[k], b[k])
        else:
            result[k] = deepcopy(b[k])
    return result
