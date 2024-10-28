from babel.messages.pofile import read_po, write_po
import logging

logger = logging.getLogger(__name__)


def fill_msg_with_msg_id(file_path: str):
    # Read the .po file
    with open(file_path, "rb") as po_file:
        catalog = read_po(po_file)

    for message in catalog:
        if message.id and not message.string:
            message.string = message.id
        elif message.id != message.string:
            logger.warning(
                "%s L%s: MISMATCH message id %s / message string %s",
                file_path,
                message.lineno,
                message.id,
                message.string,
            )

    # Write the updated catalog back to the .po file
    with open(file_path, "wb") as po_file:
        write_po(po_file, catalog)


if __name__ == "__main__":
    po_file_path = "app/translations/zh/LC_MESSAGES/messages.po"
    fill_msg_with_msg_id(po_file_path)
