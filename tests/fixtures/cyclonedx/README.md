# CycloneDX 1.6 JSON schema (unmodified copies)

Used by `tests/test_cbom_schema.py` to validate the scanner's CBOM output (`jsonschema` is pinned in
the `dev` extra since 2026-10-05).

Source: <https://github.com/CycloneDX/specification>, directory `schema/`, commit
`1ce97b2a7b8cf2429da248560d2aa671c6bce74a`, downloaded on 2026-10-01 from

- <https://raw.githubusercontent.com/CycloneDX/specification/1ce97b2a7b8cf2429da248560d2aa671c6bce74a/schema/bom-1.6.schema.json>
- <https://raw.githubusercontent.com/CycloneDX/specification/1ce97b2a7b8cf2429da248560d2aa671c6bce74a/schema/spdx.schema.json>
- <https://raw.githubusercontent.com/CycloneDX/specification/1ce97b2a7b8cf2429da248560d2aa671c6bce74a/schema/jsf-0.82.schema.json>

`bom-1.6.schema.json` refers to the other two by relative `$ref`, so all three are kept together.
The CycloneDX specification is published under the Apache License 2.0.
