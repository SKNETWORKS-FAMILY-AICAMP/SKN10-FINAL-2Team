from openai import OpenAI
from app.config import get_settings
from sqlalchemy.orm import Session
from app.models.chat import LLMRequest
from app.models.supplement import Supplement, Ingredient
from typing import List, Dict

settings = get_settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class LLMService:
    def __init__(self, db: Session):
        self.db = db

    def get_supplement_recommendation(self, user_info: Dict) -> List[Dict]:
        # 사용자 정보를 기반으로 프롬프트 생성
        prompt = self._create_recommendation_prompt(user_info)
        
        # LLM에 요청
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a nutrition expert AI assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 응답 저장
        llm_request = LLMRequest(
            user_id=user_info.get("user_id"),
            input_prompt=prompt,
            llm_response=response.choices[0].message.content,
            model="gpt-4",
            status="completed"
        )
        self.db.add(llm_request)
        self.db.commit()
        
        return self._parse_recommendation_response(response.choices[0].message.content)

    def _create_recommendation_prompt(self, user_info: Dict) -> str:
        return f"""
        Based on the following user information, recommend appropriate supplements:
        
        Age: {user_info.get('age')}
        Gender: {user_info.get('gender')}
        Health Conditions: {user_info.get('health_conditions')}
        Allergies: {user_info.get('allergies')}
        
        Please provide recommendations in the following format:
        1. Supplement name
        2. Reason for recommendation
        3. Potential benefits
        4. Precautions
        """

    def _parse_recommendation_response(self, response: str) -> List[Dict]:
        # LLM 응답을 파싱하여 구조화된 데이터로 변환
        recommendations = []
        # 여기에 파싱 로직 구현
        return recommendations

    def check_interactions(self, supplement_ids: List[int]) -> List[Dict]:
        # 영양제 간 상호작용 확인
        supplements = self.db.query(Supplement).filter(
            Supplement.id.in_(supplement_ids)
        ).all()
        
        interactions = []
        for supplement in supplements:
            for ingredient in supplement.ingredients:
                # 성분 간 상호작용 확인 로직
                pass
        
        return interactions 