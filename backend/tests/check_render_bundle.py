import urllib.request
import re

req = urllib.request.Request('https://sistema-dni-plantillas-1.onrender.com', headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
    print('HTML length:', len(html))
    js_files = re.findall(r'/assets/[a-zA-Z0-9_\-]+\.js', html)
    print('JS files in HTML:', js_files)
    if js_files:
        js_url = 'https://sistema-dni-plantillas-1.onrender.com' + js_files[0]
        js_content = urllib.request.urlopen(js_url, timeout=10).read().decode('utf-8')
        print('Has sistema-dni-plantillas:', 'sistema-dni-plantillas' in js_content)
        print('Has 127.0.0.1:', '127.0.0.1' in js_content)
        print('Has onrender.com:', 'onrender.com' in js_content)
except Exception as e:
    print('Error:', e)
