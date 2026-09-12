# Talent Desk

Talent Desk is a Cloudflare Workers HR dashboard for reviewing candidates selected in Ambiguous's `chosen` sheet and managing their hiring state.

## Local development

```bash
npm install
npx wrangler secret put AMBIGUOUS_API_KEY
npm run dev
```

Open the local URL printed by Wrangler. The Worker keeps the Ambiguous credential server-side and exposes same-origin API routes for the UI:

- `GET /api/candidates`
- `GET /api/chosen`
- `PATCH /api/chosen/:candidate_id/state`
- `GET /api/health`

Available candidates are read from `Candidate Pool` and exclude IDs already present in `chosen`. HR actions update only the `state` column in `chosen`.

## Cloudflare deployment

Authenticate Wrangler and deploy:

```bash
npx wrangler login
npx wrangler secret put AMBIGUOUS_API_KEY
npm run deploy
```

The Worker reads sheets by title, so the Ambiguous sheet names must remain `Candidate Pool` and `chosen`. Both sheets use `candidate_id`, `name`, `level`, `skills`, `status`, `years`, and `role`; `chosen` also requires `state`.

The API key is never placed in browser code or committed files. If the key has been shared outside the intended workspace, rotate it before production deployment.
