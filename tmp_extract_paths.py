import urllib.request, json
d = json.loads(urllib.request.urlopen('http://127.0.0.1:8000/openapi.json').read())
for p in sorted(d['paths'].keys()):
    if 'marketplace' in p:
        print(p)
