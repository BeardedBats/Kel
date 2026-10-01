# Fixed bytes-only PDF renderer/OCR. Parent supplies validated page metadata.
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$stream = $null; $writer = $null
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
    $null = [Windows.Storage.Streams.DataWriter,Windows.Storage.Streams,ContentType=WindowsRuntime]
    $null = [Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
    $null = [Windows.Data.Pdf.PdfPageRenderOptions,Windows.Data.Pdf,ContentType=WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
    $null = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
    $null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
    $null = [Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
    $asyncMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
    $actionMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
    } | Select-Object -First 1
    function Await-Result($operation, [Type]$type) {
        $task = $asyncMethod.MakeGenericMethod($type).Invoke($null, @($operation))
        if (-not $task.Wait(15000)) { throw 'PDF OCR timed out.' }
        return $task.Result
    }
    function Await-Action($operation) {
        $task = $actionMethod.Invoke($null, @($operation))
        if (-not $task.Wait(15000)) { throw 'PDF rendering timed out.' }
        $task.GetAwaiter().GetResult()
    }
    $inputText = [Console]::In.ReadToEnd()
    if ($inputText.Length -gt 7200000) { throw 'Input too large.' }
    $payload = $inputText | ConvertFrom-Json
    $bytes = [Convert]::FromBase64String($payload.content)
    if ($bytes.Length -lt 5 -or $bytes.Length -gt 5000000 -or
        [Text.Encoding]::ASCII.GetString($bytes,0,5) -ne '%PDF-') { throw 'Invalid PDF bytes.' }
    if ($payload.pages -lt 1 -or $payload.pages -gt 20 -or
        $payload.page_texts.Count -ne $payload.pages -or $payload.missing_pages.Count -lt 1) { throw 'Invalid page metadata.' }
    $parts = [Collections.Generic.List[string]]::new()
    $missing = [Collections.Generic.List[int]]::new()
    for ($index=0; $index -lt $payload.pages; $index++) {
        if ($payload.page_texts[$index] -isnot [string]) { throw 'Invalid page text.' }
        $parts.Add($payload.page_texts[$index])
        if ([string]::IsNullOrWhiteSpace($parts[$index])) { $missing.Add($index) }
    }
    if (($missing -join ',') -ne ($payload.missing_pages -join ',') -or
        ($parts -join "`n`n").Length -gt 30000) { throw 'Invalid missing pages.' }
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($null -eq $engine) { throw 'No local OCR language is installed.' }
    $stream = [Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
    $writer = [Windows.Storage.Streams.DataWriter]::new($stream.GetOutputStreamAt(0))
    $writer.WriteBytes($bytes)
    $null = Await-Result $writer.StoreAsync() ([UInt32])
    $null = $writer.DetachStream(); $writer.Dispose(); $writer = $null
    $stream.Seek(0)
    $document = Await-Result ([Windows.Data.Pdf.PdfDocument]::LoadFromStreamAsync($stream)) ([Windows.Data.Pdf.PdfDocument])
    if ($document.IsPasswordProtected -or $document.PageCount -ne $payload.pages) { throw 'PDF metadata differs.' }
    foreach ($index in $missing) {
        $page = $null; $rendered = $null; $bitmap = $null; $converted = $null
        try {
            $page = $document.GetPage([uint32]$index)
            $width = [double]$page.Size.Width; $height = [double]$page.Size.Height
            if ([double]::IsNaN($width) -or [double]::IsNaN($height) -or
                [double]::IsInfinity($width) -or [double]::IsInfinity($height) -or
                $width -le 0 -or $height -le 0) { throw 'Invalid page dimensions.' }
            $longSide = [Math]::Min(2000,[Windows.Media.Ocr.OcrEngine]::MaxImageDimension)
            $scale = $longSide / [Math]::Max($width,$height)
            $options = [Windows.Data.Pdf.PdfPageRenderOptions]::new()
            $options.DestinationWidth = [uint32][Math]::Max(1,[Math]::Floor($width*$scale))
            $options.DestinationHeight = [uint32][Math]::Max(1,[Math]::Floor($height*$scale))
            $rendered = [Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
            $null = Await-Action ($page.RenderToStreamAsync($rendered,$options))
            $rendered.Seek(0)
            $decoder = Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($rendered)) ([Windows.Graphics.Imaging.BitmapDecoder])
            if ($decoder.PixelWidth -gt $longSide -or $decoder.PixelHeight -gt $longSide -or
                [long]$decoder.PixelWidth*[long]$decoder.PixelHeight -gt 4000000) { throw 'Rendered page too large.' }
            $bitmap = Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
            $converted = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert($bitmap,[Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,[Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied)
            $recognized = Await-Result ($engine.RecognizeAsync($converted)) ([Windows.Media.Ocr.OcrResult])
            $text = ($recognized.Lines | ForEach-Object Text) -join "`n"
            if ([string]::IsNullOrWhiteSpace($text)) { throw 'No readable page text.' }
            $parts[$index] = $text
            if (($parts -join "`n`n").Length -gt 30000) { throw 'Text too large.' }
        } finally {
            foreach ($resource in @($converted,$bitmap,$rendered,$page)) {
                if ($null -ne $resource) { $resource.Dispose() }
            }
        }
    }
    $answer = @{text=($parts -join "`n`n"); language=$engine.RecognizerLanguage.LanguageTag; pages=$document.PageCount; extraction='pdf-ocr'}
    [Console]::Out.Write(($answer | ConvertTo-Json -Compress))
} catch {
    [Console]::Out.Write('{"error":"This PDF has a page without readable text from local OCR. Choose a clearer PDF or add its text."}')
    exit 1
} finally {
    if ($null -ne $writer) { $writer.Dispose() }
    if ($null -ne $stream) { $stream.Dispose() }
}
