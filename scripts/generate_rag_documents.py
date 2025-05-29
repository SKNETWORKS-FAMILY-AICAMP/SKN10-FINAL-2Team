import json
from ast import literal_eval
from tqdm import tqdm
import pandas as pd
import os

# Helper function to clean and parse fields safely
def safe_parse(val, default=[]):
    try:
        return literal_eval(val)
    except Exception:
        return default

def generate_rag_documents(df, output_path):
    # Create a list to store the jsonl-style documents
    rag_documents = []

    # Iterate over each row and generate documents
    for _, row in tqdm(df.iterrows(), total=len(df), desc="📄 Generating RAG documents"):
        url = row["url"]
        title = row["title"]

        # Features section
        features = safe_parse(row["features"])
        if features:
            rag_documents.append({
                "text": f"{title}\n\n" + "\n".join(features),
                "metadata": {"type": "features", "source": url}
            })

        # Important info section
        if isinstance(row["important_info"], str) and len(row["important_info"]) > 20:
            rag_documents.append({
                "text": row["important_info"],
                "metadata": {"type": "important_info", "source": url}
            })

        # Table info section
        table_info = safe_parse(row["table_info"])
        if table_info:
            rag_documents.append({
                "text": "\n".join(table_info),
                "metadata": {"type": "table_info", "source": url}
            })

        # Detail dict section
        try:
            detail = literal_eval(row["detail_dict"])
            detail_text = "\n".join([f"{k}: {v}" for k, v in detail.items()])
            rag_documents.append({
                "text": detail_text,
                "metadata": {"type": "detail_dict", "source": url}
            })
        except Exception:
            continue

    # Save as jsonl file
    with open(output_path, "w", encoding="utf-8") as f:
        for doc in rag_documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    return output_path

if __name__ == "__main__":
    # Get the absolute path to the data directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(current_dir), "data")
    
    # Input and output file paths
    input_csv = os.path.join(data_dir, "crawling data.csv")
    output_path = os.path.join(data_dir, "rag_documents.jsonl")
    
    # Read CSV file
    df = pd.read_csv(input_csv)
    
    # Generate RAG documents
    generate_rag_documents(df, output_path)
    print(f"RAG documents have been generated and saved to: {output_path}") 