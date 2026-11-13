"""The OpenAPI contract-of-record diff gate (#128).

Usage:
    python3 scripts/openapi_diff.py api/openapi.json current.json

Compares the committed contract (first arg) against the freshly
generated schema (second arg) and exits 1 on BREAKING changes:
  * a path or method disappeared
  * a required request parameter or body field appeared
  * a required parameter or body field changed type / became required
  * a response field changed type or disappeared
Additions are non-breaking (new paths, optional params, response
fields clients can ignore).

Schemas are compared through their $refs (resolved against each
document's own components) and through wrappers (arrays, allOf/anyOf/
oneOf) — a break inside a referenced model or an array element is a
break on the surface.

With --json, prints the findings as JSON (for CI annotations).
"""

import json
import sys


def _deref(ref, root):
    """One local $ref -> its target (or None for anything exotic)."""
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        return root.get("components", {}).get("schemas", {}).get(
            ref.rsplit("/", 1)[-1])
    return None


def _types(node, root):
    """The declared type(s) of a schema node, as a frozenset."""
    if not isinstance(node, dict):
        return frozenset()
    t = node.get("type")
    if isinstance(t, str):
        return frozenset([t])
    if isinstance(t, list):
        return frozenset(t)
    if "enum" in node:
        return frozenset(["enum"])
    if "$ref" in node:
        target = _deref(node["$ref"], root)
        return _types(target, root)
    if "oneOf" in node or "anyOf" in node:
        return frozenset(["union"])
    if "items" in node:
        return _types(node["items"], root)     # arrays: their element type
    return frozenset()


def _props(schema, root, seen=None):
    """Every field name visible in a schema — resolved through $refs,
    combiners (allOf/anyOf/oneOf) and array items."""
    if not isinstance(schema, dict):
        return {}
    seen = seen or set()
    if "$ref" in schema:
        target = _deref(schema["$ref"], root)
        if target is None or id(target) in seen:
            return {}
        return _props(target, root, seen | {id(target)})
    out = {}
    for comb in ("allOf", "oneOf", "anyOf"):
        for sub in schema.get(comb) or []:
            out.update(_props(sub, root, seen))
    items = schema.get("items")
    if items:
        out.update(_props(items, root, seen))
    out.update(schema.get("properties") or {})
    return out


def _required(schema, root, seen=None):
    """Every required field name — same traversal as _props."""
    if not isinstance(schema, dict):
        return set()
    seen = seen or set()
    if "$ref" in schema:
        target = _deref(schema["$ref"], root)
        if target is None or id(target) in seen:
            return set()
        return _required(target, root, seen | {id(target)})
    out = set(schema.get("required") or [])
    for comb in ("allOf", "oneOf", "anyOf"):
        for sub in schema.get(comb) or []:
            out |= _required(sub, root, seen)
    items = schema.get("items")
    if items:
        out |= _required(items, root, seen)
    return out


def breaking(old: dict, new: dict) -> list[str]:
    """Every breaking change between two OpenAPI documents (old =
    contract of record, new = what the branch generates)."""
    out: list[str] = []

    old_paths = old.get("paths") or {}
    new_paths = new.get("paths") or {}
    for path, ops in sorted(old_paths.items()):
        if path not in new_paths:
            out.append(f"path removed: {path}")
            continue
        for method, op in ops.items():
            if method not in new_paths[path]:
                out.append(f"method removed: {method.upper()} {path}")
                continue
            old_op, new_op = op, new_paths[path][method]
            # --- parameters ---
            old_params = {(p.get("name"), p.get("in")): p
                          for p in old_op.get("parameters", [])}
            new_params = {(p.get("name"), p.get("in")): p
                          for p in new_op.get("parameters", [])}
            for key, p in old_params.items():
                np = new_params.get(key)
                if np is None:
                    out.append(f"parameter removed: {p.get('in')}:"
                               f"{p.get('name')} on {method.upper()} {path}")
                elif _types(p.get("schema"), old) and not (
                        _types(p.get("schema"), old)
                        & _types(np.get("schema"), new)):
                    out.append(f"parameter type changed: {p.get('in')}:"
                               f"{p.get('name')} on {method.upper()} {path}")
            for key, p in new_params.items():
                if key not in old_params and p.get("required"):
                    out.append(f"required parameter added: {p.get('in')}:"
                               f"{p.get('name')} on {method.upper()} {path}")
            # --- request bodies ---
            old_body = (old_op.get("requestBody") or {}).get("content", {}) \
                .get("application/json", {}).get("schema", {})
            new_body = (new_op.get("requestBody") or {}).get("content", {}) \
                .get("application/json", {}).get("schema", {})
            for name in _required(new_body, new) - _required(old_body, old):
                if name in _props(new_body, new) and \
                        name not in _props(old_body, old):
                    out.append(f"required request field added: {name} "
                               f"on {method.upper()} {path}")
            # --- responses (any 2xx/4xx key both sides understand) ---
            old_resps = old_op.get("responses") or {}
            new_resps = new_op.get("responses") or {}
            for code, r in old_resps.items():
                if code not in new_resps:
                    out.append(f"response removed: {code} on "
                               f"{method.upper()} {path}")
                    continue
                old_schema = (r.get("content") or {}) \
                    .get("application/json", {}).get("schema", {})
                new_schema = (new_resps[code].get("content") or {}) \
                    .get("application/json", {}).get("schema", {})
                old_rprops = _props(old_schema, old)
                new_rprops = _props(new_schema, new)
                for name, schema in old_rprops.items():
                    if name not in new_rprops:
                        out.append(f"response field removed: {code}:{name} "
                                   f"on {method.upper()} {path}")
                    elif _types(schema, old) and not (
                            _types(schema, old)
                            & _types(new_rprops[name], new)):
                        out.append(f"response field type changed: "
                                   f"{code}:{name} on "
                                   f"{method.upper()} {path}")
    # --- component models (the shapes responses reference, directly or
    # through other models — webhooks payloads included). A break in a
    # reachable model is a surface break even when no response names it
    # at the top level.
    old_comps = old.get("components", {}).get("schemas", {})
    new_comps = new.get("components", {}).get("schemas", {})
    for name, s in sorted(old_comps.items()):
        ns = new_comps.get(name)
        if ns is None:
            continue          # a model nothing references anymore is dead code
        for field, fs in (s.get("properties") or {}).items():
            nf = (ns.get("properties") or {}).get(field)
            if nf is None:
                out.append(f"model field removed: {name}.{field}")
            elif _types(fs, old) and not (_types(fs, old) & _types(nf, new)):
                out.append(f"model field type changed: {name}.{field}")
    return sorted(set(out))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    old = json.load(open(sys.argv[1]))
    new = json.load(open(sys.argv[2]))
    findings = breaking(old, new)
    if "--json" in sys.argv:
        print(json.dumps({"breaking": findings}, indent=2))
    else:
        for f in findings:
            print(f"BREAKING: {f}")
    if findings:
        print(f"\n{len(findings)} breaking change(s). The OpenAPI snapshot "
              "(api/openapi.json) is the contract of record (#128): either "
              "revert, or add the `api-breaking` label after a deprecation "
              "cycle per docs/deprecation.md, then regenerate the snapshot "
              "with scripts/openapi_dump.py.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
