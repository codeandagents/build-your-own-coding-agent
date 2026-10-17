# 0009: The visit archive

**Date:** 2025-02-24. **Status:** accepted.

**Context.** Vets must keep clinical records for seven years. `clinic.json` was growing by ~1,000 visits a year and
every command loads it whole.

**Decision.** Once a year the practice manager runs `archive --before <seven years ago>`: those visits move to
`data/archive.json` with their ids. `restore` brings them back (all, or one pet's) when a full history is needed.

**Consequences.** Archived visits don't show in reports, statements or a pet's history until restored. Ids stay unique
across both files.
