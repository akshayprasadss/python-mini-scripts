import os
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Application, CandidateProfile, EmployerProfile, CustomUser, Job

User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "username", "password", "role", "phone"]

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            role=validated_data["role"],
            phone=validated_data["phone"]
        )
        return user

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ["employer"]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "email", "username", "role", "phone"]

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = ["candidate", "job", "applied_at"] 

class CandidateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = "__all__"
        read_only_fields = ["user", "is_active"]
        
    def validate_resume(self, value):
        ext = os.path.splitext(value.name)[1]

        allowed_extensions = ['.pdf', '.doc', '.docx']

        if ext.lower() not in allowed_extensions:
            raise serializers.ValidationError("Only PDF, DOC, DOCX files allowed.")

        if value.size > 5 * 1024 * 1024:  # 5MB limit
            raise serializers.ValidationError("File size must be under 5MB.")

        return value


class EmployerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerProfile
        fields = "__all__"
        read_only_fields = ["user", "verification_status", "is_active"]