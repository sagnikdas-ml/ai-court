const API_DEFAULT = "https://app.ambiguous.ai/api";
const VALID_STATES = new Set(["offer", "hired", "rejected", "fired"]);

const respond = (body, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});
const clean = (value) => String(value ?? "").trim();
const key = (value) => clean(value).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");

function parseContent(envelope) {
  let data = envelope?.content ?? envelope?.data ?? envelope;
  if (typeof data === "string") {
    try { data = JSON.parse(data); } catch { throw new Error("Ambiguous returned invalid sheet content"); }
  }
  const sheet = data?.sheets?.[0];
  const matrix = Array.isArray(data) ? data : Array.isArray(data?.values) ? data.values : Array.isArray(data?.rows) ? data.rows : sheet?.rows;
  if (!Array.isArray(matrix)) throw new Error("Ambiguous returned an unexpected sheet shape");
  const rows = matrix.map((row) => Array.isArray(row) ? Object.fromEntries(row.map((value, index) => [columnId(index), value])) : row || {});
  const headerIndex = rows.findIndex((row) => Object.values(row).some((value) => clean(value)));
  if (headerIndex < 0) return { rows: [], headers: [], tab: sheet?.name || "Sheet1", headerIndex: -1 };
  const headerRow = rows[headerIndex];
  const headers = Object.entries(headerRow).filter(([, value]) => clean(value)).map(([column, value]) => ({ column, name: key(value) }));
  const records = rows.slice(headerIndex + 1).map((row, offset) => ({
    rowIndex: headerIndex + 1 + offset,
    values: Object.fromEntries(headers.map(({ column, name }) => [name, clean(row?.[column])])),
  })).filter(({ values }) => Object.values(values).some(Boolean));
  return { rows: records, headers, tab: sheet?.name || "Sheet1", headerIndex };
}

async function ambi(env, path, options = {}) {
  if (!env.AMBIGUOUS_API_KEY) throw new Error("AMBIGUOUS_API_KEY is not configured");
  const response = await fetch(`${env.AMBIGUOUS_API_URL || API_DEFAULT}${path}`, {
    ...options,
    headers: { authorization: `Bearer ${env.AMBIGUOUS_API_KEY}`, ...(options.headers || {}) },
  });
  if (!response.ok) {
    const detail = await response.text();
    let message = detail;
    try { message = JSON.parse(detail).error || detail; } catch {}
    throw new Error(`Ambiguous API returned ${response.status}: ${message || response.statusText}`);
  }
  return response.status === 204 ? null : response.json();
}

async function apiSheetId(env, title) {
  const sheets = await ambi(env, "/sheets");
  const found = (sheets.data || []).find((sheet) => clean(sheet.title || sheet.name).toLowerCase() === clean(title).toLowerCase());
  if (!found) throw new Error(`Ambiguous sheet not found: ${title}`);
  return found.id;
}

async function readSheet(env, title) {
  const id = await apiSheetId(env, title);
  const envelope = await ambi(env, `/sheets/${id}/range?spec=${encodeURIComponent("Sheet1!A1:Z100")}`);
  return { id, ...parseContent(envelope) };
}

async function loadChosen(env) {
  return readSheet(env, env.CHOSEN_SHEET_TITLE || "chosen");
}

function candidateRecord(values) {
  return {
    candidate_id: values.candidate_id,
    name: values.name,
    level: values.level || "Unknown",
    skills: values.skills || "Unknown",
    status: values.status || "Unknown",
    years: values.years || "Unknown",
    role: values.role || "Unknown",
    state: values.state || "",
    offer_amount: values.offer_amount || "",
  };
}

async function patchState(env, candidateId, state, offerAmount = "") {
  const sheet = await loadChosen(env);
  const row = sheet.rows.find(({ values }) => values.candidate_id === candidateId);
  if (!row) throw new Error("Chosen candidate not found");
  const stateHeader = sheet.headers.find(({ name }) => name === "state");
  if (!stateHeader) throw new Error("The chosen sheet is missing the state column");
  const updates = [{ cell: `${stateHeader.column}${row.rowIndex + 1}`, value: state }];
  if (state === "offer") {
    let offerHeader = sheet.headers.find(({ name }) => name === "offer_amount");
    if (!offerHeader) {
      offerHeader = { column: columnId(sheet.headers.length), name: "offer_amount" };
      updates.push({ cell: `${offerHeader.column}${sheet.headerIndex + 1}`, value: "offer_amount" });
    }
    updates.push({ cell: `${offerHeader.column}${row.rowIndex + 1}`, value: offerAmount });
  }
  await ambi(env, `/sheets/${sheet.id}/cells`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ updates }),
  });
  return { ...candidateRecord({ ...row.values, state, offer_amount: offerAmount || row.values.offer_amount }), state, offer_amount: offerAmount || row.values.offer_amount || "" };
}

function columnId(index) {
  let result = "";
  for (let value = index + 1; value > 0; value = Math.floor((value - 1) / 26)) result = String.fromCharCode(65 + ((value - 1) % 26)) + result;
  return result;
}

async function route(request, env) {
  const url = new URL(request.url);
  if (url.pathname === "/api/health") return respond({ ok: true, service: "ai-court-hr-portal" });
  if (url.pathname === "/api/candidates" && request.method === "GET") {
    const [pool, chosen] = await Promise.all([readSheet(env, env.CANDIDATE_SHEET_TITLE || "Candidate Pool"), loadChosen(env)]);
    const chosenIds = new Set(chosen.rows.map(({ values }) => values.candidate_id).filter(Boolean));
    return respond(pool.rows.map(({ values }) => candidateRecord(values)).filter((candidate) => candidate.candidate_id && !chosenIds.has(candidate.candidate_id)));
  }
  if (url.pathname === "/api/chosen" && request.method === "GET") {
    const sheet = await loadChosen(env);
    return respond(sheet.rows.map(({ values }) => candidateRecord(values)).filter((candidate) => candidate.candidate_id));
  }
  const match = url.pathname.match(/^\/api\/chosen\/([^/]+)\/state$/);
  if (match && request.method === "PATCH") {
    const body = await request.json().catch(() => ({}));
    const state = clean(body.state).toLowerCase();
    if (!VALID_STATES.has(state)) return respond({ error: "State must be offer, hired, rejected, or fired" }, 400);
    const offerAmount = clean(body.offer_amount);
    if (state === "offer" && (!offerAmount || !/^\d+(?:[.,]\d{1,2})?$/.test(offerAmount) || Number(offerAmount.replace(",", ".")) < 0)) return respond({ error: "A non-negative EUR offer amount is required" }, 400);
    const candidateId = decodeURIComponent(match[1]);
    const sheet = await loadChosen(env);
    const current = sheet.rows.find(({ values }) => values.candidate_id === candidateId)?.values.state || "";
    if (state === "fired" && current.toLowerCase() !== "hired") return respond({ error: "Only hired candidates can be fired" }, 409);
    return respond(await patchState(env, candidateId, state, state === "offer" ? offerAmount.replace(",", ".") : ""));
  }
  if (match && request.method === "POST") {
    const form = await request.formData();
    const state = clean(form.get("state")).toLowerCase();
    const offerAmount = clean(form.get("offer_amount"));
    if (!VALID_STATES.has(state)) return Response.redirect(new URL("/?error=Invalid%20candidate%20state", request.url), 303);
    if (state === "offer" && (!offerAmount || !/^\d+(?:[.,]\d{1,2})?$/.test(offerAmount) || Number(offerAmount.replace(",", ".")) < 0)) return Response.redirect(new URL("/?error=Enter%20a%20valid%20non-negative%20EUR%20offer%20amount", request.url), 303);
    try {
      await patchState(env, decodeURIComponent(match[1]), state, offerAmount.replace(",", "."));
      return Response.redirect(new URL("/?updated=1", request.url), 303);
    } catch (error) {
      return Response.redirect(new URL(`/?error=${encodeURIComponent(error instanceof Error ? error.message : "Update failed")}`, request.url), 303);
    }
  }
  return null;
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-methods": "GET, PATCH, OPTIONS", "access-control-allow-headers": "content-type" } });
    try {
      const response = await route(request, env);
      if (response) return response;
      return env.ASSETS ? env.ASSETS.fetch(request) : new Response("Not found", { status: 404 });
    } catch (error) {
      return respond({ error: error instanceof Error ? error.message : "Unexpected server error" }, 502);
    }
  },
};
