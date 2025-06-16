import json
import os
from django.conf import settings
from .models import SurveyResult
def get_recommended_supplements(survey_result):
    supplements = []
    added_names = set()  # 중복 방지를 위한 집합

    def add_supplement(name, reason, benefits):
        if name not in added_names:
            supplements.append({
                'name': name,
                'reason': reason,
                'benefits': benefits
            })
            added_names.add(name)

    answers = survey_result.answers

    # 비타민 D 추천
    if answers.get('indoor_daytime') == '예':
        add_supplement(
            name='비타민 D',
            reason='실내 생활이 많고 햇빛 노출이 부족합니다.',
            benefits='면역력 강화와 뼈 건강에 도움을 줍니다.'
        )
    # 오메가-3 추천
    if answers.get('sitting_work') == '예' and answers.get('exercise_frequency') in ['전혀 안함', '1-2회']:
        add_supplement(
            name='오메가-3',
            reason='장시간 앉아서 일하고 운동이 부족합니다.',
            benefits='심장 건강과 염증 감소에 도움을 줍니다.'
        )

    # 비타민 C 추천 (흡연자)
    if answers.get('smoking') == '예':
        add_supplement(
            name='비타민 C',
            reason='흡연으로 인한 산화 스트레스와 비타민 C 소모가 큽니다.',
            benefits='항산화 작용 및 면역력 강화에 도움을 줍니다.'
        )
    if answers.get('drinking') == '예':
        add_supplement('비타민 B1', '음주로 인해 비타민 B1이 소모됩니다.', '간 기능 보호와 에너지 대사에 필요합니다.')
        add_supplement('비타민 B6', '음주로 인해 비타민 B6가 소모됩니다.', '신경계 기능 유지와 피로 회복에 도움을 줍니다.')
        add_supplement('비타민 B12', '음주로 인해 비타민 B12가 소모됩니다.', '신경 보호 및 혈액 생성에 필요합니다.')

    # 4. 수면 문제
    if answers.get('sleep_well') == '아니오' or (answers.get('still_tired') == '예' and float(answers.get('sleep_hours', 0)) >= 7):
        add_supplement('마그네슘', '수면의 질이 낮거나 피로가 지속됩니다.', '신경 안정과 숙면에 도움을 줍니다.')

    # 5. 물 섭취 부족 (기준은 1일 1.5~2L 미만으로 임의 설정 가능)
    if float(answers.get('water_intake', 0)) < 7:
        add_supplement('칼륨', '수분 섭취가 적어 전해질 균형이 우려됩니다.', '체내 수분 및 전해질 균형 유지에 도움을 줍니다.')
        add_supplement('마그네슘', '수분 섭취가 적어 장 기능과 근육 건강에 부담이 됩니다.', '신경과 근육 기능을 조절하고 변비를 예방합니다.')

    # 6. 건강상태 나쁨
    if answers.get('health_status') in ['나쁨', '매우 나쁨']:
        add_supplement('아연', '전반적인 건강 상태가 좋지 않습니다.', '면역 기능과 세포 재생에 도움을 줍니다.')
        add_supplement('셀레늄', '전반적인 건강 상태가 좋지 않습니다.', '항산화 작용과 갑상선 기능 유지에 도움을 줍니다.')
        add_supplement('종합비타민', '전반적인 영양이 부족할 수 있습니다.', '기초 영양을 폭넓게 보충합니다.')

    # 7. 면역력 향상 목적
    if '면역' in answers.get('health_concerns', ''):
        add_supplement('아연', '면역력 향상을 원하십니다.', '면역세포 형성과 기능에 필수적입니다.')
        add_supplement('비타민 C', '면역력 향상을 원하십니다.', '면역 활성과 감염 방어에 기여합니다.')
        add_supplement('비타민 D', '면역력 향상을 원하십니다.', '면역세포 조절과 염증 반응 억제에 도움을 줍니다.')

    # 8. 피로
    if answers.get('fatigue') == '예' or answers.get('still_tired') == '예':
        add_supplement('비타민 B', '피로를 자주 느끼고 회복이 어렵습니다.', '에너지 생성과 신경계 안정에 도움을 줍니다.')
        add_supplement('마그네슘', '피로 회복이 더디고 수면의 질이 낮을 수 있습니다.', '근육 이완과 신경 안정에 기여합니다.')
    

    return supplements


def get_required_nutrients(user):
    """
    사용자에게 필요한 영양소 목록을 받아,
    JSON 파일에서 각 영양소의 권장 섭취량을 찾아 매핑하여 반환합니다.
    """
    # 1. nutrient_standard.json 파일의 전체 경로를 설정합니다.
    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'json', 'Mypage', 'nutrient_standards.json')
    
    all_standards = {}
    try:
        # 2. JSON 파일을 읽어 모든 영양소의 기준 정보를 불러옵니다.
        #    'utf-8' 인코딩은 한글 깨짐을 방지합니다.
        with open(file_path, 'r', encoding='utf-8') as f:
            all_standards = json.load(f)
    except FileNotFoundError:
        print(f"오류: {file_path} 에서 파일을 찾을 수 없습니다.")
        return {} # 파일이 없으면 빈 딕셔너리 반환
    except json.JSONDecodeError:
        print(f"오류: {file_path} 파일이 올바른 JSON 형식이 아닙니다.")
        return {}
    latest_survey = SurveyResult.objects.filter(user=user).order_by('-created_at').first()
    # 3. 사용자에게 추천되는 영양소 목록을 가져옵니다.
    user_needed_nutrients = get_recommended_supplements(latest_survey)
    
    # 4. 사용자가 필요로 하는 영양소만 필터링하여 최종 딕셔너리를 생성합니다.
    required_nutrients_map = {}
    for nutrient in user_needed_nutrients:
        # JSON 데이터에 해당 영양소 정보가 있는지 확인
        if nutrient['name'] in all_standards:
            # 해당 영양소의 'recommended_amount' 값을 가져와 맵에 추가
            nutrient_info = all_standards[nutrient['name']]
            recommended_amount = nutrient_info.get('recommended_amount')
            
            if recommended_amount is not None:
                required_nutrients_map[nutrient['name']] = recommended_amount
        else:
            print(f"경고: '{nutrient['name']}'에 대한 기준 정보를 찾을 수 없습니다.")

    # 최종적으로 매핑된 딕셔너리 반환
    # 예: {'비타민C': 100, '마그네슘': 350, '아연': 8}
    return required_nutrients_map

