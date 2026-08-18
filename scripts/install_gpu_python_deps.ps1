$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'
$py = '.\.venv\Scripts\python.exe'

& $py -m pip install --no-cache-dir auto-gptq==0.7.1 autoawq==0.2.9 xformers==0.0.35 bitsandbytes==0.50.1
if ($LASTEXITCODE -ne 0) {
  throw "GPU dependency install failed with exit code $LASTEXITCODE"
}

& $py -m pip show auto-gptq autoawq xformers bitsandbytes
