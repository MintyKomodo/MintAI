# MintWatch payments — Stripe embedded checkout backend

This is the tiny serverless backend behind two pages:

| Page | Route | What it charges |
|---|---|---|
| `preorder.html` | `POST /create-preorder-session` | **$600 per MintWatch**, fixed in `worker.js`. The browser only sends a quantity (1 to 3). |
| `donate.html` | `POST /create-checkout-session` | A donor-chosen amount, $1 to $10,000. |

Both show an **embedded** Stripe form, so nobody leaves the site.

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
Open **both** `preorder.html` and `donate.html`, find these two lines near the bottom of each,
and fill them in with the same values:
```js
var STRIPE_PUBLISHABLE_KEY = "pk_live_REPLACE_ME";   // your Stripe PUBLISHABLE key (pk_...)
var WORKER_URL = "https://REPLACE_ME.workers.dev";   // your Worker URL, no trailing slash
```
- `STRIPE_PUBLISHABLE_KEY` — Stripe Dashboard → Developers → API keys → **Publishable key** (safe to expose).
- `WORKER_URL` — the URL shown on your Worker's page (e.g. `https://mintwatch-payments.yourname.workers.dev`).

Until those are filled in, the buttons stay dark and show *"Preorders are not switched on yet."*
Nothing can be charged before you paste the keys.

Commit + deploy the site and preorders are live.

---

## Test it
1. Use Stripe **test mode** keys first (`sk_test_...` on the Worker, `pk_test_...` in the pages).
2. On `preorder.html`, pick a quantity → **Reserve for $600** → the form appears inline.
3. Pay with Stripe's test card `4242 4242 4242 4242`, any future date, any CVC/ZIP.
4. You should land back on the page with **"You're in."**, and see a $600 payment plus the
   shipping address in your Stripe Dashboard (test mode).
5. Confirm the price cannot be tampered with: in DevTools, change `UNIT_PRICE` to `1` and reserve
   again. Stripe should still charge **$600**, because the amount comes from `PREORDER_CENTS`
   in `worker.js`, not from the browser.
6. When happy, swap both keys to **live** (`sk_live_` / `pk_live_`) and redeploy.

## Before you take real money
- Set your **refund policy, terms, and support email** in Stripe → Settings → Public details.
  Card networks expect a preorder to state its ship window, and Stripe may ask for it.
- Under US FTC rules, if a stated ship date slips you must offer buyers a notice and a free
  refund. `preorder.html` promises a full refund any time before shipping. Keep that promise.
- Consider holding preorder cash separately rather than spending it on ops. If you cannot
  deliver, that money has to go back.
- Stripe holds funds for a physical good shipping far out; expect a reserve or a rolling payout
  hold on a new account. Talk to Stripe support before a launch push.

## Notes
- Preorder price is `PREORDER_CENTS` and the per-person cap is `PREORDER_MAX_QTY`, both in `worker.js`.
  Changing the price there is the only place that matters. `UNIT_PRICE` in `preorder.html` is display only,
  so update both together or the page will quote a number it does not charge.
- To switch from a full charge to a deposit, drop `PREORDER_CENTS` (e.g. `5000` for $50) and update
  the copy on `preorder.html`.
- Donation amount limits are `$1`–`$10,000` (`MIN_CENTS` / `MAX_CENTS`).
- The Worker only accepts requests from `https://mint-ai.tech` (see `ALLOWED_ORIGIN`).
- This backend holds no data; Stripe stores the payments, addresses, and receipts.
