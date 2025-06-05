from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password # 비밀번호 해싱을 위해
from datetime import date
User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True) # 비밀번호는 응답에 포함되지 않도록

    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'birth_date'] # 필요에 따라 gender도 추가
        # read_only_fields = ['username'] # 만약 username이 필수가 아니라면
    
    def create(self, validated_data):
        # 비밀번호를 해싱하여 저장
        validated_data['password'] = make_password(validated_data['password'])
        
        # username이 필수가 아니라면, email을 username으로 사용하는 로직을 추가할 수 있습니다.
        if 'name' in validated_data and not validated_data.get('username'):
            validated_data['username'] = validated_data['name']
            
        user = super().create(validated_data)
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