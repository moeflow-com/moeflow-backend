# models

Persistent models in MongoDB.

## Core

### User



### Team

- `Team`
- `Application`

### Projects

- `Project`
- `ProjectSet`

### Inside project

- `File`
- `Source`
- `Target`

## etc

- `VCode`

<!--
git grep -w class -- app/models/

------- global

app/models/user.py:class User(Document):

app/models/file.py:class Filename:
app/models/file.py:class File(Document):
app/models/file.py:class FileTargetCache(Document):
app/models/file.py:class Source(Document):
app/models/file.py:class Translation(Document):
app/models/file.py:class Tip(Document):


------ Team

app/models/team.py:class TeamPermission(PermissionMixin):
app/models/team.py:class TeamRole(RoleMixin, Document):
app/models/team.py:class Team(GroupMixin, Document):
app/models/team.py:class TeamUserRelation(RelationMixin, Document):

------ Project

app/models/project.py:class ProjectSet(Document):
app/models/project.py:class ProjectRole(RoleMixin, Document):
app/models/project.py:class ProjectUserRelation(RelationMixin, Document):

------ inside Project

app/models/project.py:class Project(GroupMixin, Document):
app/models/language.py:class Language(Document):
app/models/message.py:class Message(Document):
app/models/output.py:class Output(Document):

------

app/models/project.py:class ProjectAllowApplyType(AllowApplyType):
app/models/project.py:class ProjectPermission(PermissionMixin):
app/models/target.py:class Target(Document):

app/models/term.py:class TermBank(Document):
app/models/term.py:class TermGroup(Document):
app/models/term.py:class Term(Document):

app/models/invitation.py:class InvitationStatus:
app/models/invitation.py:class Invitation(Document):

app/models/application.py:class ApplicationStatus:
app/models/application.py:class Application(Document):

app/models/v_code.py:class VCode(Document):
app/models/v_code.py:class Captcha(VCode):

app/models/site_setting.py:class SiteSetting(Document):
-->
