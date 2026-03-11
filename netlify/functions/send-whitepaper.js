'use strict';
// Netlify serverless function — sends the White Paper PDF link via email (Resend)
// Triggered when someone submits the "Get the White Paper" sign-up form.

const { Resend } = require('resend');

exports.handler = async (event) => {
  // Only accept POST
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  let name, email;
  try {
    ({ name, email } = JSON.parse(event.body));
  } catch {
    return { statusCode: 400, body: 'Invalid request body' };
  }

  if (!name || !email) {
    return { statusCode: 400, body: 'Name and email are required' };
  }

  // Build the PDF download URL from the current site
  const host = event.headers['x-forwarded-host'] || event.headers.host || '';
  const siteUrl = process.env.SITE_URL || (host ? `https://${host}` : '');
  // Exact filename: "The Compound Intelligence Framework — White Paper 1.pdf"
  const pdfUrl = `${siteUrl}/The%20Compound%20Intelligence%20Framework%20%E2%80%94%20White%20Paper%201.pdf`;

  const resend = new Resend(process.env.RESEND_API_KEY);

  try {
    await resend.emails.send({
      from: process.env.FROM_EMAIL || 'Compound Intelligence Partners <hello@compoundintelligence.com>',
      to: email,
      subject: 'Your White Paper: The Compound Intelligence Framework',
      html: buildWhitepaperEmail(name, pdfUrl),
    });

    console.log(`White paper email sent to ${email}`);

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ success: true }),
    };
  } catch (err) {
    console.error('Resend error:', err);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Failed to send email' }),
    };
  }
};

// ── Email template ─────────────────────────────────────────────────────────────
function buildWhitepaperEmail(name, pdfUrl) {
  const firstName = name.split(' ')[0];
  return `
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>The Compound Intelligence Framework — White Paper</title>
</head>
<body style="margin:0; padding:0; background:#F1F5F9; font-family:Arial,Helvetica,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#F1F5F9; padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" role="presentation"
             style="background:#FFFFFF; border-radius:12px; overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,.08); max-width:600px; width:100%;">

        <!-- Header — Teal accent for white paper (more premium feel) -->
        <tr>
          <td style="background:linear-gradient(135deg,#060D1F 0%,#0F2940 100%);
                     padding:44px 48px 40px; text-align:center;
                     border-bottom:4px solid #0D9488;">
            <p style="margin:0 0 12px; font-size:11px; font-weight:700; letter-spacing:.14em;
                      color:rgba(255,255,255,.4); text-transform:uppercase;">
              Compound Intelligence Partners — White Paper
            </p>
            <h1 style="margin:0 0 14px; font-size:26px; font-weight:700; color:#FFFFFF;
                       line-height:1.3;">
              The Compound Intelligence Framework™
            </h1>
            <p style="margin:0; font-size:14px; color:rgba(255,255,255,.55); line-height:1.5;">
              Context Engineering · Agentic Workflows · Intelligence Graphs
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:40px 48px 36px;">
            <p style="margin:0 0 20px; font-size:16px; color:#334155; line-height:1.6;">
              Hi ${firstName},
            </p>
            <p style="margin:0 0 20px; font-size:15px; color:#475569; line-height:1.7;">
              Thank you for requesting
              <strong style="color:#1E293B;">The Compound Intelligence Framework™</strong>
              white paper. This paper describes the next-level AI challenges facing growing businesses
              — and the integrated architecture that solves them.
            </p>
            <p style="margin:0 0 20px; font-size:15px; color:#475569; line-height:1.7;">
              These are leading-edge best practices — not bleeding-edge experiments.
              Everything in this paper is deployable today.
            </p>

            <!-- Divider with accent -->
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                   style="margin:24px 0;">
              <tr>
                <td style="border-top:2px solid #0D9488; opacity:.3;"></td>
              </tr>
            </table>

            <p style="margin:0 0 16px; font-size:14px; font-weight:700; color:#1E293B;
                      letter-spacing:.04em; text-transform:uppercase;">
              What's inside
            </p>

            <!-- Bullet points -->
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                   style="margin-bottom:32px;">
              ${[
                'Why piecemeal AI adoption creates compounding technical debt',
                'Brand Brain™ — the persistent knowledge architecture that makes AI coherent',
                'The five-agent AI workforce and what each agent produces',
                'Compound Intelligence Graph™ — the self-improving knowledge layer',
                'Data sovereignty: why owning your intelligence beats renting it from cloud platforms',
                'The exact implementation path for $1M–$25M businesses',
              ].map(pt => `
              <tr>
                <td width="24" valign="top"
                    style="padding:0 12px 14px 0; color:#0D9488; font-size:16px;">→</td>
                <td style="padding:0 0 14px; font-size:14px; color:#475569; line-height:1.6;">
                  ${pt}
                </td>
              </tr>`).join('')}
            </table>

            <!-- CTA Button -->
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                   style="margin-bottom:36px;">
              <tr>
                <td align="center">
                  <a href="${pdfUrl}"
                     style="display:inline-block; background:#0D9488; color:#FFFFFF;
                            font-size:16px; font-weight:700; text-decoration:none;
                            padding:16px 40px; border-radius:8px;
                            letter-spacing:.02em;">
                    Download the White Paper →
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 16px; font-size:14px; color:#94A3B8; line-height:1.6;">
              If the button above doesn't work, copy and paste this link into your browser:
            </p>
            <p style="margin:0 0 32px; font-size:13px; word-break:break-all;">
              <a href="${pdfUrl}" style="color:#0D9488; text-decoration:none;">${pdfUrl}</a>
            </p>

            <hr style="border:none; border-top:1px solid #E2E8F0; margin:0 0 28px;"/>

            <p style="margin:0 0 8px; font-size:14px; color:#475569; line-height:1.6;">
              If you'd like to explore what this architecture would look like for your
              specific business, we'd love to talk. Just reply to this email to schedule
              a complimentary Compound Intelligence Assessment.
            </p>
            <p style="margin:0; font-size:14px; color:#475569;">
              — The Compound Intelligence Partners Team
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#F8FAFC; padding:24px 48px; text-align:center;
                     border-top:1px solid #E2E8F0;">
            <p style="margin:0 0 8px; font-size:12px; color:#94A3B8;">
              © 2026 Compound Intelligence Partners. All rights reserved.
            </p>
            <p style="margin:0; font-size:12px; color:#94A3B8;">
              You're receiving this because you requested our white paper.
              No spam — ever.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>
  `.trim();
}
