import os

import click

from app import create_app


@click.group()
def main():
    pass


@click.command()
def docs():
    """
    需要安装apidoc, `npm install apidoc -g`
    """
    os.system("apidoc -i app/ -o docs/")


@click.command()
def run():
    """
    运行开发服务器
    """
    app = create_app()
    app.run(host="0.0.0.0", port=5001)


@click.command()
@click.option(
    "--action",
    prompt="""请选择下一步操作:
1. 生成 .pot 模板文件
2. 为某个语言生成 .po 文件
3. 重新生成 .pot 模板文件并更新 .po 文件
4. 生产 .mo 文件
""",
    type=int,
)
def local(action):
    cfg_path = "babel.cfg"
    locale_folder = "app/locales"
    pot_filename = "messages.pot"
    pot_path = os.path.join(locale_folder, pot_filename)
    if not os.path.isdir(locale_folder):
        os.makedirs(locale_folder)
    if action == 1:
        os.system(
            "pybabel extract -F {cfg_path} -k lazy_gettext -o {pot_path} .".format(  # noqa: E501
                cfg_path=cfg_path, pot_path=pot_path
            )
        )
    elif action == 2:
        if not os.path.isfile(pot_path):
            pass
        lang_name = click.prompt("Please enter a language name")
        os.system(
            "pybabel init -i {pot_path} -d {locale_folder} -l {lang_name}".format(  # noqa: E501
                pot_path=pot_path,
                locale_folder=locale_folder,
                lang_name=lang_name,
            )
        )
    elif action == 3:
        os.system(
            "pybabel extract -F {cfg_path} -k lazy_gettext -o {pot_path} .".format(  # noqa: E501
                cfg_path=cfg_path, pot_path=pot_path
            )
        )
        os.system(
            "pybabel update -i {pot_path} -d {locale_folder}".format(
                pot_path=pot_path, locale_folder=locale_folder
            )
        )
    elif action == 4:
        os.system(
            "pybabel compile -d {locale_folder}".format(
                locale_folder=locale_folder
            )
        )


main.add_command(run)
main.add_command(local)
main.add_command(docs)

if __name__ == "__main__":
    main()
