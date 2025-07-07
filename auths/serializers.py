from .models import CommitmentForSixMonths
from utils.upload_utils import upload_file_to_digital_ocean
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
User = get_user_model()

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    # Temporary field for image upload (write-only)
    photo_tmp = serializers.ImageField(
        required=False, allow_null=True, write_only=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'username', 'email',  'role', 'address',
                  'phone_number', 'photo', 'photo_tmp',  'trial_status', 'city', 'postal_code')
        read_only_fields = ('id', 'username', 'email', 'trial_status')

    def create(self, validated_data):
        # Handle image upload if provided
        photo_tmp = validated_data.pop('photo_tmp', None)

        if photo_tmp:
            uploaded_image_url = upload_file_to_digital_ocean(photo_tmp)
            validated_data['photo'] = uploaded_image_url

        user = User.objects.create(**validated_data)
        return user

    def validate_phone_number(self, value):
        if len(value) > 15:
            raise serializers.ValidationError(
                "Stellen Sie sicher, dass dieses Feld nicht mehr als 15 Zeichen enthält."
            )
        return value


    def update(self, instance, validated_data):
        # Handle image upload if provided
        photo_tmp = validated_data.pop('photo_tmp', None)

        if photo_tmp:
            uploaded_image_url = upload_file_to_digital_ocean(photo_tmp)
            validated_data['photo'] = uploaded_image_url

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure string fields are cleaned properly
        for key in ['username', 'role', 'address', 'phone_number']:
            if isinstance(data.get(key), str):
                data[key] = data[key].strip()

        return data


class UserRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone_number',
                  'address', 'city', 'postal_code', 'confirm_password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret.pop('password', None)
        return ret

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {"error": "Passwörter stimmen nicht überein."}
            )

        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError(
                {"email": "E-Mail-Adresse ist bereits registriert."}
            )

        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError(
                {"username": "Benutzername ist bereits vergeben."}
            )

        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.is_active = True
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data['identifier']
        password = data['password']

        # Find user either by username or email
        user = None
        if '@' in identifier and '.' in identifier:
            user = User.objects.filter(email=identifier).first()
        else:
            user = User.objects.filter(username=identifier).first()

        if not user:
            raise serializers.ValidationError(
                {"identifier": "Ungültige Anmeldedaten. Bitte überprüfen Sie Ihre E-Mail-Adresse oder Ihren Benutzernamen."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"identifier": "Ihr Konto ist nicht aktiv. Bitte überprüfen Sie Ihre E-Mail-Adresse zur Verifizierung."}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {"password": "Falsches Passwort. Bitte versuchen Sie es erneut."}
            )

        return {"user": user}


class TokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()

    def to_representation(self, instance):
        return {
            'access': instance.access_token,
            'refresh': instance.refresh_token,
        }


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            return user
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Ein Benutzer mit dieser E-Mail-Adresse existiert nicht."
            )



class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                "Neues Passwort und Bestätigungspasswort stimmen nicht überein."
            )
        return data


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                "New password and confirmation password do not match.")
        return data


class CustomUserAllSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'address', 'city', 'postal_code',
                  'phone_number', 'photo', 'trial_status', 'is_active']


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'address', 'city',
                  'postal_code', 'phone_number', 'photo', 'trial_status']


class UpdateTrialStatusSerializer(serializers.Serializer):
    trial_status = serializers.BooleanField()

    def validate_trial_status(self, value):
        return value


class CommitmentForSixMonthsSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)

    class Meta:
        model = CommitmentForSixMonths
        fields = ['id', 'user','committed_once', 'commitment_status',
                  'commitment_start_date', 'commitment_end_date', 'updated_at']

    def update(self, instance, validated_data):
        """
        Override the update method to handle updating the commitment status.
        """
        # If we want to reset commitment details when status is False
        if 'commitment_status' in validated_data and validated_data['commitment_status'] is False:
            instance.reset_commitment()
        else:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
        return instance


class MyCommitmentfSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommitmentForSixMonths
        fields = ['id', 'commitment_status', 'commitment_start_date',
                  'commitment_end_date', 'updated_at']


class MyCommitmentSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email')
    username = serializers.CharField(source='user.username')
    role = serializers.CharField(source='user.role')

    class Meta:
        model = CommitmentForSixMonths
        fields = ['id', 'email', 'username', 'role', 'commitment_status']

    def get_commitment_status(self, obj):
        """
        Get the commitment status for the authenticated user.
        If the user has no commitment, return False.
        """
        if obj.commitment_status is None:
            return False
        return obj.commitment_status
