import os
from babel.messages.pofile import read_po, write_po
import openai

client = openai.Client()


def translate_text(text, target_language="es"):
    response = client.completions.create(
        model="gpt4o",
        prompt=f"Translate the following text to {target_language}: {text}",
        max_tokens=1000,
        temperature=0.3,
    )
    return response.choices[0].text.strip()


def parse_and_translate_po(file_path, target_language="es"):
    # Read the .po file
    with open(file_path, "rb") as po_file:
        catalog = read_po(po_file)

    # Translate each message
    for message in catalog:
        if message.id and not message.string:
            translated_text = translate_text(message.id, target_language)
            message.string = translated_text
            print(f"Translated '{message.id}' to '{message.string}'")

    # Write the updated catalog back to the .po file
    with open(file_path, "wb") as po_file:
        write_po(po_file, catalog)


if __name__ == "__main__":
    po_file_path = "path/to/your/file.po"
    target_language = "es"  # Change this to your target language code
    parse_and_translate_po(po_file_path, target_language)
