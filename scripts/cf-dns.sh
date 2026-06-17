#!/usr/bin/env bash
# Create/update the Cloudflare CNAME for the front end → Render static site.
#
# wrangler can't manage DNS records, so this uses the Cloudflare REST API.
# Requires an API token with Zone:Read + DNS:Edit on the stagehopper.app zone:
#   https://dash.cloudflare.com/profile/api-tokens  (template: "Edit zone DNS")
#
# Usage:
#   export CLOUDFLARE_API_TOKEN=...           # the DNS-scoped token
#   ./scripts/cf-dns.sh worldcup-web.onrender.com   # the target Render shows you
#
# Defaults: name=worldcup.stagehopper.app, zone=stagehopper.app, proxied=false
# (Render manages TLS, so start DNS-only / grey-cloud; you can proxy later.)
set -o errexit

TARGET="${1:?Pass the Render CNAME target, e.g. worldcup-web.onrender.com}"
NAME="${DNS_NAME:-worldcup.stagehopper.app}"
ZONE="${DNS_ZONE:-stagehopper.app}"
PROXIED="${DNS_PROXIED:-false}"
: "${CLOUDFLARE_API_TOKEN:?Set CLOUDFLARE_API_TOKEN (Zone:Read + DNS:Edit)}"

api() { curl -sf -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
              -H "Content-Type: application/json" "$@"; }
base="https://api.cloudflare.com/client/v4"

zone_id=$(api "$base/zones?name=$ZONE" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"][0]["id"])')
echo "Zone $ZONE → $zone_id"

rec_id=$(api "$base/zones/$zone_id/dns_records?name=$NAME&type=CNAME" \
  | python3 -c 'import sys,json;r=json.load(sys.stdin)["result"];print(r[0]["id"] if r else "")')

body=$(printf '{"type":"CNAME","name":"%s","content":"%s","ttl":1,"proxied":%s}' "$NAME" "$TARGET" "$PROXIED")

if [ -n "$rec_id" ]; then
  echo "Updating existing record $rec_id → $TARGET"
  api -X PUT "$base/zones/$zone_id/dns_records/$rec_id" --data "$body" >/dev/null
else
  echo "Creating CNAME $NAME → $TARGET"
  api -X POST "$base/zones/$zone_id/dns_records" --data "$body" >/dev/null
fi
echo "Done. $NAME is now a CNAME → $TARGET (proxied=$PROXIED)"
