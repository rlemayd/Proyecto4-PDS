from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from telegram_bot.views import TutorialBotView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webhooks/tutorial/', csrf_exempt(TutorialBotView.as_view())),
]
