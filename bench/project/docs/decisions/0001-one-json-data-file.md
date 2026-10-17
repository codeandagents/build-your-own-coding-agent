# 0001: One JSON data file

**Date:** 2023-02-06. **Status:** accepted.

**Context.** The Harbourside branch needed to replace ClinicMaster 4 quickly and cheaply. The front desk has one PC;
there is no server room and no database administrator.

**Decision.** All records live in one JSON file, `clinic.json`, loaded whole by each command and saved whole. One
record per line, so the nightly backup's diffs are readable.

**Consequences.** Simple to back up, read and repair. Every command loads everything: fine up to tens of thousands of
visits (the archive, decision 0009, keeps the file small). Two commands run at once can overwrite each other's
changes: the scheduled tasks never overlap, and the desk runs one command at a time.
