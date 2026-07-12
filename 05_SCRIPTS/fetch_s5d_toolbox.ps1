# Downloads DotNetSiemensPLCToolBoxLibrary (LGPL-2.1) + SharpZipLib from
# NuGet into 05_SCRIPTS/_s5d_toolbox/ (gitignored — the LGPL DLLs are
# fetched, never vendored, never modified). Needed once for .s5d import.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bin = Join-Path $here "_s5d_toolbox"
$tmp = Join-Path $here "_nuget_tmp"
New-Item -ItemType Directory -Force $bin | Out-Null
New-Item -ItemType Directory -Force $tmp | Out-Null

$pkgs = @(
    @{ id = "dotnetprojects.dotnetsiemensplctoolboxlibrary"; ver = "4.4.10";
       dll = "lib/net461/DotNetSiemensPLCToolBoxLibrary.dll" },
    @{ id = "sharpziplib"; ver = "1.4.2";
       dll = "lib/netstandard2.0/ICSharpCode.SharpZipLib.dll" }
)
foreach ($p in $pkgs) {
    $nupkg = Join-Path $tmp "$($p.id).nupkg"
    $url = "https://api.nuget.org/v3-flatcontainer/$($p.id)/$($p.ver)/$($p.id).$($p.ver).nupkg"
    Invoke-WebRequest -Uri $url -OutFile $nupkg -UseBasicParsing
    $dir = Join-Path $tmp $p.id
    Expand-Archive $nupkg $dir -Force
    Copy-Item (Join-Path $dir ($p.dll -replace "/", "\")) $bin -Force
}
Remove-Item $tmp -Recurse -Force
Get-ChildItem $bin
