# TextHub client (vendored)

TextHub's Python client, version 2.3.1, copied here so the clinic needs no packages from PyPI (decision 0007).
Only `client.py`, `segments.py` and `errors.py` are kept; the async client and the webhooks module were removed.

- Don't change these files. To upgrade, copy the new release over them and note the version in `__init__.py`.
- The clinic's own code talks to it only through `petclinic/sms.py`.
- Tests never reach the gateway: without `TEXTHUB_TOKEN`, `sms.client()` returns a dry-run client.

Licensed to Harbourside Vets under the TextHub SDK licence (account HV-20419). Not for redistribution outside the
clinic's systems.
