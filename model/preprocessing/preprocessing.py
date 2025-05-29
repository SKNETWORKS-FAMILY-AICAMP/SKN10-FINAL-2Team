import os
import pandas as pd
from generate_rag_documents import generate_rag_documents

def compute_bayesian_score(avg, count, global_avg, confidence=10):
    return (count / (count + confidence)) * avg + (confidence / (count + confidence)) * global_avg

def extract_rating_summary(input_csv, output_csv):
    df = pd.read_csv(input_csv)

    # 필요한 컬럼만 추출
    df_summary = df[["title", "average_rating", "total_reviews"]].copy()

    # 평균점수로 베이지안 점수 계산
    global_avg = df_summary["average_rating"].mean()
    df_summary["bayesian_score"] = df_summary.apply(
        lambda row: compute_bayesian_score(
            row["average_rating"], row["total_reviews"], global_avg
        ), axis=1
    )

    df_summary = df_summary.sort_values(by="bayesian_score", ascending=False)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df_summary.to_csv(output_csv, index=False)
    print(f"✅ 정리된 평점 요약 CSV 저장 완료 → {output_csv}")
    return df_summary

if __name__ == "__main__":
    # 현재 스크립트의 절대 경로
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # nutrition_ai 디렉토리 경로 (model의 상위 디렉토리)
    nutrition_ai_dir = os.path.dirname(os.path.dirname(current_dir))
    # data 디렉토리 경로
    data_dir = os.path.join(nutrition_ai_dir, "data")
    
    # 평점 요약 생성
    input_csv = os.path.join(data_dir, "crawling data.csv")
    output_csv = os.path.join(data_dir, "review_summary.csv")
    extract_rating_summary(input_csv, output_csv)
    
    # RAG 문서 생성
    output_rag = os.path.join(data_dir, "rag_documents.jsonl")
    df = pd.read_csv(input_csv)
    generate_rag_documents(df, output_rag)
    print(f"✅ RAG 문서 생성 완료 → {output_rag}")
