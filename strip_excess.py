import json
from pathlib import Path

supplier_url = "https://gsmcheap.com/"

def strip_excess(input_file, output_file):
    with open(input_file, 'r',encoding="utf-8") as f:
        data = json.load(f)

    stripped_data = []
    for service in data.get('services', []):
        stripped_data.append({
            'title': service.get('title'),
            'delivery_time': service.get('delivery_time'),
            'price': service.get('price'),
            
            
        })
    data_file = {
        'supplier': data.get('supplier'),
        'services_type': data.get('services_type'),
        'supplier_url': supplier_url,
        'services': stripped_data
    }

    with open(output_file, 'w', encoding="utf-8") as f:
        json.dump(data_file, f, indent=4)

if __name__ == "__main__":
    input_file = Path('services.json')
    output_file = Path('gsm_tech_africa_rental.json')
    strip_excess(input_file, output_file)