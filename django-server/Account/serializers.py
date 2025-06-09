from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password # 비밀번호 해싱을 위해
from datetime import date
from django.contrib.auth.password_validation import validate_password
User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    birth_date = serializers.DateField(
        input_formats=['%Y-%m-%d', '%Y%m%d']
    )
    # 새로 추가될 필드: 성별을 나타내는 숫자 ID
    gender_id = serializers.IntegerField(
        help_text="성별을 나타내는 숫자 (1,3: 남성, 2,4: 여성)",
        min_value=1,
        max_value=4 # 1,2,3,4만 유효하게 받으려면 max_value를 4로 제한
    )

    class Meta:
        model = User
        fields = ('name', 'email', 'password', 'birth_date', 'gender_id') # gender_id 포함
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        gender_id = data.get('gender_id') # gender_id 값 가져오기

        # 1. 이메일 중복 확인
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "이미 등록된 이메일 주소입니다."})
        
        # 2. 비밀번호 길이 확인 (DRF 기본 PasswordValidator도 사용되지만, 클라이언트 단에서 간단한 검사)
        if len(password) < 8:
            raise serializers.ValidationError({"password": "비밀번호는 최소 8자 이상이어야 합니다."})
        
        # 3. 생년월일 형식 확인 (DateField가 기본적으로 처리)
        # 4. 성별 ID에 따른 gender 값 설정
        gender = None
        if gender_id in [1, 3]:
            gender = 'male'
        elif gender_id in [2, 4]:
            gender = 'female'
        else:
            # 이 시점에 도달할 가능성은 낮음 (min_value, max_value로 걸러짐)
            raise serializers.ValidationError({"gender_id": "성별을 나타내는 숫자는 1, 2, 3, 4 중 하나여야 합니다."})

        data['gender'] = gender # User 모델의 'gender' 필드에 할당될 값

        return data

    def create(self, validated_data):
        # gender_id는 User 모델 필드가 아니므로 제거
        gender_id = validated_data.pop('gender_id') 
        # validate 메서드에서 추가한 'gender' 필드를 사용
        gender = validated_data.pop('gender') 

        user = User.objects.create_user(
            username=validated_data['email'],
            name=validated_data['name'],
            email=validated_data['email'],
            password=validated_data['password'],
            birth_date=validated_data['birth_date'],
            gender=gender, # gender 필드 저장
            is_verified=False # 이메일 인증을 위해 기본값 False
        )
        return user
class FindEmailSerializer(serializers.Serializer):
    # 클라이언트에서 받을 필드: 이름 (name)과 생년월일 (birth_date)
    name = serializers.CharField(max_length=20, required=True)
    birth_date = serializers.DateField(required=True,input_formats=['%Y-%m-%d', '%Y%m%d']) # "YYYY-MM-DD" 형식으로 기대
    print(birth_date)
    # Serializer.validate() 메서드는 전체 데이터에 대한 유효성 검사를 수행합니다.
    def validate(self, data):
        # 이름과 생년월일로 사용자 찾기
        try:
            # name은 모델의 'name' 필드에, birth_date는 모델의 'birth_date' 필드에 매핑
            user = User.objects.get(name=data['name'], birth_date=data['birth_date'])
        except User.DoesNotExist:
            raise serializers.ValidationError("입력하신 정보와 일치하는 사용자를 찾을 수 없습니다.")
        except User.MultipleObjectsReturned:
            # 이론적으로 이름+생년월일 조합이 유니크하지 않을 경우 발생 가능
            # 이메일 찾기는 고유해야 하므로, 이 경우에도 에러 처리하거나,
            # 더 많은 정보(예: 전화번호)를 요구하여 고유성을 높여야 합니다.
            # 여기서는 간단히 "찾을 수 없음"으로 처리합니다.
            raise serializers.ValidationError("입력하신 정보와 일치하는 사용자가 너무 많습니다. 추가 정보를 입력해주세요.")
        
        # is_verified 필드를 확인하여 이메일 인증이 완료된 사용자만 찾도록 합니다.
        if not user.is_verified:
            raise serializers.ValidationError("해당 계정은 이메일 인증이 완료되지 않았습니다.")

        data['user'] = user # 찾은 유저 객체를 data에 추가하여 뷰에서 사용
        return data
    
class PasswordResetRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=20, required=True)
    email = serializers.EmailField(required=True)
    birth_date = serializers.DateField(
        required=True,
        input_formats=['%Y-%m-%d', '%Y%m%d']
    )

    def validate(self, data):
        name = data.get('name')
        email = data.get('email')
        birth_date = data.get('birth_date')

        try:
            user = User.objects.get(name=name, email=email, birth_date=birth_date)
        except User.DoesNotExist:
            raise serializers.ValidationError("입력하신 정보와 일치하는 사용자를 찾을 수 없습니다.")

        
        if not user.is_verified:
            raise serializers.ValidationError("해당 계정은 이메일 인증이 완료되지 않았습니다.")

        data['user'] = user
        return data
class SetNewPasswordWithTokenSerializer(serializers.Serializer):
    uidb64 = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(min_length=8, write_only=True, required=True)
    confirm_new_password = serializers.CharField(min_length=8, write_only=True, required=True)

    def validate(self, data):
        from django.utils.http import urlsafe_base64_decode
        from django.contrib.auth.tokens import default_token_generator
        from django.core.exceptions import ValidationError

        uidb64 = data.get('uidb64')
        token = data.get('token')
        new_password = data.get('new_password')
        confirm_new_password = data.get('confirm_new_password')
        # 비밀번호 일치 검사
        if new_password != confirm_new_password:
            raise serializers.ValidationError({"confirm_new_password": "새 비밀번호와 확인 비밀번호가 일치하지 않습니다."})

        # 비밀번호 유효성 검사 (Django 기본 검사기 사용)
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": e.messages})

        # UID 디코딩 및 사용자 찾기
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is None:
            raise serializers.ValidationError({"detail": "유효하지 않은 재설정 링크입니다."})
        
        # 토큰 유효성 검사
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({"detail": "재설정 링크가 만료되었거나 유효하지 않습니다."})

        data['user'] = user # 유효한 사용자 객체 추가
        return data