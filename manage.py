import os
import re
import click
import logging
from app import flask_app
from app.factory import init_db

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
def list_translations():
    from app.factory import babel

    with flask_app.app_context():
        print(babel.list_translations())


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


main.add_command(docs)
main.add_command(migrate)
main.add_command(list_translations)
main.add_command(mit_preprocess_file)
main.add_command(mit_preprocess_dir)

if __name__ == "__main__":
    main()
