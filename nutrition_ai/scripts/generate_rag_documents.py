import os
import json
import pandas as pd
from ast import literal_eval
from tqdm import tqdm

# 안전하게 eval 처리
def safe_parse(val, default=[]):
    try:
        return literal_eval(val)
    except Exception:
        return default

def generate_rag_documents(df, output_path):
    rag_documents = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="📄 Generating RAG documents"):
        url = row.get("url", "")
        title = row.get("title", "")

        # Features
        features = safe_parse(row.get("features", "[]"))
        if features:
            rag_documents.append({
                "text": f"{title}\n\n" + "\n".join(features),
                "metadata": {"type": "features", "source": url}
            })

        # Important Info
        important_info = row.get("important_info", "")
        if isinstance(important_info, str) and len(important_info) > 20:
            rag_documents.append({
                "text": important_info,
                "metadata": {"type": "important_info", "source": url}
            })

        # Table Info
        table_info = safe_parse(row.get("table_info", "[]"))
        if table_info:
            rag_documents.append({
                "text": "\n".join(table_info),
                "metadata": {"type": "table_info", "source": url}
            })

        # Detail Dict
        try:
            detail = literal_eval(row.get("detail_dict", "{}"))
            if isinstance(detail, dict):
                detail_text = "\n".join([f"{k}: {v}" for k, v in detail.items()])
                rag_documents.append({
                    "text": detail_text,
                    "metadata": {"type": "detail_dict", "source": url}
                })
        except Exception as e:
            print(f"⚠️ detail_dict 파싱 오류: {e}")
            continue

    # 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for doc in rag_documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"✅ 총 {len(rag_documents)}개의 문서가 생성되어 저장됨 → {output_path}")
    return output_path

if __name__ == "__main__":
    # 실행 위치 관계없이 동작하도록 절대경로 사용
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(base_dir, "../data/crawling data.csv")
    output_jsonl = os.path.join(base_dir, "../data/rag_documents.jsonl")

    df = pd.read_csv(input_csv)
    generate_rag_documents(df, output_jsonl)

