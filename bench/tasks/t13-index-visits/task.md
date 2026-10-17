`Store.visits_for_pet` and `Store.book_visit` are too slow for our biggest clinic: its data file has 200,000
visits, the pet history screen calls `visits_for_pet` thousands of times, and the import of the old system's history
books thousands of visits in one go. Make both fast: on a store with 200,000 visits, 1,000 `visits_for_pet` calls
must take well under 2 seconds in total, and so must 2,000 `book_visit` calls.

Nothing else may change: every Store method must keep returning exactly what it returns today, after every way the
app changes visits: booking, cancelling, rescheduling and purging visits, merging duplicate pets or owners, archiving
visits and restoring them, and loading a store from its file.
