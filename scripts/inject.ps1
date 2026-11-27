# Injects the latency_spike scenario evidence into Ergo as tagged IRC messages, one at a
# time, so you can watch the kernel react in the web UI.
#
# Prereqs: Ergo running on 127.0.0.1:6667, kernel running (scripts/run_kernel.py).
# Run:     powershell -ExecutionPolicy Bypass -File scripts/inject.ps1

$tcp = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 6667)
$writer = [System.IO.StreamWriter]::new($tcp.GetStream())
$writer.AutoFlush = $true

# Register with message-tags so Ergo relays our client-only +bb-* tags.
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
    Start-Sleep -Seconds 3   # pause so you can watch each land + the KSs react
}

Send-Evidence "e_cfg"  "0.95" "03:12 config change: db.pool.max 50 -> 5"
Send-Evidence "e_lat"  "0.99" "03:14 p99 latency rose 180ms -> 4200ms"
Send-Evidence "e_wait" "0.9"  "03:14 db connection wait time 3800ms"
Send-Evidence "e_dep"  "0.9"  "03:10 deployment of v2.4.1"
Send-Evidence "e_cpu"  "0.9"  "03:14 CPU usage 40% (within normal range)"
Send-Evidence "e_mem"  "0.85" "03:14 memory usage 95%"

Write-Host ""
Write-Host "All evidence injected. The LLM should have produced hypotheses."
Write-Host "To retract the misleading memory reading, run:  scripts/retract.ps1"
Start-Sleep -Seconds 2
$tcp.Close()
