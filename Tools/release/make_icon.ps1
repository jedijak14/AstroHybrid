# Draws AstroHybrid's own icon - no game artwork is used anywhere in the public app.
#
# The mark is a flat planetary emblem: a warm off-white planet with a violet ring
# on a near-black rounded tile, plus one small sparkle. Solid fills only, so it
# stays crisp at 16 px. This is the PowerShell equivalent of
# Tools/brand/make_logo.py for people who want the icon without Python.
#
#   powershell -ExecutionPolicy Bypass -File Tools\release\make_icon.ps1
#
# Writes AstroHybrid.App\Resources\astrohybrid.png, astrohybrid-mark.png and
# astrohybrid.ico.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$out = Join-Path $root 'AstroHybrid.App\Resources'

$TILE    = [Drawing.Color]::FromArgb(255, 14, 18, 26)
$PLANET  = [Drawing.Color]::FromArgb(255, 246, 242, 227)
$RING    = [Drawing.Color]::FromArgb(255, 139, 124, 255)
$SPARKLE = [Drawing.Color]::FromArgb(255, 169, 155, 255)
$TILT    = -18.0

# The ring is a flat band: outer ellipse minus inner ellipse, rotated. Drawing it
# twice - once behind the planet, once clipped to the lower half - puts the front
# of the ring in front of the disc.
function Ring-Band([int]$n, [bool]$lowerHalfOnly) {
    $rx = $n * 0.355; $ry = $n * 0.112; $th = $n * 0.062
    $cx = $n / 2.0; $cy = $n / 2.0

    $mask = New-Object Drawing.Bitmap $n, $n
    $mg = [Drawing.Graphics]::FromImage($mask)
    $mg.SmoothingMode = 'AntiAlias'
    $mg.Clear([Drawing.Color]::Transparent)
    $br = New-Object Drawing.SolidBrush $RING
    $mg.FillEllipse($br, [float]($cx - $rx), [float]($cy - $ry), [float](2 * $rx), [float](2 * $ry))
    $mg.CompositingMode = 'SourceCopy'
    $clear = New-Object Drawing.SolidBrush ([Drawing.Color]::Transparent)
    $mg.FillEllipse($clear, [float]($cx - $rx + $th), [float]($cy - $ry + $th), [float](2 * ($rx - $th)), [float](2 * ($ry - $th)))
    $mg.Dispose()

    if ($lowerHalfOnly) {
        $cut = New-Object Drawing.Bitmap $n, $n
        $cg = [Drawing.Graphics]::FromImage($cut)
        $cg.DrawImage($mask, 0, 0)
        $cg.CompositingMode = 'SourceCopy'
        $clearRect = New-Object Drawing.SolidBrush ([Drawing.Color]::Transparent)
        $cg.FillRectangle($clearRect, 0, 0, $n, [int]($cy - $ry * 0.15))
        $cg.Dispose()
        $mask.Dispose()
        $mask = $cut
    }

    $rotated = New-Object Drawing.Bitmap $n, $n
    $rg = [Drawing.Graphics]::FromImage($rotated)
    $rg.InterpolationMode = 'HighQualityBicubic'
    $rg.TranslateTransform([float]$cx, [float]$cy)
    $rg.RotateTransform([float]$TILT)
    $rg.TranslateTransform([float](-$cx), [float](-$cy))
    $rg.DrawImage($mask, 0, 0)
    $rg.Dispose()
    $mask.Dispose()
    return $rotated
}

function Draw-Mark([int]$n, [bool]$tile) {
    $bmp = New-Object Drawing.Bitmap $n, $n
    $g = [Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'AntiAlias'
    $g.PixelOffsetMode = 'HighQuality'
    $g.Clear([Drawing.Color]::Transparent)

    if ($tile) {
        $inset = [Math]::Round($n * 0.03)
        $r = [Math]::Round($n * 0.215)
        $w = $n - 2 * $inset - 1
        $path = New-Object Drawing.Drawing2D.GraphicsPath
        $path.AddArc($inset, $inset, 2 * $r, 2 * $r, 180, 90)
        $path.AddArc($inset + $w - 2 * $r, $inset, 2 * $r, 2 * $r, 270, 90)
        $path.AddArc($inset + $w - 2 * $r, $inset + $w - 2 * $r, 2 * $r, 2 * $r, 0, 90)
        $path.AddArc($inset, $inset + $w - 2 * $r, 2 * $r, 2 * $r, 90, 90)
        $path.CloseFigure()
        $g.FillPath((New-Object Drawing.SolidBrush $TILE), $path)
    }

    $back = Ring-Band $n $false
    $g.DrawImage($back, 0, 0)
    $back.Dispose()

    $cx = $n / 2.0; $pr = $n * 0.232
    $g.FillEllipse((New-Object Drawing.SolidBrush $PLANET),
        [float]($cx - $pr), [float]($cx - $pr), [float](2 * $pr), [float](2 * $pr))

    $front = Ring-Band $n $true
    $g.DrawImage($front, 0, 0)
    $front.Dispose()

    # Sparkle, upper right.
    $sx = $n * 0.785; $sy = $n * 0.235; $sr = $n * 0.066; $sw = $sr * 0.28
    $pts = New-Object 'Drawing.PointF[]' 8
    $pts[0] = New-Object Drawing.PointF ([float]$sx), ([float]($sy - $sr))
    $pts[1] = New-Object Drawing.PointF ([float]($sx + $sw)), ([float]($sy - $sw))
    $pts[2] = New-Object Drawing.PointF ([float]($sx + $sr)), ([float]$sy)
    $pts[3] = New-Object Drawing.PointF ([float]($sx + $sw)), ([float]($sy + $sw))
    $pts[4] = New-Object Drawing.PointF ([float]$sx), ([float]($sy + $sr))
    $pts[5] = New-Object Drawing.PointF ([float]($sx - $sw)), ([float]($sy + $sw))
    $pts[6] = New-Object Drawing.PointF ([float]($sx - $sr)), ([float]$sy)
    $pts[7] = New-Object Drawing.PointF ([float]($sx - $sw)), ([float]($sy - $sw))
    $g.FillPolygon((New-Object Drawing.SolidBrush $SPARKLE), $pts)

    $g.Dispose()
    return $bmp
}

# A chunkier drawing for the 16-24 px frames: thicker ring, no sparkle.
function Draw-Mark-Small([int]$n) {
    $bmp = New-Object Drawing.Bitmap $n, $n
    $g = [Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'AntiAlias'
    $g.Clear([Drawing.Color]::Transparent)
    $inset = [Math]::Round($n * 0.015)
    $g.FillRectangle((New-Object Drawing.SolidBrush $TILE), $inset, $inset, $n - 2 * $inset, $n - 2 * $inset)
    $cx = $n / 2.0
    $rx = $n * 0.40; $ry = $n * 0.135; $th = [Math]::Max(1.5, $n * 0.085)
    $rot = [float]$TILT
    $ringPen = New-Object Drawing.Pen $RING, ([float]$th)
    $state = $g.Save()
    $g.TranslateTransform([float]$cx, [float]$cx)
    $g.RotateTransform($rot)
    $g.TranslateTransform([float](-$cx), [float](-$cx))
    $g.DrawEllipse($ringPen, [float]($cx - $rx), [float]($cx - $ry), [float](2 * $rx), [float](2 * $ry))
    $g.Restore($state)
    $pr = $n * 0.255
    $g.FillEllipse((New-Object Drawing.SolidBrush $PLANET), [float]($cx - $pr), [float]($cx - $pr), [float](2 * $pr), [float](2 * $pr))
    # Front half again.
    $state = $g.Save()
    $g.TranslateTransform([float]$cx, [float]$cx)
    $g.RotateTransform($rot)
    $g.TranslateTransform([float](-$cx), [float](-$cx))
    $clipRect = New-Object Drawing.RectangleF ([float]0), ([float]($cx - $ry * 0.15)), ([float]$n), ([float]$n)
    $g.SetClip($clipRect)
    $g.DrawEllipse($ringPen, [float]($cx - $rx), [float]($cx - $ry), [float](2 * $rx), [float](2 * $ry))
    $g.Restore($state)
    $ringPen.Dispose()
    $g.Dispose()
    return $bmp
}

function Png-Bytes($bmp) {
    $ms = New-Object IO.MemoryStream
    $bmp.Save($ms, [Drawing.Imaging.ImageFormat]::Png)
    return ,$ms.ToArray()
}

$master = Draw-Mark 1024 $true
$mark = Draw-Mark 1024 $false

$png = New-Object Drawing.Bitmap $master, 512, 512
$png.Save((Join-Path $out 'astrohybrid.png'), [Drawing.Imaging.ImageFormat]::Png)
$pngMark = New-Object Drawing.Bitmap $mark, 512, 512
$pngMark.Save((Join-Path $out 'astrohybrid-mark.png'), [Drawing.Imaging.ImageFormat]::Png)

# ICO with PNG-compressed frames, built by hand so Windows 10/11 picks the
# right size instead of rescaling one bitmap.
$sizes = @(16, 24, 32, 48, 64, 128, 256)
$frames = @()
foreach ($s in $sizes) {
    if ($s -le 24) { $b = Draw-Mark-Small $s } else { $b = New-Object Drawing.Bitmap $master, $s, $s }
    $frames += ,(Png-Bytes $b)
    $b.Dispose()
}

$ico = New-Object IO.MemoryStream
$bw = New-Object IO.BinaryWriter $ico
$bw.Write([UInt16]0)
$bw.Write([UInt16]1)
$bw.Write([UInt16]$sizes.Count)
$offset = 6 + 16 * $sizes.Count
for ($i = 0; $i -lt $sizes.Count; $i++) {
    $dim = if ($sizes[$i] -ge 256) { 0 } else { $sizes[$i] }
    $bw.Write([Byte]$dim)
    $bw.Write([Byte]$dim)
    $bw.Write([Byte]0)
    $bw.Write([Byte]0)
    $bw.Write([UInt16]1)
    $bw.Write([UInt16]32)
    $bw.Write([UInt32]$frames[$i].Length)
    $bw.Write([UInt32]$offset)
    $offset += $frames[$i].Length
}
foreach ($f in $frames) { $bw.Write($f) }
[IO.File]::WriteAllBytes((Join-Path $out 'astrohybrid.ico'), $ico.ToArray())
$bw.Dispose()

$master.Dispose(); $mark.Dispose(); $png.Dispose(); $pngMark.Dispose()
Write-Host "Wrote astrohybrid.png, astrohybrid-mark.png and astrohybrid.ico to $out"
