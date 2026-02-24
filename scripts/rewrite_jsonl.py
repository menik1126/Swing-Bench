import json

def add_model_name(input_file, output_file, model_name="Qwen2-5"):
    with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
        for line in infile:
            data = json.loads(line)
            data["model_name_or_path"] = model_name
            json.dump(data, outfile, ensure_ascii=False)
            outfile.write("\n")

if __name__ == "__main__":
    input_path = "../outputs/predictions.jsonl"    
    output_path = "../outputs/output.jsonl" 
    
    add_model_name(input_path, output_path)
    print(f"Updated JSONL file saved as {output_path}")