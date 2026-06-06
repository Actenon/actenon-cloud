from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/pilot", tags=["pilot-ui"], include_in_schema=False)


def _page_html(
    *,
    title: str,
    heading: str,
    description: str,
    script_name: str,
    action_intent_record_id: str | None = None,
) -> HTMLResponse:
    action_attr = ""
    if action_intent_record_id is not None:
        action_attr = f' data-action-intent-record-id="{action_intent_record_id}"'

    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link rel="stylesheet" href="/pilot-static/pilot.css">
  </head>
  <body{action_attr}>
    <div id="pilot-app" class="pilot-shell">
      <header class="pilot-shell__hero">
        <p class="pilot-shell__eyebrow">Actenon Cloud</p>
        <h1>{heading}</h1>
        <p class="pilot-shell__description">{description}</p>
      </header>
      <noscript>
        <section class="pilot-card pilot-card--warning">
          <h2>JavaScript Required</h2>
          <p>
            The pilot operator views require JavaScript so they can load authenticated
            finance action data from the existing API surface.
          </p>
        </section>
      </noscript>
    </div>
    <script type="module" src="/pilot-static/{script_name}"></script>
  </body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("")
def get_pilot_root() -> RedirectResponse:
    return RedirectResponse(url="/pilot/actions", status_code=307)


@router.get("/actions")
def get_action_list_page() -> HTMLResponse:
    return _page_html(
        title="Invoice Payment Actions",
        heading="Invoice Payment Actions",
        description=(
            "Review governed invoice payment actions, inspect current lifecycle state, "
            "and open the full trace for one action."
        ),
        script_name="actions-list.js",
    )


@router.get("/review")
def get_review_queue_page() -> HTMLResponse:
    return _page_html(
        title="Invoice Payment Review Queue",
        heading="Invoice Payment Review Queue",
        description=(
            "Review held invoice payment actions, separate blocked outcomes from live "
            "operator work, and open the action detail view for approval or evidence steps."
        ),
        script_name="review-queue.js",
    )


@router.get("/actions/{action_intent_record_id}")
def get_action_detail_page(action_intent_record_id: str) -> HTMLResponse:
    return _page_html(
        title="Invoice Payment Action Detail",
        heading="Invoice Payment Action Detail",
        description=(
            "Inspect one governed invoice payment from intake through proof, release, "
            "receipt, and audit trace."
        ),
        script_name="action-detail.js",
        action_intent_record_id=action_intent_record_id,
    )
