# Injects the checkout_timeout_amplification scenario evidence into Ergo, one item at a
# time, so you can watch two LLM agents react in the web UI.
#
# Prereqs: Ergo on 127.0.0.1:6667, kernel running (scripts/run_multiagent.py).
# Run:     powershell -ExecutionPolicy Bypass -File scripts/inject_checkout.ps1

$tcp = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 6667)
$writer = [System.IO.StreamWriter]::new($tcp.GetStream())
$writer.AutoFlush = $true

$writer.WriteLine("CAP REQ :message-tags")
$writer.WriteLine("NICK injector")
$writer.WriteLine("USER injector 0 * :Injector")
$writer.WriteLine("CAP END")
Start-Sleep -Seconds 1
$writer.WriteLine("JOIN #evidence")
Start-Sleep -Seconds 1

function Send-Evidence($id, $conf, $text) {
    $line = "@+bb-kind=claim;+bb-id=$id;+bb-claim-kind=evidence;+bb-level=0;+bb-conf=$conf PRIVMSG #evidence :$text"
    Write-Host ">> injecting $id"
    $writer.WriteLine($line)
    Start-Sleep -Seconds 4   # pause so each lands and the agents can react
}

Send-Evidence "e_deploy"  "0.85" "02:58 deploy of checkout-api build 2231 completed on all 6 hosts"
Send-Evidence "e_p99"     "0.88" "03:00-03:30 checkout-api p99 latency 11.2s (baseline 340ms), 5xx 0.3%"
Send-Evidence "e_replag"  "0.75" "03:01 db-replica-2 replication lag 14s"
Send-Evidence "e_provlat" "0.95" "02:59 onward payments-provider probe p95 9400ms (baseline 450ms)"
Send-Evidence "e_cpu"     "0.92" "03:00-03:30 checkout hosts avg cpu 38%, 1120 rps (baseline 1100)"
Send-Evidence "e_tmocfg"  "0.94" "config r88 6 days ago: payments client timeout_ms 2000 -> 30000"
Send-Evidence "e_pool"    "0.86" "03:02 host 3 worker pool in_use 64/64, request queue depth 410"
Send-Evidence "e_dbq"     "0.9"  "03:00-03:30 db primary query p99 14ms, slow query log empty"
Send-Evidence "e_threads" "0.88" "03:04 host 3 thread dump: 64/64 workers in socket_read to payments-provider:443"

Write-Host ""
Write-Host "All evidence injected. Watch the two agents propose competing hypotheses."
Write-Host "To retract the misleading leads, run:  scripts/retract_checkout.ps1"
Start-Sleep -Seconds 2
$tcp.Close()
