# Windows Laptop: run from any directory, no bash required.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location ..
$subnet = '192.168.10'
if ($args -contains '--local') { $subnet = '127.0.0' }
py -m central.dashboard --subnet $subnet
