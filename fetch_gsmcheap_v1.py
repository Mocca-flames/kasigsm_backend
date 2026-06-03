import requests
import re
import json

url = "https://gsmcheap.com/remote/service"
headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-ZA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/147.0.0.0 Safari/537.36"
}

r = requests.get(url, headers=headers)

if r.status_code == 200:
    # Find the services variable in the HTML
    # Look for patterns like: var services = [...];
    pattern = r'var\s+services\s*=\s*(\[.*?\]);'
    match = re.search(pattern, r.text, re.DOTALL)
    
    if match:
        services_json_str = match.group(1)
        services_data = json.loads(services_json_str)
        
        
        # Save as JSON file
        with open("service.json", "w", encoding="utf-8") as f:
            json.dump(services_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully saved {len(services_data)} services to services.json")
    else:
        print("Could not find 'var services' in the page")
        # Debug: save HTML to see what's there
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print("Saved HTML to debug.html for inspection")