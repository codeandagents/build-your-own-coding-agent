Yesterday the front desk imported the old system's export with `python -m petclinic import`, and some pets didn't
make it in. The import's log is logs/import-2026-10-15.log. Find out why those pets were skipped and fix the importer
so they import next time. Rows that were skipped for a good reason must still be skipped.
