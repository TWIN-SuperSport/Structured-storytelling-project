# BASE LAN-only recovery (2026-10-02 JST)

Source main 97622ae; local unmerged 8725ef2 relay-client identification cherry-picked with history retained. Mac/BASE metadata files preserved in backup and ignored, never deleted. All prior tracked changes absent.

URL: https://reverse-plot-tool.lab.ktsys.jp
BASE: /home/shino/source/repos/upstream/Structured-storytelling-project
Mac: /Volumes/SSD250GBUSB/source/repos/upstream/Structured-storytelling-project

App nginx connects to wos-proxy-network. All three containers restart unless-stopped. No new host ports. App nginx trusts only current proxy 172.22.0.4 and Apache bridge 172.22.0.1, resolves X-Forwarded-For recursively, permits 192.168.1.0/24 and denies all others. Host/network admins are trusted. Recheck trust after topology changes; never allow Docker ranges broadly.

LAN testing used curl --noproxy "*" --resolve reverse-plot-tool.lab.ktsys.jp:443:192.168.1.23. Public DNS is unchanged; browser access requires LAN name resolution or may receive 403.

Verified LAN root 200 with TLS valid, public and forged LAN header requests 403. Health ok. One dummy epilogue request through the job API returned 200 with two choices. Initial request after API recreation arrived before readiness and returned nginx 502; only ready-state request reached generation. Compose/nginx/PHP/diff checks passed. Restart/power-cycle and complete multi-stage user workflow were not tested.

Disk remained about 8.6GB available. No prune or data deletion. Shared proxy, relay, DB, recordings, DNS and certificates unchanged.

Backup: /home/shino/work/tmp/reverse-recovery-20261002-102211. public/index.php made readable (644). Existing composer.lock retained. Old VPS deployment workflow disabled in GitHub and changed to manual no-op. CI retained.

Rollback: stop only reverse containers, restore retained code/config if needed. No shared network removal or prune. Original metadata stays preserved. Old VPS instructions are historical.
