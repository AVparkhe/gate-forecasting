import urllib.request
import json

req = urllib.request.Request('http://localhost:8000/api/learning/cross-validation')
try:
    response = urllib.request.urlopen(req)
    print(response.read().decode('utf-8')[:500])
except Exception as e:
    print(e)
