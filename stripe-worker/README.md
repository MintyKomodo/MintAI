# MintWatch payments — Stripe embedded checkout backend

> ### `preorder.html` does NOT use this Worker
> Preorders run on a **Stripe Payment Link**, which is a hosted checkout URL. No Worker, no
> secret key, no publishable key in the HTML. The only thing `preorder.html` holds is the link
> itself, in the `PAYMENT_LINK` constant near the bottom of the file. See
> [Preorders](#preorders-payment-link) below.
>
> This Worker is still what `donate.html` needs, and its `/create-preorder-session` route is
> kept as the **alternative** path if you ever want preorder checkout embedded in the page
> instead of hosted by Stripe. Nothing calls it today.

This is the tiny serverless backend behind `donate.html`:

| Page | Route | What it charges |
|---|---|---|
| `donate.html` | `POST /create-checkout-session` | A donor-chosen amount, $1 to $10,000. |
| *(unused)* | `POST /create-preorder-session` | $639 per MintWatch, fixed in `worker.js`. Kept for the embedded-checkout option. |

It shows an **embedded** Stripe form, so donors never leave the site.

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
2. On `preorder.html`, pick a quantity → **Reserve for $639** → the form appears inline.
3. Pay with Stripe's test card `4242 4242 4242 4242`, any future date, any CVC/ZIP.
4. You should land back on the page with **"You're in."**, and see a $639 payment plus the
   shipping address in your Stripe Dashboard (test mode).
5. Confirm the price cannot be tampered with: in DevTools, change `UNIT_PRICE` to `1` and reserve
   again. Stripe should still charge **$639**, because the amount comes from `PREORDER_CENTS`
   in `worker.js`, not from the browser.
6. When happy, swap both keys to **live** (`sk_live_` / `pk_live_`) and redeploy.

---

## Preorders (Payment Link)

`preorder.html` points at a Stripe Payment Link. Everything below already exists in the
**sandbox** account `acct_1TyzHXQms4FVknLq` ("Mint Technologies sandbox"):

| Object | ID | Notes |
|---|---|---|
| Product | `prod_UyyOgp7NEPVlcm` | MintWatch — Founders Preorder, shippable, unit label "watch" |
| Price | `price_1Tz0ReQms4FVknLqFttwF7gp` | $639.00 USD one-time, tax behavior `exclusive` |
| Payment Link | `plink_1Tz0RsQms4FVknLqssGVKOZb` | `https://book.stripe.com/test_9B6dRb1A53d9gss9oXbbG00` |

Link configuration: quantity adjustable 1 to 3, billing address required, shipping address
limited to 25 countries, phone collected, promo codes on, submit button reads "Book",
redirects to `/preorder.html?reserved=1` when paid, and **`restrictions.completed_sessions.limit`
is 250**, so Stripe closes the Founders wave by itself and then shows the `inactive_message`.

### These are TEST objects
The account is a sandbox, so that URL contains `/test_` and accepts **only** Stripe test cards.
No real money can move through it. To take real preorders you must recreate the product, price,
and link in **live mode**, then paste the live URL (`https://book.stripe.com/…` with no `test_`)
into `PAYMENT_LINK` in `preorder.html`.

The page defends against getting this wrong:
- A link that is not `https://book.stripe.com/…` or `https://buy.stripe.com/…` disables the button.
- A `/test_` link **on mint-ai.tech** disables the button and says preorders are in test mode.
- A `/test_` link on localhost stays clickable, with a test-mode banner, so you can rehearse.

So publishing the site with the test link still in place cannot take fake orders. It just shows
a disabled button.

### Rehearse the flow
1. Serve the site locally and open `/preorder.html`.
2. Click **Reserve for $639**. You land on Stripe with "MintWatch — Founders Preorder", "$639.00
   per watch", and a Qty control.
3. Pay with `4242 4242 4242 4242`, any future expiry, any CVC and postcode.
4. You should be redirected to `/preorder.html?reserved=1`, which shows "You're in."
5. Check the Stripe Dashboard for the payment, the shipping address, and the phone number.

## Before you take real money
- Set your **refund policy, terms, and support email** in Stripe → Settings → Public details.
  Card networks expect a preorder to state its ship window, and Stripe may ask for it.
- Under US FTC rules, if a stated ship date slips you must offer buyers a notice and a free
  refund. `preorder.html` promises a full refund any time before shipping. Keep that promise.
- Consider holding preorder cash separately rather than spending it on ops. If you cannot
  deliver, that money has to go back.
- Stripe holds funds for a physical good shipping far out; expect a reserve or a rolling payout
  hold on a new account. Talk to Stripe support before a launch push.
- **Review the buy-now-pay-later methods.** The link currently offers Affirm, Klarna, Cash App,
  and Amazon Pay alongside cards, because payment methods default to whatever is enabled on the
  account. BNPL providers underwrite against prompt delivery, and a 2027 ship date is far outside
  what they normally expect. If you want cards only, set `payment_method_types` to `["card"]` on
  the payment link, or turn the others off in Dashboard → Settings → Payment methods.

## Notes
- Preorder price is `PREORDER_CENTS` and the per-person cap is `PREORDER_MAX_QTY`, both in `worker.js`.
  Changing the price there is the only place that matters. `UNIT_PRICE` in `preorder.html` is display only,
  so update both together or the page will quote a number it does not charge.
- To switch from a full charge to a deposit, drop `PREORDER_CENTS` (e.g. `5000` for $50) and update
  the copy on `preorder.html`.
- Donation amount limits are `$1`–`$10,000` (`MIN_CENTS` / `MAX_CENTS`).
- The Worker only accepts requests from `https://mint-ai.tech` (see `ALLOWED_ORIGIN`).
- This backend holds no data; Stripe stores the payments, addresses, and receipts.
