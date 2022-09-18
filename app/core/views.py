from flask import g

from flask_apikit.views import APIView
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class MoeAPIView(APIView):
    @property
    def current_user(self) -> "User":
        return g.get("current_user")
