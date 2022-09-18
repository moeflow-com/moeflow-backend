from flask import request
from flask_babel import gettext
from mongoengine import Q

from app.core.responses import MoePagination
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model
from app.exceptions import NoPermissionError
from app.models.team import Team, TeamPermission
from app.models.term import Term, TermBank
from app.validators.term import TermBankSchema, TermSchema


class TermBankAPI(MoeAPIView):
    @token_required
    @fetch_model(Team)
    def get(self, team):
        """
        @api {get} /v1/teams/<team_id>/term-banks?word=<word> 获取团队的所有术语库
        @apiVersion 1.0.0
        @apiName get_term_banks
        @apiGroup Term
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id
        @apiParam {String} [word] 模糊查询的名称

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有访问团队权限
        if not self.current_user.can(team, TeamPermission.ACCESS):
            raise NoPermissionError
        # 获取查询参数
        word = request.args.get("word")
        # 分页
        p = MoePagination()
        objects = team.term_banks(skip=p.skip, limit=p.limit, word=word)
        return p.set_objects(objects)

    @token_required
    @fetch_model(Team)
    def post(self, team):
        """
        @api {post} /v1/teams/<team_id>/term-banks 创建术语库
        @apiVersion 1.0.0
        @apiName add_term_bank
        @apiGroup Term
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id
        @apiParamExample {json} 请求示例
        {
           "name": "术语库名（1-40个字符）",
           "source_language": "language_id",
           "target_language": "language_id",
           "tip": "备注（0-140个字符）"
        }

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 权限检查
        if not self.current_user.can(team, TeamPermission.CREATE_TERM_BANK):
            raise NoPermissionError(gettext("您没有「创建术语库」权限，不能在此团队创建术语库"))
        data = self.get_json(TermBankSchema())
        TermBank.create(
            name=data["name"],
            team=team,
            source_language=data["source_language"],
            target_language=data["target_language"],
            tip=data["tip"],
            user=self.current_user,
        )
        return {"message": gettext("创建成功")}

    @token_required
    @fetch_model(TermBank)
    def put(self, term_bank):
        """
        @api {put} /v1/team-banks/<team_bank_id> 设置术语库
        @apiVersion 1.0.0
        @apiName edit_term_bank
        @apiGroup Term
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_bank_id 术语库id
        @apiParamExample {json} 请求示例
        {
           "name": "name"
        }

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not (
            self.current_user.can(term_bank.team, TeamPermission.CHANGE_TERM_BANK)
            or term_bank.user == self.current_user
        ):
            raise NoPermissionError(gettext("您没有「设置他人术语库」权限，只能设置自己创建的术语库"))
        data = self.get_json(TermBankSchema())
        term_bank.edit(
            name=data["name"],
            source_language=data["source_language"],
            target_language=data["target_language"],
            tip=data["tip"],
        )
        return {"message": gettext("修改成功")}

    @token_required
    @fetch_model(TermBank)
    def delete(self, term_bank):
        """
        @api {delete} /v1/term_banks/<term_bank_id> 删除术语库
        @apiVersion 1.0.0
        @apiName delete_term_bank
        @apiGroup Term
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} term_bank_id 术语库id

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有访问团队权限
        if not (
            self.current_user.can(term_bank.team, TeamPermission.DELETE_TERM_BANK)
            or term_bank.user == self.current_user
        ):
            raise NoPermissionError(gettext("您没有「删除他人术语库」权限，只能删除自己创建的术语库"))
        term_bank.clear()
        return {"message": gettext("删除成功")}


class TermListAPI(MoeAPIView):
    @token_required
    @fetch_model(TermBank)
    def get(self, term_bank):
        """
        @api {get} /v1/term-banks/<term_bank_id>/terms?word=<word> 获取术语库所有术语
        @apiVersion 1.0.0
        @apiName get_term
        @apiGroup Term
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id
        @apiParam {String} [word] 模糊查询术语

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有访问团队权限
        if not (
            self.current_user.can(term_bank.team, TeamPermission.ACCESS_TERM_BANK)
            or term_bank.user == self.current_user
        ):
            raise NoPermissionError(gettext("您没有「查看他人术语库」权限，只能查看自己创建的术语库中的术语"))
        # 获取查询参数
        word = request.args.get("word")
        # 分页
        p = MoePagination()
        objects = term_bank.terms(skip=p.skip, limit=p.limit)
        if word:
            objects = objects.filter(
                Q(source__icontains=word)
                | Q(target__icontains=word)
                | Q(tip__icontains=word)
            )
        return p.set_objects(objects)

    @token_required
    @fetch_model(TermBank)
    def post(self, term_bank):
        """
        @api {post} /v1/term-banks/<term_bank_id>/terms 创建术语
        @apiVersion 1.0.0
        @apiName add_term
        @apiGroup Term
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id
        @apiParamExample {json} 请求示例
        {
           "name": "name"
        }

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有创建术语权限
        if not (
            self.current_user.can(term_bank.team, TeamPermission.CREATE_TERM)
            or term_bank.user == self.current_user
        ):
            raise NoPermissionError(gettext("您没有「在他人术语库中增加术语」权限，只能在自己创建的术语库中增加术语"))
        # 获取data
        data = self.get_json(TermSchema())
        Term.create(
            term_bank=term_bank,
            source=data["source"],
            target=data["target"],
            tip=data["tip"],
            user=self.current_user,
        )
        return {"message": gettext("创建成功")}


class TermAPI(MoeAPIView):
    @token_required
    @fetch_model(Term)
    def put(self, term):
        """
        @api {put} /v1/terms/<term_id> 修改术语
        @apiVersion 1.0.0
        @apiName edit_term
        @apiGroup Term
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} project_set_id 项目集id
        @apiParamExample {json} 请求示例
        {
           "name": "name"
        }

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        term_bank = term.term_bank
        if not (
            self.current_user.can(term_bank.team, TeamPermission.CHANGE_TERM)
            or term_bank.user == self.current_user
            or term.user == self.current_user
        ):
            raise NoPermissionError(gettext("您没有「修改他人术语」权限，只能修改自己创建的术语或自己术语库中的术语"))
        # 获取data
        data = self.get_json(TermSchema())
        term.edit(source=data["source"], target=data["target"], tip=data["tip"])
        return {"message": gettext("修改成功")}

    @token_required
    @fetch_model(Term)
    def delete(self, term):
        """
        @api {delete} /v1/terms/<term_id> 删除术语
        @apiVersion 1.0.0
        @apiName delete_term
        @apiGroup Term
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} term_id 项目集id

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有访问团队权限
        term_bank = term.term_bank
        if not (
            self.current_user.can(term_bank.team, TeamPermission.DELETE_TERM)
            or term_bank.user == self.current_user
            or term.user == self.current_user
        ):
            raise NoPermissionError(gettext("您没有「删除他人术语」权限，只能删除自己创建的术语或自己术语库中的术语"))
        term.clear()
        return {"message": gettext("删除成功")}
