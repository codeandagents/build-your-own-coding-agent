# 0006: Importing from ClinicMaster every week

**Date:** 2023-06-12. **Status:** accepted; ends when Devonport moves over (2027).

**Context.** Devonport still runs ClinicMaster 4. Its clients also come to Harbourside, and both branches' front desks
need to find them.

**Decision.** Devonport exports the clients it saw each week (`legacy/clinicmaster/export_clients.py`) and Harbourside
imports the file every Monday (`petclinic/importer.py`, `docs/runbooks/weekly-import.md`). The export copies records as
ClinicMaster has them, without cleaning: the importer does the cleaning. It must be safe to import the same file twice.

**Consequences.** Names arrive in any case and spacing, numbers in any format, dates in whatever form they were typed.
A row the importer can't use is skipped and logged, never guessed; the practice manager phones those clients.
