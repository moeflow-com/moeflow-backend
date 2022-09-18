from app.utils import default
from mongoengine.base.fields import ObjectIdField
from mongoengine.fields import ListField
from app.constants.output import OutputStatus, OutputTypes
from app.exceptions.output import OutputNotExistError
import datetime
from flask import current_app

from app.utils.logging import logger
from mongoengine import DateTimeField, Document, IntField, ReferenceField
from typing import List, TYPE_CHECKING
import oss2
from app import oss

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.target import Target
    from app.models.user import User


class Output(Document):
    """项目的导出"""

    project = ReferenceField("Project", db_field="p", required=True)
    target = ReferenceField("Target", db_field="t", required=True)
    user = ReferenceField("User", db_field="u")  # 操作人
    status = IntField(db_field="s", default=OutputStatus.QUEUING)
    type = IntField(db_field="ty", default=OutputTypes.ALL)
    create_time = DateTimeField(db_field="ct", default=datetime.datetime.utcnow)
    file_ids_include = ListField(ObjectIdField(), default=list)
    file_ids_exclude = ListField(ObjectIdField(), default=list)

    @classmethod
    def create(
        cls,
        /,
        *,
        project: "Project",
        target: "Target",
        user: "User",
        type: int,
        file_ids_include: List[str] = None,
        file_ids_exclude: List[str] = None,
    ) -> "Output":
        output = cls(
            project=project,
            target=target,
            user=user,
            type=type,
            file_ids_include=file_ids_include,
            file_ids_exclude=file_ids_exclude,
        ).save()
        return output

    @classmethod
    def delete_real_files(cls, outputs):
        try:
            oss.delete(
                current_app.config["OSS_OUTPUT_PREFIX"],
                [str(output.id) + ".zip" for output in outputs],
            )
        except (oss2.exceptions.NoSuchKey) as e:
            logger.error(e)
        except (Exception) as e:
            logger.error(e)

    def delete_real_file(self):
        try:
            oss.delete(current_app.config["OSS_OUTPUT_PREFIX"], str(self.id) + ".zip")
        except (oss2.exceptions.NoSuchKey) as e:
            logger.error(e)
        except (Exception) as e:
            logger.error(e)

    def clear(self):
        self.delete()

    @classmethod
    def by_id(cls, id):
        file = cls.objects(id=id).first()
        if file is None:
            raise OutputNotExistError
        return file

    def to_api(self):
        data = {
            "id": str(self.id),
            "project": self.project.to_api(),
            "target": self.target.to_api(),
            "user": default(self.user, None, "to_api"),
            "type": self.type,
            "status": self.status,
            "status_details": OutputStatus.to_api(),
            "file_ids_include": [str(id) for id in self.file_ids_include],
            "file_ids_exclude": [str(id) for id in self.file_ids_exclude],
            "create_time": self.create_time.isoformat(),
        }
        if self.status == OutputStatus.SUCCEEDED:
            data["link"] = (
                oss.sign_url(
                    current_app.config["OSS_OUTPUT_PREFIX"], str(self.id) + ".zip"
                )
                if self.type == OutputTypes.ALL
                else oss.sign_url(
                    current_app.config["OSS_OUTPUT_PREFIX"], str(self.id) + ".txt"
                )
            )
        return data
