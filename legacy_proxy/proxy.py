from flask import Flask, request, Response, render_template, redirect, url_for
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus, unquote_plus
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Global tracker for context
CURRENT_URL = "https://www.google.com"

# Use a session to persist cookies
SESSION = requests.Session()
# Mimic a real browser heavily to avoid detection
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
})

@app.route('/')
def home():
    return render_template('index.html')

def fetch_and_render(url):
    global CURRENT_URL
    
    # Basic URL Cleanup
    if not url.startswith('http'):
        url = 'https://' + url
    
    try:
        logging.info(f"Fetching: {url}")
        
        # Determine method
        if request.method == 'POST':
            # Send form data if POST
            # Allow redirects=False to capture 302s manually
            resp = SESSION.post(url, data=request.form, files=request.files, allow_redirects=False)
        else:
            # Send query params if present, but exclude 'url' passed to proxy
            params = {k: v for k, v in request.args.items() if k != 'url'}
            resp = SESSION.get(url, params=params, timeout=10, allow_redirects=False)
        
        # Handle Redirects Manually
        if resp.is_redirect:
            location = resp.headers.get('Location')
            if location:
                new_dest = urljoin(url, location)
                logging.info(f"Redirecting to: {new_dest}")
                # Redirect the USER'S browser to the proxy with the new URL
                return redirect(url_for('proxy', url=new_dest))
        
        # Update Context on successful fetch (non-redirect, or final)
        CURRENT_URL = resp.url

    except Exception as e:
        return f"Error fetching {url}: {str(e)}", 500

    # Pass headers
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'content-security-policy']
    headers = [(name, value) for (name, value) in resp.headers.items() 
               if name.lower() not in excluded_headers]

    content_type = resp.headers.get('Content-Type', '').lower()

    if 'text/html' in content_type:
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Rewrite common attributes
        tags_attributes = {
            'a': 'href',
            'link': 'href',
            'script': 'src',
            'img': 'src',
            'iframe': 'src',
            'form': 'action',
            'source': 'src',
            'video': 'src',
            'audio': 'src',
            'object': 'data',
            'embed': 'src'
        }

        for tag_name, attr in tags_attributes.items():
            for tag in soup.find_all(tag_name):
                if tag.has_attr(attr):
                    original = tag[attr]
                    # Skip internal links, javascript calls, data URIs
                    if not original or original.startswith('data:') or original.startswith('#') or original.startswith('javascript:'):
                        continue
                        
                    # Resolve relative to absolute
                    absolute_url = urljoin(resp.url, original)
                    
                    # Rewrite to point to proxy
                    new_val = f"/proxy?url={quote_plus(absolute_url)}"
                    tag[attr] = new_val
        
        # Rewrite Meta Refresh
        for meta in soup.find_all('meta', attrs={'http-equiv': lambda x: x and x.lower() == 'refresh'}):
            if meta.has_attr('content'):
                content = meta['content']
                parts = content.split('url=', 1)
                if len(parts) > 1:
                    delay = parts[0]
                    target_url = parts[1].strip("'\" ")
                    absolute_target = urljoin(resp.url, target_url)
                    new_val = f"{delay}url=/proxy?url={quote_plus(absolute_target)}"
                    meta['content'] = new_val

        return Response(str(soup), resp.status_code, headers)

    # For everything else (images, css, js)
    return Response(resp.content, resp.status_code, headers)

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    url = request.args.get('url')
    if not url:
        # If no URL provided, try to stay on current context or show error, 
        # but DO NOT go back to index.html
        if CURRENT_URL:
             return fetch_and_render(CURRENT_URL)
        return "Error: No URL provided and no history available.", 400
    return fetch_and_render(url)

@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    global CURRENT_URL
    # We are here because a relative path was requested (e.g. /search?q=foo)
    # We reconstruct the full intended URL using the last known CURRENT_URL
    # request.full_path includes the query string e.g., "/search?q=hello"
    
    # If path matches a known route like proxy, skip (Flask handles it, but just in case)
    if path == 'proxy':
        return proxy()
        
    target_url = urljoin(CURRENT_URL, request.full_path)
    logging.info(f"Catch-all caught '{path}'. Proxying to: {target_url}")
    return fetch_and_render(target_url)

if __name__ == '__main__':
    # Run on default port 5000
    app.run(host='0.0.0.0', port=5000)
