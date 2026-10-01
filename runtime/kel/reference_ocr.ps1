# Fixed local OCR worker. Input is selected image bytes, never a path or command.
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
    $null = [Windows.Storage.Streams.DataWriter,Windows.Storage.Streams,ContentType=WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
    $null = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
    $null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
    $null = [Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
    $asyncMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
    function Await-Result($operation, [Type]$type) {
        $task = $asyncMethod.MakeGenericMethod($type).Invoke($null, @($operation))
        if (-not $task.Wait(15000)) { throw 'OCR timed out.' }
        return $task.Result
    }
    $inputText = [Console]::In.ReadToEnd()
    if ($inputText.Length -gt 7000000) { throw 'Input too large.' }
    $payload = $inputText | ConvertFrom-Json
    $bytes = [Convert]::FromBase64String($payload.content)
    if ($bytes.Length -lt 1 -or $bytes.Length -gt 5000000) { throw 'Input too large.' }
    $stream = [Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
    $writer = [Windows.Storage.Streams.DataWriter]::new($stream.GetOutputStreamAt(0))
    $writer.WriteBytes($bytes)
    $null = Await-Result $writer.StoreAsync() ([UInt32])
    $null = $writer.DetachStream(); $writer.Dispose()
    $stream.Seek(0)
    $decoder = Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($null -eq $engine) { throw 'No local OCR language is installed.' }
    if ($decoder.PixelWidth -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension -or
        $decoder.PixelHeight -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension -or
        [long]$decoder.PixelWidth * [long]$decoder.PixelHeight -gt 20000000) { throw 'Image dimensions too large.' }
    $bitmap = Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $converted = [Windows.Graphics.Imaging.SoftwareBitmap]::Convert($bitmap, [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8, [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied)
    $recognized = Await-Result ($engine.RecognizeAsync($converted)) ([Windows.Media.Ocr.OcrResult])
    $text = ($recognized.Lines | ForEach-Object Text) -join "`n"
    if ([string]::IsNullOrWhiteSpace($text) -or $text.Length -gt 30000) { throw 'No bounded readable text was found.' }
    $answer = @{text=$text; language=$engine.RecognizerLanguage.LanguageTag; pages=1; extraction='windows-ocr'}
    $converted.Dispose(); $bitmap.Dispose(); $stream.Dispose()
    [Console]::Out.Write(($answer | ConvertTo-Json -Compress))
} catch {
    [Console]::Out.Write('{"error":"Kel could not read this image with local OCR. Choose a clearer image or add its text."}')
    exit 1
}
