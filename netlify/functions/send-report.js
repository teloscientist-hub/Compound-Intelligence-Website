'use strict';
// Netlify serverless function — sends the free report PDF link via email (Resend)
// Triggered when someone submits the "Turn AI Tools Into Profitable Workflows" sign-up form.

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
  const pdfUrl = `${siteUrl}/Turn%20AI%20Tools%20Into%20Profitable%20Workflows.pdf`;

  const resend = new Resend(process.env.RESEND_API_KEY);

  try {
    await resend.emails.send({
      from: process.env.FROM_EMAIL || 'Compound Intelligence Partners <hello@compoundintelligence.com>',
      to: email,
      subject: 'Your Free Guide: Turn AI Tools Into Profitable Workflows',
      html: buildReportEmail(name, pdfUrl),
    });

    // Optional: log to console for Netlify function logs
    console.log(`Report email sent to ${email}`);

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
function buildReportEmail(name, pdfUrl) {
  const firstName = name.split(' ')[0];
  return `
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Your Free Guide</title>
</head>
<body style="margin:0; padding:0; background:#F1F5F9; font-family:Arial,Helvetica,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#F1F5F9; padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" role="presentation"
             style="background:#FFFFFF; border-radius:12px; overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,.08); max-width:600px; width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#060D1F 0%,#1E3A5F 100%);
                     padding:40px 48px 36px; text-align:center;">
            <p style="margin:0 0 16px; font-size:11px; font-weight:700; letter-spacing:.14em;
                      color:rgba(255,255,255,.45); text-transform:uppercase;">
              Compound Intelligence Partners
            </p>
            <h1 style="margin:0 0 12px; font-size:26px; font-weight:700; color:#FFFFFF;
                       line-height:1.3;">
              Turn AI Tools Into<br/>Profitable Workflows
            </h1>
            <p style="margin:0; font-size:15px; color:rgba(255,255,255,.6);">
              Your free guide is ready to download.
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
              Thank you for your interest — your copy of
              <strong style="color:#1E293B;">Turn AI Tools Into Profitable Workflows</strong>
              is ready. Inside you'll find the exact framework for moving from scattered AI
              experiments to an agentic, brand-congruent system that compounds in value over time.
            </p>
            <p style="margin:0 0 32px; font-size:15px; color:#475569; line-height:1.7;">
              What's covered:
            </p>

            <!-- Bullet points -->
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                   style="margin-bottom:32px;">
              ${[
                'The four stages of AI integration — and where most businesses get stuck',
                'What Brand Brain™ is and why it changes everything',
                'How a five-agent AI team runs your content without constant direction',
                'Why a self-improving knowledge graph is the missing piece',
                'The 7–10 day path from zero to a working AI system',
              ].map(pt => `
              <tr>
                <td width="24" valign="top"
                    style="padding:0 12px 12px 0; color:#0D9488; font-size:16px;">✓</td>
                <td style="padding:0 0 12px; font-size:14px; color:#475569; line-height:1.6;">
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
                     style="display:inline-block; background:#2563EB; color:#FFFFFF;
                            font-size:16px; font-weight:700; text-decoration:none;
                            padding:16px 40px; border-radius:8px;
                            letter-spacing:.02em;">
                    Download Your Free Guide →
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 16px; font-size:14px; color:#94A3B8; line-height:1.6;">
              If the button above doesn't work, copy and paste this link into your browser:
            </p>
            <p style="margin:0 0 32px; font-size:13px; word-break:break-all;">
              <a href="${pdfUrl}" style="color:#2563EB; text-decoration:none;">${pdfUrl}</a>
            </p>

            <hr style="border:none; border-top:1px solid #E2E8F0; margin:0 0 28px;"/>

            <p style="margin:0 0 8px; font-size:14px; color:#475569; line-height:1.6;">
              Questions or want to talk about implementing these systems in your business?
              Simply reply to this email — we respond to every message.
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
              You're receiving this because you requested our free guide.
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
