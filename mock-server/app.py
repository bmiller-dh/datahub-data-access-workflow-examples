"""
Mock server for grant_permissions with a simple UI to list pending Data Access
Requests and Approve/Deny them. Also receives POSTs from the grant-external-permissions
DataHub action when requests are approved.
"""
import base64
import json
import os
from collections import deque

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory store of recent grant_permissions POSTs (last 50)
RECENT_GRANTS = deque(maxlen=50)
RECENT_METADATA_PROPOSALS = deque(maxlen=50)
RECENT_GLOSSARY_PROPOSALS = deque(maxlen=50)

DATAHUB_URL = os.environ.get("DATAHUB_URL", "").rstrip("/")
DATAHUB_TOKEN = os.environ.get("DATAHUB_TOKEN", "")


def _current_user_urn():
    """Get corpuser URN from JWT sub claim."""
    if not DATAHUB_TOKEN:
        return None
    try:
        parts = DATAHUB_TOKEN.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1] + "==" * (4 - len(parts[1]) % 4)
        payload = base64.urlsafe_b64decode(payload_b64)
        data = json.loads(payload)
        sub = data.get("sub")
        if sub:
            return f"urn:li:corpuser:{sub}"
    except Exception:
        pass
    return None


def _graphql(query: str, variables: dict):
    if not DATAHUB_URL or not DATAHUB_TOKEN:
        return None, "DATAHUB_URL and DATAHUB_TOKEN must be set"
    url = f"{DATAHUB_URL}/api/graphql"
    headers = {"Authorization": f"Bearer {DATAHUB_TOKEN}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, json={"query": query, "variables": variables}, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get("errors"):
            return None, data["errors"][0].get("message", str(data["errors"]))
        return data.get("data"), None
    except requests.RequestException as e:
        return None, str(e)


LIST_REQUESTS_QUERY = """
query ListActionRequests($input: ListActionRequestsInput!) {
  listActionRequests(input: $input) {
    total
    actionRequests {
      urn
      status
      result
      entity { ... on Dataset { urn name properties { name } } }
    }
  }
}
"""

REVIEW_MUTATION = """
mutation Review($input: ReviewActionWorkflowFormRequestInput!) {
  reviewActionWorkflowFormRequest(input: $input)
}
"""


@app.route("/", methods=["GET"])
def index():
    return _dashboard_html()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "up"})


@app.route("/api/pending", methods=["GET"])
def api_pending():
    """Return pending Data Access Requests assigned to the token user."""
    user_urn = _current_user_urn()
    if not user_urn:
        return jsonify({"error": "DATAHUB_TOKEN not set or invalid"}), 400
    input_params = {
        "start": 0,
        "count": 50,
        "type": "WORKFLOW_FORM_REQUEST",
        "allActionRequests": True,
        "status": "PENDING",
        "assignee": {"type": "USER", "urn": user_urn},
    }
    data, err = _graphql(LIST_REQUESTS_QUERY, {"input": input_params})
    if err:
        return jsonify({"error": err}), 502
    result = data.get("listActionRequests") or {}
    return jsonify({"total": result.get("total", 0), "requests": result.get("actionRequests", [])})


@app.route("/api/review", methods=["POST"])
def api_review():
    """Approve or deny a request. Body: { requestUrn, result: "ACCEPTED"|"REJECTED", comment? }"""
    body = request.get_json(force=True, silent=True) or {}
    urn = body.get("requestUrn") or body.get("request_urn")
    result = body.get("result", "").upper()
    comment = body.get("comment") or body.get("comment", "")
    if not urn or result not in ("ACCEPTED", "REJECTED"):
        return jsonify({"error": "requestUrn and result (ACCEPTED|REJECTED) required"}), 400
    data, err = _graphql(REVIEW_MUTATION, {"input": {"urn": urn, "result": result, "comment": comment or None}})
    if err:
        return jsonify({"error": err}), 502
    return jsonify({"ok": True, "reviewActionWorkflowFormRequest": data.get("reviewActionWorkflowFormRequest")})


@app.route("/api/activity", methods=["GET"])
def api_activity():
    """Recent grant_permissions events received from the pipeline."""
    return jsonify({"events": list(RECENT_GRANTS)})


@app.route("/api/metadata_proposals", methods=["GET"])
def api_metadata_proposals():
    """Recent metadata proposal events (from metadata-proposal-pipeline)."""
    return jsonify({"events": list(RECENT_METADATA_PROPOSALS)})


@app.route("/api/glossary_proposals", methods=["GET"])
def api_glossary_proposals():
    """Recent glossary proposal events (from glossary-proposal-pipeline)."""
    return jsonify({"events": list(RECENT_GLOSSARY_PROPOSALS)})


@app.route("/metadata_proposals", methods=["POST"])
def metadata_proposals():
    """Receive metadata proposal events from metadata-proposal-pipeline."""
    data = request.get_json(force=True, silent=True) or {}
    RECENT_METADATA_PROPOSALS.append(data)
    print("[mock-server] POST /metadata_proposals received:", data.get("actionRequestType"), data.get("entityUrn"), flush=True)
    return jsonify({"status": "ok", "received": True})


@app.route("/glossary_proposals", methods=["POST"])
def glossary_proposals():
    """Receive glossary proposal events from glossary-proposal-pipeline."""
    data = request.get_json(force=True, silent=True) or {}
    RECENT_GLOSSARY_PROPOSALS.append(data)
    print("[mock-server] POST /glossary_proposals received:", data.get("actionRequestType"), data.get("entityUrn"), flush=True)
    return jsonify({"status": "ok", "received": True})


@app.route("/grant_permissions", methods=["POST"])
def grant_permissions():
    data = request.get_json(force=True, silent=True) or {}
    RECENT_GRANTS.append(data)
    print("[mock-server] POST /grant_permissions received:", flush=True)
    print(f"  entityUrn: {data.get('entityUrn')}", flush=True)
    print(f"  actorUrn: {data.get('actorUrn')}", flush=True)
    print(f"  result: {data.get('result')}", flush=True)
    return jsonify({"status": "ok", "message": "Permissions granted (mock)", "received": True})


def _dashboard_html():
    config_ok = bool(DATAHUB_URL and DATAHUB_TOKEN)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Grant Permissions Mock – Data Access Requests</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1rem 2rem; max-width: 900px; }}
    h1 {{ margin-top: 0; }}
    .badge {{ display: inline-block; padding: 0.2em 0.5em; border-radius: 4px; font-size: 0.85em; }}
    .badge.ok {{ background: #d4edda; color: #155724; }}
    .badge.warn {{ background: #fff3cd; color: #856404; }}
    .req {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; }}
    .req .meta {{ color: #666; font-size: 0.9em; margin-top: 0.5rem; }}
    .btns {{ margin-top: 0.75rem; }}
    .btns button {{ margin-right: 0.5rem; padding: 0.4rem 0.8rem; cursor: pointer; border-radius: 4px; border: 1px solid #ccc; }}
    .btns button.approve {{ background: #28a745; color: white; border-color: #28a745; }}
    .btns button.deny {{ background: #dc3545; color: white; border-color: #dc3545; }}
    .activity {{ margin-top: 2rem; }}
    .activity ul {{ list-style: none; padding: 0; }}
    .activity li {{ border-left: 3px solid #28a745; padding: 0.5rem 1rem; margin-bottom: 0.5rem; background: #f8f9fa; }}
    .empty {{ color: #666; }}
    #msg {{ margin-top: 1rem; min-height: 1.5em; }}
  </style>
</head>
<body>
  <h1>Grant Permissions Mock</h1>
  <p>
    <span class="badge {'ok' if config_ok else 'warn'}">
      {'DataHub configured' if config_ok else 'Set DATAHUB_URL and DATAHUB_TOKEN for Approve/Deny'}
    </span>
  </p>

  <h2>Pending requests (yours)</h2>
  <div id="pending"></div>
  <div id="msg"></div>

  <div class="activity">
    <h2>Recent approvals received (from pipeline)</h2>
    <ul id="activity"></ul>
  </div>
  <div class="activity">
    <h2>Recent metadata proposals</h2>
    <ul id="metadata-proposals"></ul>
  </div>
  <div class="activity">
    <h2>Recent glossary proposals</h2>
    <ul id="glossary-proposals"></ul>
  </div>

  <script>
    const configOk = {json.dumps(config_ok).lower()};
    function msg(t, isErr) {{
      const el = document.getElementById('msg');
      el.textContent = t;
      el.style.color = isErr ? '#c00' : '#333';
    }}
    function loadPending() {{
      const div = document.getElementById('pending');
      if (!configOk) {{ div.innerHTML = '<p class="empty">Configure DATAHUB_URL and DATAHUB_TOKEN and restart the server.</p>'; return; }}
      fetch('/api/pending')
        .then(r => r.json())
        .then(data => {{
          if (data.error) {{ div.innerHTML = '<p class="empty">' + data.error + '</p>'; return; }}
          if (!data.requests || data.requests.length === 0) {{
            div.innerHTML = '<p class="empty">No pending requests assigned to you.</p>';
            return;
          }}
          div.innerHTML = data.requests.map(r => {{
            const name = (r.entity && r.entity.name) || (r.entity && r.entity.properties && r.entity.properties.name) || r.urn;
            return `
              <div class="req" data-urn="${{r.urn}}">
                <strong>${{name}}</strong>
                <div class="meta">${{r.urn}}</div>
                <div class="btns">
                  <button class="approve" onclick="review('${{r.urn}}', 'ACCEPTED')">Approve</button>
                  <button class="deny" onclick="review('${{r.urn}}', 'REJECTED')">Deny</button>
                </div>
              </div>`;
          }}).join('');
        }})
        .catch(e => {{ div.innerHTML = '<p class="empty">Error: ' + e.message + '</p>'; }});
    }}
    function review(urn, result) {{
      msg('Sending ' + result + '...');
      fetch('/api/review', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ requestUrn: urn, result: result, comment: result === 'ACCEPTED' ? 'Approved via mock UI' : 'Denied via mock UI' }})
      }})
        .then(r => r.json())
        .then(data => {{
          if (data.error) {{ msg('Error: ' + data.error, true); return; }}
          msg(result + ' submitted. Refresh to update list.');
          loadPending();
        }})
        .catch(e => msg('Error: ' + e.message, true));
    }}
    function loadActivity() {{
      fetch('/api/activity')
        .then(r => r.json())
        .then(data => {{
          const ul = document.getElementById('activity');
          if (!data.events || data.events.length === 0) {{ ul.innerHTML = '<li class="empty">None yet. Approve a request in DataHub (or here) to see pipeline events here.</li>'; return; }}
          ul.innerHTML = data.events.slice().reverse().map(e => {{
            const entity = e.entityUrn || '';
            const name = (e.entityName || entity.split('/').pop() || entity).substring(0, 60);
            const res = e.result || '—';
            return '<li><strong>' + res + '</strong> ' + name + '</li>';
          }}).join('');
        }});
    }}
    function loadProposals(endpoint, listId, emptyText) {{
      fetch(endpoint)
        .then(r => r.json())
        .then(data => {{
          const ul = document.getElementById(listId);
          if (!data.events || data.events.length === 0) {{ ul.innerHTML = '<li class="empty">' + emptyText + '</li>'; return; }}
          ul.innerHTML = data.events.slice().reverse().map(e => {{
            const type = e.actionRequestType || e.eventType || '—';
            const entity = (e.entityUrn || '').substring(0, 80);
            return '<li><strong>' + type + '</strong> ' + entity + '</li>';
          }}).join('');
        }});
    }}
    loadPending();
    loadActivity();
    loadProposals('/api/metadata_proposals', 'metadata-proposals', 'None yet. Run metadata-proposal-pipeline and create a metadata proposal in DataHub.');
    loadProposals('/api/glossary_proposals', 'glossary-proposals', 'None yet. Run glossary-proposal-pipeline and create a glossary proposal in DataHub.');
    setInterval(loadActivity, 5000);
    setInterval(() => {{ loadProposals('/api/metadata_proposals', 'metadata-proposals', 'None yet.'); loadProposals('/api/glossary_proposals', 'glossary-proposals', 'None yet.'); }}, 5000);
  </script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
