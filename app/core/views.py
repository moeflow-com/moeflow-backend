from flask import g
from flask_apikit.views import APIView
from app.models.user import User


class MoeAPIView(APIView):
    @property
    def current_user(self) -> User:
        return g.get("current_user")
