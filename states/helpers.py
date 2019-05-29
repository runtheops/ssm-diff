from copy import deepcopy


def add(obj, path, value, sep='/'):
    """Add value to the `obj` dict at the specified path"""
    parts = path.strip(sep).split(sep)
    last = len(parts) - 1
    current = obj
    for index, part in enumerate(parts):
        if index == last:
            current[part] = value
        else:
            current = current.setdefault(part, {})
    # convenience return, object is mutated
    return obj


def search(state, path):
    """Get value in `state` at the specified path, returning {} if the key is absent"""
    if path.strip("/") == '':
        return state
    for p in path.strip("/").split("/"):
        if p not in state:
            return {}
        state = state[p]
    return state


def filter(state, path):
    if path.strip("/") == '':
        return state
    return add({}, path, search(state, path))


def merge(a, b):
    if not isinstance(b, dict):
        return b
    # TODO: we deepcopy `a` at every level which is overkill
    result = deepcopy(a)
    for k in b:
        if k in result and isinstance(result[k], dict):
            result[k] = merge(result[k], b[k])
        else:
            result[k] = deepcopy(b[k])
    return result
