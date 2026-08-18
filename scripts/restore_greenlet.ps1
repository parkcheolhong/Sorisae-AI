$ErrorActionPreference='Stop'
Set-Location 'C:\Users\WORK\source\repos\parkcheolhong\codeAI'
$py='.\.venv\Scripts\python.exe'
& $py -m pip install greenlet==3.5.5
& $py -m pip check
& $py -c "import greenlet, sqlalchemy; print('greenlet', greenlet.__version__); print('sqlalchemy', sqlalchemy.__version__)"
