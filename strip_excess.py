import json
from pathlib import Path

def strip_excess(input_file, output_file):
    with open(input_file, 'r',encoding="utf-8") as f:
        data = json.load(f)

    stripped_data = []
    for service in data.get('services', []):
        stripped_data.append({
            'title': service.get('title'),
            'delivery_time': service.get('delivery_time'),
            'price': service.get('price'),
            'currency': service.get('currency')
        })
    data_file = {
        'supplier': data.get('supplier'),
        'services_type': data.get('service_type'),
        'services': stripped_data
    }

    with open(output_file, 'w', encoding="utf-8") as f:
        json.dump(data_file, f, indent=4)

if __name__ == "__main__":
    input_file = Path('services.json')
    output_file = Path('gsm_cheap_remote.json')
    strip_excess(input_file, output_file)