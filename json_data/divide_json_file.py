import json

def divide_json(input_file, output_file_prefix):
    # Load the original JSON data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Determine the size of each part (divide into 4)
    total_items = len(data)
    chunk_size = total_items // 4

    # Split the data into 4 parts
    parts = [data[i:i + chunk_size] for i in range(0, total_items, chunk_size)]

    # Handle the last chunk (if there are leftover items)
    if len(parts) > 4:
        parts[3].extend(parts.pop())

    # Write each part to a new JSON file
    for i, part in enumerate(parts):
        output_file = f"{output_file_prefix}_part{i+1}.json"
        with open(output_file, 'w') as f:
            json.dump(part, f, indent=4)

    print("JSON file has been divided into 4 parts successfully!")

# Example usage
divide_json('data_updated.json', 'data_update_splited')