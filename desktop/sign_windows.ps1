param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = 'Stop'
if (-not $env:AURORA_SIGNING_PFX_BASE64) {
    Write-Host 'No publisher certificate configured. Output remains unsigned.'
    exit 0
}
$pfx = Join-Path $env:RUNNER_TEMP ('aurora-signing-' + [guid]::NewGuid().ToString() + '.pfx')
try {
    [IO.File]::WriteAllBytes($pfx,[Convert]::FromBase64String($env:AURORA_SIGNING_PFX_BASE64))
    $password = ConvertTo-SecureString $env:AURORA_SIGNING_PFX_PASSWORD -AsPlainText -Force
    $cert = Get-PfxCertificate -FilePath $pfx -Password $password
    $eku = @($cert.EnhancedKeyUsageList | ForEach-Object {$_.ObjectId.Value})
    if ('1.3.6.1.5.5.7.3.3' -notin $eku) { throw 'Certificate is not valid for code signing.' }
    $chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
    if (-not $chain.Build($cert)) { throw 'Certificate is not trusted by Windows. Refusing to label a self-signed certificate as a trusted signature.' }
    $signtool = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe' | Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $signtool) { throw 'Windows SDK SignTool not found.' }
    & $signtool.FullName sign /f $pfx /p $env:AURORA_SIGNING_PFX_PASSWORD /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $Target
    if ($LASTEXITCODE -ne 0) { throw 'Authenticode signing failed.' }
    $result = Get-AuthenticodeSignature $Target
    if ($result.Status -ne 'Valid') { throw 'Windows did not validate the signature.' }
    Write-Host ('Trusted signature verified: ' + $result.SignerCertificate.Subject)
} finally {
    Remove-Item $pfx -Force -ErrorAction SilentlyContinue
}
