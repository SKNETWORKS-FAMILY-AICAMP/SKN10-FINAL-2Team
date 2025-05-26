import pandas as pd

# CSV 파일 읽기
df = pd.read_csv('data/crawling data.csv')

# 컬럼 정보 출력
print("\n컬럼 목록:")
print(df.columns.tolist())

# 데이터 타입 정보 출력
print("\n데이터 타입:")
print(df.dtypes)

# 처음 5개 행 출력
print("\n처음 5개 행:")
print(df.head()) 