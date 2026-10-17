# ClinicMaster 4 scripts

ClinicMaster 4 was the clinic's practice-management system from 2009 until PetClinic Lite replaced it at the
Harbourside branch in 2023. The Devonport branch still runs it until it moves over (planned for 2027), so two of
these scripts still run there every week:

- `clinicmaster/export_clients.py` writes the weekly export of clients seen at Devonport, which PetClinic Lite
  imports every Monday (`docs/runbooks/weekly-import.md`);
- `clinicmaster/reminders.py` sends Devonport's own reminder letters.

The rest is kept for reference while the last records move over. **Nothing in `petclinic/` imports this code**, and
its rules are ClinicMaster's, not ours: several are out of date. Don't change these files to fix PetClinic Lite,
and don't copy their logic into it.

The scripts ran on Python 3.6 at Devonport; they read ClinicMaster's own database export (`cm4.db`, not here).
