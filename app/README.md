# App Layout

This directory now contains the initial backend runtime foundation for Actenon Cloud.

Current runtime modules:

- `main.py` for the FastAPI entrypoint and middleware
- `config.py` for environment-backed settings
- `logging.py` for structured logging
- `database.py` for SQLAlchemy scaffolding
- `container.py` for runtime wiring
- `api/` for router and health endpoints
- `pilot_ui/` for the narrow built-in invoice payment pilot UI

Current pilot UI routes:

- `/pilot/actions` for the invoice payment action list
- `/pilot/review` for the held and exceptions queue
- `/pilot/actions/{action_intent_record_id}` for the invoice payment detail and trace view

The repository remains backend-first. Future domain modules should continue to favor:

- intake
- tenancy and auth
- policy and approvals
- evidence
- receipts
- audit and export
- revocation and quarantine
