# Deprecation policy — the freeze contract

tonearm's API surface is the contract: the OpenAPI snapshot
(`api/openapi.json`) is its record, the PWA + companion pages + live_test
are the canaries, and this document is what "frozen" means.

## The one rule

**A deprecated route or response shape survives ONE MINOR CYCLE with
loud headers, then dies.** Nothing breaks without a cycle of warning.

## How a deprecation happens

1. The replacement (or the removal note) is written in the CHANGELOG
   entry of the minor release that introduces it.
2. The old route is registered in `tonearm/deprecate.py::DEPRECATED`
   with its sunset date (the next minor's release date, at minimum —
   when in doubt, one full minor cycle out).
3. Clients see, on every response from that route:
   - `Deprecation: true`
   - `Sunset: <HTTP-date>` — when it dies
   - `Link: </api/…>; rel="successor-version"` — where to go
   - `Deprecation-Note: …` — anything the changelog says in brief
4. The `/health` `surface` field and the `X-Tonearm-Surface` header pin
   the surface version clients coded against. A bump from `0.8` to
   `0.9` is the signal to re-read the changelog.

## Removing

When the sunset date passes, the route/shape is deleted, the registry
entry is deleted, the OpenAPI snapshot is regenerated
(`scripts/openapi_dump.py`), and the CHANGELOG says "removed" in that
release. CI's OpenAPI gate (#128) fails any breaking diff that didn't
go through this policy (the `api-breaking` label is how a PR swears it
did — one label per reviewed, policy-compliant break).

## The last pre-1.0 break

The error envelope (#32) is the LAST breaking change before the freeze.
After v1.0.0: only additive changes without a deprecation cycle;
everything else rides the policy above.
