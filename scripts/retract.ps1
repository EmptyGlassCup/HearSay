# Retracts the misleading memory evidence (e_mem). Run after inject.ps1, while the kernel
# is up, to watch the memory-leak hypothesis and everything built on it ghost out.
#
# Run: powershell -ExecutionPolicy Bypass -File scripts/retract.ps1

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

Write-Host ">> retracting e_mem (memory reading was misread; actual 45%)"
$writer.WriteLine("@+bb-kind=retract-claim;+bb-ref=e_mem PRIVMSG #evidence :Retracting e_mem: memory reading was misread, actual 45%")
Start-Sleep -Seconds 2
$tcp.Close()

Write-Host "Retracted. Watch the graph: the memory-pressure chain should dim to ghosts."
