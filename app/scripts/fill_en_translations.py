import dotenv
from babel.messages.pofile import read_po, write_po
import openai
import logging

dotenv.load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

client = openai.Client()


def translate_text(text: str, target_language: str):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""You are a skillful multilanguage translatior specialized in UI i18n. Please translate the following text to {target_language}: {text}. Please only return the translated text and nothing else.""",
            }
        ],
        max_tokens=1000,
        temperature=0,
    )
    return response.choices[0].message.content


def parse_and_translate_po(file_path: str, target_language: str, limit=0):
    # Read the .po file
    with open(file_path, "rb") as po_file:
        catalog = read_po(po_file)

    print(f"Translating {len(catalog)} messages to {target_language}")

    translated_count = 0

    # Translate each message
    for message in catalog:
        # print("message:", message.id, message.string)
        if message.id and not message.string:
            print(f"Translating '{message.id}'")
            try:
                translated_text = translate_text(str(message.id), target_language)
                message.string = translated_text
                logger.info(f"Translated '{message.id}' to '{message.string}'")
                translated_count += 1
            except Exception:
                break
        else:
            print(f"Skipping '{message.id}'")
        if limit and translated_count >= limit:
            break

    # Write the updated catalog back to the .po file
    with open(file_path, "wb") as po_file:
        write_po(po_file, catalog)


def po_path_for_language(language_code):
    return f"app/translations/{language_code}/LC_MESSAGES/messages.po"


if __name__ == "__main__":
    for lang in ["en"]:
        po_file_path = po_path_for_language(lang)
        parse_and_translate_po(po_file_path, lang, limit=500)
