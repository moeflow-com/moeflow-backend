from app.exceptions import NotExistError, TeamNotExistError
from tests import MoeTestCase


class NotExistTestCase(MoeTestCase):
    def test_not_exist_error(self):
        with self.app.test_request_context():
            self.assertEqual(NotExistError("Team").code, 3001)
            self.assertEqual(NotExistError("Project").code, 4001)
            self.assertEqual(NotExistError("Nothing").code, 104)
            self.assertEqual(NotExistError("Team"), TeamNotExistError)
