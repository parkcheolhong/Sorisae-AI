$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'
$py = '.\.venv\Scripts\python.exe'

& $py -m pip uninstall -y greenlet
& $py -m pip install --no-cache-dir greenlet==3.0.3
& $py -m pip check
& $py -c "import greenlet, sqlalchemy; print('greenlet', greenlet.__version__); print('sqlalchemy', sqlalchemy.__version__)"
