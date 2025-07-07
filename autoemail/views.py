import logging
from django.conf import settings
from django.core.mail import send_mail
from celery import shared_task
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from collections import defaultdict
from datetime import timedelta


class TriggerProductListTask(APIView):
    def get(self, request):
        return Response({"message": "Task triggered successfully!"}, status=status.HTTP_200_OK)
