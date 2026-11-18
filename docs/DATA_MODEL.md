# Data model principles

Every development record should eventually have:
- stable ID
- title, description, category, sector
- district ID (nullable for statewide/multi-district)
- status and status history
- announced investment vs realized investment as separate fields
- expected jobs vs verified jobs created as separate fields
- affected/beneficiary counts with methodology and date
- one or more source records (URL, publisher, publication date, retrieved date)
- confidence and verification state
- created/updated timestamps

Recommended statuses:
`announced -> mou_signed -> approved -> grounded -> operational`
Additional terminal/exception states: `delayed`, `cancelled`, `on_hold`.

Do not automatically advance a project's status based on an AI-generated summary. Require documentary evidence and a reviewable status event.
