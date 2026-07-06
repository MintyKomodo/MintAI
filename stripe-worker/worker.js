/**
 * MintWatch donations — Cloudflare Worker (Stripe Embedded Checkout backend)
 *
 * WHAT THIS IS: a tiny serverless endpoint that creates Stripe Checkout
 * Sessions so donate.html can show an EMBEDDED payment form (no redirect).
 *
 * SETUP (once):
 *   1. Create a free Cloudflare account -> Workers & Pages -> Create Worker.
 *   2. Paste this whole file into the editor and Deploy.
 *   3. Worker Settings -> Variables -> add an ENCRYPTED secret:
 *        Name:  STRIPE_SECRET_KEY
 *        Value: your Stripe secret key (sk_live_... or sk_test_...)
 *   4. Copy the Worker URL (https://xxxx.workers.dev) into donate.html (WORKER_URL).
 *
 * SECURITY: the secret key lives ONLY here as a Cloudflare secret. It is never
 * in the website or in this source file. The website only uses your PUBLISHABLE
 * key (pk_...), which is safe to expose.
 *
 * ROUTES:
 *   POST /create-checkout-session   body {"amount": <dollars>}   -> { clientSecret }
 *   GET  /session-status?session_id=cs_...                       -> { status, payment_status }
 */

const ALLOWED_ORIGIN = "https://mint-ai.tech";
const RETURN_URL = "https://mint-ai.tech/donate.html?session_id={CHECKOUT_SESSION_ID}";
const MIN_CENTS = 100;       // $1 minimum
const MAX_CENTS = 1000000;   // $10,000 maximum

function cors(resp) {
  resp.headers.set("Access-Control-Allow-Origin", ALLOWED_ORIGIN);
  resp.headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  resp.headers.set("Access-Control-Allow-Headers", "Content-Type");
  resp.headers.set("Vary", "Origin");
  return resp;
}

function json(obj, status) {
  return cors(new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { "Content-Type": "application/json" },
  }));
}

async function stripeApi(path, secretKey, method, form) {
  const opts = { method: method, headers: { Authorization: "Bearer " + secretKey } };
  if (form) {
    opts.headers["Content-Type"] = "application/x-www-form-urlencoded";
    opts.body = form;
  }
  const r = await fetch("https://api.stripe.com/v1/" + path, opts);
  return r.json();
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return cors(new Response(null, { status: 204 }));
    }
    if (!env.STRIPE_SECRET_KEY) {
      return json({ error: "Server not configured (missing STRIPE_SECRET_KEY)." }, 500);
    }

    // Create an embedded Checkout Session for a donation of {amount} dollars
    if (request.method === "POST" && url.pathname === "/create-checkout-session") {
      let body;
      try { body = await request.json(); } catch (e) { return json({ error: "Bad request." }, 400); }
      const cents = Math.round(Number(body.amount) * 100);
      if (!Number.isFinite(cents) || cents < MIN_CENTS || cents > MAX_CENTS) {
        return json({ error: "Please enter an amount between $1 and $10,000." }, 400);
      }
      const form = new URLSearchParams();
      form.set("mode", "payment");
      form.set("ui_mode", "embedded");
      form.set("return_url", RETURN_URL);
      form.set("submit_type", "donate");
      form.set("line_items[0][quantity]", "1");
      form.set("line_items[0][price_data][currency]", "usd");
      form.set("line_items[0][price_data][unit_amount]", String(cents));
      form.set("line_items[0][price_data][product_data][name]", "MintWatch Support");
      const session = await stripeApi("checkout/sessions", env.STRIPE_SECRET_KEY, "POST", form);
      if (session.error) {
        return json({ error: (session.error && session.error.message) || "Stripe error." }, 400);
      }
      return json({ clientSecret: session.client_secret });
    }

    // Report a session's status for the thank-you page
    if (request.method === "GET" && url.pathname === "/session-status") {
      const id = url.searchParams.get("session_id");
      if (!id) return json({ error: "Missing session_id." }, 400);
      const session = await stripeApi("checkout/sessions/" + encodeURIComponent(id), env.STRIPE_SECRET_KEY, "GET", null);
      if (session.error) {
        return json({ error: (session.error && session.error.message) || "Stripe error." }, 400);
      }
      return json({ status: session.status, payment_status: session.payment_status });
    }

    return json({ error: "Not found." }, 404);
  },
};
