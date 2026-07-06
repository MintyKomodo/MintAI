# MintWatch donations — Stripe embedded checkout backend

This is the tiny serverless backend that lets `donate.html` show an **embedded**
Stripe payment form (donors never leave the site) with a **customer-chosen amount**.

A static GitHub Pages site can't safely talk to Stripe on its own (it can't hold a
secret key), so this one small Cloudflare Worker does it. It's free.

---

## One-time setup

### 1. Deploy the Worker
1. Make a free account at https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Create Worker**.
2. Give it a name (e.g. `mintwatch-donations`) and click **Deploy**.
3. Click **Edit code**, delete the sample, paste **all of `worker.js`**, and **Deploy** again.

### 2. Add your Stripe secret key (kept private on Cloudflare)
1. In the Worker: **Settings → Variables and Secrets → Add**.
2. Type: **Secret** (encrypted). 
   - **Name:** `STRIPE_SECRET_KEY`
   - **Value:** your Stripe secret key — `sk_test_...` while testing, `sk_live_...` when live
     (Stripe Dashboard → **Developers → API keys**).
3. Save and **Deploy**.

> The secret key lives ONLY here. It is never in the website or in git.

### 3. Wire the website to the Worker
Open `donate.html`, find the two lines near the bottom and fill them in:
```js
var STRIPE_PUBLISHABLE_KEY = "pk_live_REPLACE_ME";   // your Stripe PUBLISHABLE key (pk_...)
var WORKER_URL = "https://REPLACE_ME.workers.dev";   // your Worker URL, no trailing slash
```
- `STRIPE_PUBLISHABLE_KEY` — Stripe Dashboard → Developers → API keys → **Publishable key** (safe to expose).
- `WORKER_URL` — the URL shown on your Worker's page (e.g. `https://mintwatch-donations.yourname.workers.dev`).

Commit + deploy the site, and donations are live.

---

## Test it
1. Use Stripe **test mode** keys first (`sk_test_...` on the Worker, `pk_test_...` in donate.html).
2. On the donate page, pick an amount → **Continue to payment** → the form appears inline.
3. Pay with Stripe's test card `4242 4242 4242 4242`, any future date, any CVC/ZIP.
4. You should return to a **Thank you** message, and see the payment in your Stripe Dashboard (test mode).
5. When happy, swap both keys to **live** (`sk_live_` / `pk_live_`) and redeploy.

## Notes
- Amount limits are `$1`–`$10,000` (edit `MIN_CENTS` / `MAX_CENTS` in `worker.js`).
- The Worker only accepts requests from `https://mint-ai.tech` (see `ALLOWED_ORIGIN`).
- This backend holds no data; Stripe stores the payments.
