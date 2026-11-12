# tonearm TypeScript client

GENERATED from the real OpenAPI schema (`schema.ts`) — do not edit by hand.
Regenerate on the next release tag (`clients.yml` does it):

    npx openapi-typescript@7 <server>/openapi.json -o schema.ts

    import { createClient } from "@hey-api/openapi-fetch";
    import type { paths } from "./schema";

    const client = createClient<paths>({ baseUrl: "http://127.0.0.1:8189" });

Auth (both dialects are in the schema): pass `api_key` as a query param or
an `Authorization: Bearer` header when the server runs keyed.
