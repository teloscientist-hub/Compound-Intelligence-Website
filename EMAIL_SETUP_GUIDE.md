# Email Delivery Setup Guide
## Compound Intelligence Partners Website

This guide walks you through going live with email delivery in about 20 minutes.

---

## How it works

When someone submits a form on the website, a serverless function running on Netlify's servers fires automatically. It calls the **Resend** email API, which sends a branded HTML email with a PDF download link directly to the subscriber.

- **Free Report form** → `netlify/functions/send-report.js` → sends *Turn AI Tools Into Profitable Workflows.pdf*
- **White Paper form** → `netlify/functions/send-whitepaper.js` → sends *The Compound Intelligence Framework — White Paper 1.pdf*

---

## Step 1 — Create a free Resend account

1. Go to **[resend.com](https://resend.com)** and sign up (free)
2. In the Resend dashboard, click **API Keys → Create API Key**
3. Name it `compound-intelligence-site`, set permission to **Sending access**
4. Copy the key — you'll only see it once. Save it somewhere safe.

---

## Step 2 — Verify your sending domain

Resend requires you to verify the domain you send email *from* (e.g., `compoundintelligence.com`).

1. In the Resend dashboard, go to **Domains → Add Domain**
2. Enter your domain name
3. Resend will give you 3–4 DNS records (TXT and MX) to add to your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.)
4. Add those records in your registrar's DNS settings
5. Click **Verify** in Resend — verification usually takes 5–30 minutes

> **While testing**, you can skip domain verification and send to the email address you signed up with on Resend.

---

## Step 3 — Deploy to Netlify

### Option A — Drag and drop (simplest)

1. Go to **[netlify.com](https://netlify.com)** and create a free account
2. From your Netlify dashboard, click **Add new site → Deploy manually**
3. Drag the entire **Compound-Intelligence** folder onto the upload area
4. Netlify will deploy the site and give you a URL like `https://amazing-panda-123.netlify.app`

### Option B — Git deployment (recommended for ongoing updates)

1. Push this folder to a GitHub repository
2. In Netlify: **Add new site → Import an existing project → GitHub**
3. Select your repository
4. Build settings:
   - **Build command**: leave empty (or `npm install`)
   - **Publish directory**: `.` (a period — the root)
5. Click **Deploy site**

---

## Step 4 — Set environment variables in Netlify

This is where you plug in your API key and settings.

1. In your Netlify site dashboard, go to **Site configuration → Environment variables**
2. Add these variables:

| Variable | Value | Description |
|---|---|---|
| `RESEND_API_KEY` | `re_xxxxxxxxxxxx` | Your Resend API key from Step 1 |
| `FROM_EMAIL` | `hello@compoundintelligence.com` | The "from" address (must match your verified domain) |
| `SITE_URL` | `https://compoundintelligence.com` | Your live site URL (no trailing slash) |

3. After adding variables, **redeploy the site** (Deploys → Trigger deploy)

---

## Step 5 — Connect your custom domain (optional)

1. In Netlify: **Domain management → Add custom domain**
2. Enter `compoundintelligence.com`
3. Update your domain's nameservers to point to Netlify (Netlify will show you the exact values)
4. Netlify automatically provisions an SSL certificate

---

## Testing

Once deployed, test both forms:

1. Submit the **Free Guide** form with a real email address
2. Submit the **White Paper** form with a real email address
3. Check your inbox — both emails should arrive within 30 seconds
4. If you don't see them, check your spam folder and Netlify's **Functions** log (in your site dashboard under **Functions**)

---

## File checklist

Make sure these files are all in your deployment folder:

```
Compound-Intelligence/
├── index.html                                          ← updated with both forms
├── netlify.toml                                        ← Netlify config
├── package.json                                        ← declares Resend dependency
├── Turn AI Tools Into Profitable Workflows.pdf         ← free report PDF
├── The Compound Intelligence Framework — White Paper 1.pdf  ← white paper PDF
└── netlify/
    └── functions/
        ├── send-report.js                              ← free report email function
        └── send-whitepaper.js                          ← white paper email function
```

---

## Resend free tier

Resend's free plan includes **3,000 emails/month** and **100/day** — more than enough to get started. Paid plans start at $20/month for 50,000 emails.

---

## Troubleshooting

**"Failed to send email" on form submit**
- Check that `RESEND_API_KEY` is set in Netlify environment variables
- Check the Netlify Functions log for the exact error
- Make sure your sending domain is verified in Resend

**PDFs return 404**
- Make sure the PDF files are in the root of your deployment folder
- File names must match exactly (including the em dash `—` in the white paper name)

**Emails going to spam**
- Complete domain verification in Resend (add all DNS records)
- Make sure `FROM_EMAIL` matches your verified domain

---

Questions? Reply to any email sent through the system — or reach out directly.
