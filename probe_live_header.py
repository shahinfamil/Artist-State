import urllib.request

url = 'http://127.0.0.1:5000/'

try:
    req = urllib.request.Request(url, method='GET')
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read(120000).decode('utf-8', errors='ignore')
        print('HTTP_STATUS', resp.status)
        print('LEN_BODY', len(body))
        print('HEADER', '<header class="site-header"' in body)
        print('TOGGLE', '<button class="mobile-menu-toggle"' in body)
        print('THREE_DOT', '<i class="ri-more-2-fill"' in body)
        print('MAIN_NAV', '<nav class="main-nav" id="main-navigation"' in body)
        print('ADMIN_LEGACY', 'class="mobile-admin-link"' in body or 'ri-shield-user-line' in body or '/admin/' in body)
except Exception as exc:
    print(type(exc).__name__, exc)
