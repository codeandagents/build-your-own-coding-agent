# 0007: No dependencies

**Date:** 2023-02-06. **Status:** accepted.

**Context.** The front-desk PC has no internet access for installing packages (the clinic's IT contract), and nobody
maintains the app full time.

**Decision.** Python's standard library only. Third-party code the app needs is copied into `vendor/` whole, with its
version, and never edited: an upgrade replaces the folder.

**Consequences.** No `requirements.txt` for the app. Tests use pytest, which the developers' machines have.
