import csv
from io import StringIO

from flask import Blueprint, Response, current_app, render_template
from flask_login import current_user, login_required

from app.authz import permission_required
from app.models import ConversionEvent
from app.tenancy import TenantGuard


integrations_bp = Blueprint("integrations", __name__, url_prefix="/integrations")


def _build_embed_snippet(clinic_slug, api_key, base_url):
    snippet = """
<form id="crmLeadForm">
  <input name="first_name" required>
  <input name="last_name" required>
  <input name="email" type="email">
  <input name="phone">
  <input name="clinic_slug" value="__CLINIC_SLUG__" type="hidden">
  <input name="utm_source" type="hidden">
  <input name="utm_medium" type="hidden">
  <input name="utm_campaign" type="hidden">
  <input name="utm_term" type="hidden">
  <input name="utm_content" type="hidden">
  <input name="gclid" type="hidden">
  <input name="fbclid" type="hidden">
  <input name="company_website" type="text" style="display:none">
  <button type="submit">Send</button>
</form>
<script>
  const p = new URLSearchParams(window.location.search);
  ['utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','fbclid'].forEach((k) => {
    const el = document.querySelector('[name="' + k + '"]');
    if (el) el.value = p.get(k) || '';
  });

  document.getElementById('crmLeadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    data.landing_page_url = window.location.href;
    data.referrer_url = document.referrer || '';

    await fetch('__BASE_URL__/api/v1/leads', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': '__API_KEY__'
      },
      body: JSON.stringify(data)
    });
  });
</script>
"""
    return (
        snippet.replace("__CLINIC_SLUG__", clinic_slug)
        .replace("__API_KEY__", api_key)
        .replace("__BASE_URL__", base_url)
    )


@integrations_bp.route("/")
@login_required
@permission_required("integrations.manage")
def index():
    conversions = TenantGuard.scoped_query(ConversionEvent).order_by(ConversionEvent.created_at.desc()).limit(200).all()

    snippet = _build_embed_snippet(
        clinic_slug=current_user.clinic.slug,
        api_key=current_app.config["LEAD_API_KEY"],
        base_url=current_app.config.get("PUBLIC_BASE_URL", ""),
    )

    return render_template("integrations/index.html", conversions=conversions, snippet=snippet)


@integrations_bp.route("/google-ads-export.csv")
@login_required
@permission_required("integrations.manage")
def google_ads_export():
    events = TenantGuard.scoped_query(ConversionEvent).filter(ConversionEvent.gclid.isnot(None)).order_by(ConversionEvent.conversion_time.desc()).all()

    stream = StringIO()
    fieldnames = ["gclid", "conversion_name", "conversion_time", "conversion_value", "currency", "order_id"]
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()

    for event in events:
        writer.writerow(
            {
                "gclid": event.gclid,
                "conversion_name": event.conversion_name,
                "conversion_time": event.conversion_time.strftime("%Y-%m-%d %H:%M:%S+00:00"),
                "conversion_value": event.conversion_value,
                "currency": event.currency,
                "order_id": event.lead_id,
            }
        )

    return Response(stream.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=google_ads_offline_conversions.csv"})
