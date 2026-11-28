# Seeds the exfil_stale_geoip scenario into Ergo: 10 evidence facts + 8 pre-built
# intermediate hypotheses + their justifications. Two linking hypotheses (h_foreign,
# h_hijack) and both conclusions are DELIBERATELY NOT seeded - they are injected live /
# drawn by the LLM during the demo (see scripts/demo_script.md).
#
# Prereqs: Ergo on 127.0.0.1:6667, kernel running (scripts/run_kernel.py).
# Run:     powershell -ExecutionPolicy Bypass -File scripts/inject_geoip.ps1

$tcp = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 6667)
$writer = [System.IO.StreamWriter]::new($tcp.GetStream())
$writer.AutoFlush = $true

$writer.WriteLine("CAP REQ :message-tags")
$writer.WriteLine("NICK monitor")
$writer.WriteLine("USER monitor 0 * :Monitoring")
$writer.WriteLine("CAP END")
Start-Sleep -Seconds 1
$writer.WriteLine("JOIN #evidence")
$writer.WriteLine("JOIN #hypotheses")
Start-Sleep -Seconds 1

function Send-Evidence($id, $conf, $text) {
    $line = "@+bb-kind=claim;+bb-id=$id;+bb-claim-kind=evidence;+bb-level=0;+bb-conf=$conf PRIVMSG #evidence :$text"
    Write-Host ">> evidence $id"
    $writer.WriteLine($line); Start-Sleep -Milliseconds 800
}
function Send-Claim($id, $level, $conf, $text) {
    $line = "@+bb-kind=claim;+bb-id=$id;+bb-claim-kind=hypothesis;+bb-level=$level;+bb-conf=$conf PRIVMSG #hypotheses :$text"
    Write-Host ">> hypothesis $id"
    $writer.WriteLine($line); Start-Sleep -Milliseconds 800
}
function Send-Justify($id, $concl, $premises, $text) {
    $line = "@+bb-kind=justify;+bb-id=$id;+bb-conclusion=$concl;+bb-premises=$premises PRIVMSG #hypotheses :$text"
    Write-Host ">> justify $id"
    $writer.WriteLine($line); Start-Sleep -Milliseconds 800
}

# Evidence
Send-Evidence "e_geo"       "0.85" "GeoIP lookup for 203.0.113.45 using snapshot dated 2024-02: Singapore"
Send-Evidence "e_srcip"     "0.96" "DB audit: session 88213 opened 02:39 as account mchen from 203.0.113.45"
Send-Evidence "e_newip"     "0.88" "Auth logs: no sessions from 203.0.113.45 in the previous 90 days"
Send-Evidence "e_offhrs"    "0.9"  "mchen had no logins 22:00-06:00 in 90 days; session 88213 ran 02:39-03:21"
Send-Evidence "e_ua"        "0.9"  "Session 88213 client was python-requests/2.31.0; prior mchen sessions used DBeaver 23.1"
Send-Evidence "e_xfer"      "0.97" "03:12-03:21 outbound transfer of 2.1 GB from db-prod-01 to 198.51.100.77:443"
Send-Evidence "e_dest"      "0.88" "198.51.100.77 is object storage under a domain registered 11 days ago"
Send-Evidence "e_edr"       "0.84" "02:19 EDR alert (medium, unreviewed) on WS-114 (mchen): outlook.exe spawned powershell.exe"
Send-Evidence "e_egress"    "0.92" "Change CHG-4471 on 2026-10-02: corporate egress NAT pool moved to 203.0.113.0/24"
Send-Evidence "e_noexploit" "0.9"  "WAF and DB audit for session 88213: no SQL injection, no privilege escalation"

# Pre-built intermediate hypotheses (both towers' mid-levels)
Send-Claim "h_overseas"   "1" "0.88" "Session 88213 originated from an address located overseas"
Send-Claim "h_insidenet"  "1" "0.55" "Session 88213 originated from the corporate egress pool"
Send-Claim "h_wscomp"     "1" "0.6"  "Workstation WS-114 was running attacker-controlled code at 02:19"
Send-Claim "h_infra"      "1" "0.8"  "198.51.100.77 is attacker-controlled infrastructure"
Send-Claim "h_scripted"   "1" "0.82" "Session 88213 was driven by a script, not the account owner at a GUI client"
Send-Claim "h_newloc"     "2" "0.86" "Account mchen was used from a location it had never used before"
Send-Claim "h_outsidenet" "2" "0.85" "Session 88213 originated outside the corporate network"
Send-Claim "h_credsext"   "2" "0.8"  "Valid mchen credentials were used from outside the network without exploiting a vulnerability"

# Justifications
Send-Justify "j_overseas" "h_overseas"   "e_geo,e_srcip"       "overseas location follows from the GeoIP lookup of the source address"
Send-Justify "j_newloc"   "h_newloc"     "h_overseas,e_newip"  "a never-before-seen location: overseas and unseen in 90 days"
Send-Justify "j_outside"  "h_outsidenet" "h_newloc"            "a new overseas location implies an origin outside the network"
Send-Justify "j_credsext" "h_credsext"   "h_outsidenet,e_noexploit" "external use of valid creds with no exploit"
Send-Justify "j_inside"   "h_insidenet"  "e_srcip,e_egress"    "the source address is within the new corporate egress pool"
Send-Justify "j_ws"       "h_wscomp"     "e_edr"               "the EDR alert indicates attacker-controlled code on WS-114"
Send-Justify "j_infra"    "h_infra"      "e_dest,e_xfer"       "a freshly-registered storage endpoint receiving 2.1 GB is attacker infra"
Send-Justify "j_scripted" "h_scripted"   "e_ua,e_offhrs"       "a scripted client off-hours, unlike this user's usual GUI tool"

Write-Host ""
Write-Host "Seeded. Both towers' intermediates are present; h_foreign, h_hijack, and both"
Write-Host "conclusions are supplied live. Follow scripts/demo_script.md."
Start-Sleep -Seconds 1
$tcp.Close()
