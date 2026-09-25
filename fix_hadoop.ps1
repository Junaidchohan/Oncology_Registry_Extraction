$url = 'https://github.com/cdarlint/winutils/raw/master/hadoop-3.3.5/bin/hadoop.dll'
$dest = 'C:\hadoop\bin\hadoop.dll'
Write-Host 'Downloading hadoop.dll from GitHub...'
Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
$size = (Get-Item $dest).Length
Write-Host "Downloaded: $dest"
Write-Host "Size: $size bytes"
Get-ChildItem 'C:\hadoop\bin' | Select-Object Name, Length
