# Retracts the two misleading leads (e_deploy, e_replag) for the checkout scenario.
# Run after inject_checkout.ps1, while the kernel is up, to watch the deploy-blame and
# db-replica hypotheses ghost out while the timeout/provider explanation survives.
#
# Run: powershell -ExecutionPolicy Bypass -File scripts/retract_checkout.ps1

$tcp = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 6667)
$writer = [System.IO.StreamWriter]::new($tcp.GetStream())
$writer.AutoFlush = $true

$writer.WriteLine("CAP REQ :message-tags")
$writer.WriteLine("NICK operator")
$writer.WriteLine("USER operator 0 * :Operator")
$writer.WriteLine("CAP END")
Start-Sleep -Seconds 1
$writer.WriteLine("JOIN #evidence")
Start-Sleep -Seconds 1

Write-Host ">> retracting e_deploy (coincident deploy, not causal)"
$writer.WriteLine("@+bb-kind=retract-claim;+bb-ref=e_deploy PRIVMSG #evidence :Retracting e_deploy: build 2231 was a no-op config bump, ruled out")
Start-Sleep -Seconds 3

Write-Host ">> retracting e_replag (replica lag irrelevant; checkout reads primary)"
$writer.WriteLine("@+bb-kind=retract-claim;+bb-ref=e_replag PRIVMSG #evidence :Retracting e_replag: checkout reads primary, replica lag not on the path")
Start-Sleep -Seconds 2
$tcp.Close()

Write-Host "Retracted. Hypotheses built on those leads should dim; the timeout/provider chain should remain."
