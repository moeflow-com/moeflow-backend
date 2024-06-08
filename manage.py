import os
import re
import click
import logging

from app import flask_app, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    force=True,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
def migrate():
    """
    Initialize the database
    """
    init_db(flask_app)


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
            "pybabel compile -d {locale_folder}".format(locale_folder=locale_folder)
        )


@click.command("mit_file")
@click.option("--file", help="path to image file")
def mit_preprocess_file(file: str):
    from app.tasks.mit import preprocess_mit, MitPreprocessedImage

    proprocessed = preprocess_mit.delay(file, "CHT")
    proprocessed_result: dict = proprocessed.get()

    print("proprocessed", proprocessed_result)
    print("proprocessed", MitPreprocessedImage.from_dict(proprocessed_result))


@click.command("mit_dir")
@click.option("--dir", help="absolute path to a dir containing image files")
def mit_preprocess_dir(dir: str):
    from app.tasks.mit import preprocess_mit, MitPreprocessedImage

    for file in os.listdir(dir):
        if not re.match(r".*\.(jpg|png|jpeg)$", file):
            continue
        full_path = os.path.join(dir, file)
        proprocessed = preprocess_mit.delay(full_path, "CHT")
        proprocessed_result = MitPreprocessedImage.from_dict(proprocessed.get())

        print("proprocessed", proprocessed_result)
        for q in proprocessed_result.text_quads:
            print("text block", q.pts)
            print("  ", q.raw_text)
            print("  ", q.translated)


main.add_command(local)
main.add_command(docs)
main.add_command(migrate)
main.add_command(mit_preprocess_file)
main.add_command(mit_preprocess_dir)

if __name__ == "__main__":
    main()
