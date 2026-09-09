import os
import re
import argparse
import itertools
import time
import requests
from openai import OpenAI

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyBUKRdSYcItlxa5qjoczrrqTV3rm2repUs')
CODEX_DIR = 'codices'

MODEL_PRIORITY = [
   "gemini-2.5-pro",
   "gemini-pro-latest",
   "deep-research-pro-preview-12-2025",
   "gemini-3-pro-preview",
   "gemini-2.5-flash",
   "gemini-flash-latest",
   "gemini-3-flash-preview",
   "gemini-2.5-flash-preview-09-2025",
   "gemma-3-27b-it",
   "gemini-2.0-flash",
   "gemini-2.0-flash-001",
   "gemini-2.0-flash-exp",
   "gemma-3-12b-it",
   "gemini-2.5-flash-lite",
   "gemini-flash-lite-latest",
   "gemini-2.5-flash-lite-preview-09-2025",
   "gemini-2.0-flash-lite",
   "gemini-2.0-flash-lite-001",
   "gemini-2.0-flash-lite-preview-02-05",
   "gemini-2.0-flash-lite-preview",
   "gemma-3-4b-it",
   "gemma-3n-e4b-it",
   "gemma-3-1b-it",
   "gemma-3n-e2b-it",
   "gemini-exp-1206"
]

def get_codex_path(lang: str) -> str:
    return os.path.join(CODEX_DIR, f"{lang}.txt")

def get_codex_content(lang: str) -> str:
    path = get_codex_path(lang)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"WARNING: Codex file '{path}' not found."
    except Exception as e:
        return f"ERROR READING CODEX FILE: {e}\n"

def get_next_text_number(codex_content: str) -> int:
    matches = re.findall(r'--- START OF TEXT (\d+)', codex_content)
    if not matches:
        return 1
    numbers = map(int, matches)
    return max(numbers) + 1

def format_for_codex(source_text: str, translated_text: str) -> str:
    src_paras = [p.strip() for p in source_text.split('\n') if p.strip()]
    trans_paras = [p.strip() for p in translated_text.split('\n') if p.strip()]
    formatted_blocks = []
    
    for src, trans in itertools.zip_longest(src_paras, trans_paras, fillvalue="[MISSING CORRESPONDING PARAGRAPH]"):
        block = f"{src}\n:::\n{trans}"
        formatted_blocks.append(block)
    return "\n \n".join(formatted_blocks)

def append_to_codex(lang: str, formatted_content: str, text_num: int):
    path = get_codex_path(lang)
    entry_header = f"\n--- START OF TEXT {text_num} (TITLE_HERE) ---\n\n"
    entry_footer = f"\n\n--- END OF TEXT {text_num} ---"
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry_header)
            f.write(formatted_content)
            f.write(entry_footer)
        print(f"\n[SUCCESS] Text {text_num} saved to '{path}'.")
    except Exception as e:
        print(f"\n[ERROR] Failed to save to codex: {e}")

def build_prompt(codex: str, source_lang: str, target_lang: str, new_text: str) -> str:
    return f"""
Act as an expert linguist and decipherer, specializing in the "{source_lang}" language.

Below, I am providing a Codex containing several texts in "{source_lang}" and their faithful translations. This is your primary reference material. Your task is to use this Codex to perform the most accurate translation possible of the "NEW TEXT TO TRANSLATE" into the "{target_lang}" language.

STRICT RULES:
1.  Rely primarily on the vocabulary, style, and grammatical structures present in the Codex.
2.  Maintain a tone and context consistent with the examples in the Codex.
3.  Translate only the requested text. Your output must be ONLY the clean translation, with no additional comments or explanations.
4.  Maintain the paragraph formatting of the original text EXACTLY. If the input has 5 paragraphs, output exactly 5 paragraphs.
5.  Text inside square brackets [] in the English translation part of the Codex represents a list of possible meanings for a rare word. Use this information to inform your final translation.
6.  The "NEW TEXT TO TRANSLATE" may contain sections already written in a known language (like English). You must translate these sections normally into the target language ("{target_lang}") along with the deciphered parts. Treat them as an integral part of the text. If you find a section that is in an other unknown language (other than "{source_lang}"), just copy it to the correct position.
7.  If you encounter a word in the "{source_lang}" text that is NOT precisely defined in the Codex and whose meaning cannot be inferred with high certainty from its morphology and context, you MUST translate it with your best guess and enclose that guess in square brackets.

--- START OF {source_lang.upper()} CODEX ---
{codex}
--- END OF CODEX ---

--- NEW TEXT TO TRANSLATE (from "{source_lang}" to "{target_lang}") ---
{new_text}
--- END OF NEW TEXT ---

TRANSLATION:
"""

def translate_with_google_fallback(prompt: str) -> str:
    if "YOUR_KEY" in GOOGLE_API_KEY:
         return "ERROR: Google API key not configured."

    client = OpenAI(
        api_key=GOOGLE_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    for model in MODEL_PRIORITY:
        print(f"Trying model: {model}...")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a precise translator. Output only the translation."},
                    {"role": "user", "content": prompt}
                ],
                stream=False,
                temperature=0.1,
                max_tokens=8192
            )
            result = response.choices[0].message.content
            if result:
                print(f"-> Success with {model}!")
                return result
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "402" in error_msg:
                print(f"-> Quota exceeded/Error on {model}. Trying next...")
                time.sleep(1)
                continue
            else:
                return f"API ERROR ({model}): {error_msg}"
    
    return "API ERROR: All models failed or are out of quota."

def main():
    parser = argparse.ArgumentParser(description="AI Translation (Google Experimental Models).")
    parser.add_argument("source_lang", type=str, help="Source language.")
    parser.add_argument("input_file", type=str, help="Input text file.")
    parser.add_argument("-t", "--target_lang", type=str, default="english", help="Target language.")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            new_text_to_translate = f.read()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    print(f"Starting translation '{args.source_lang}' -> '{args.target_lang}'")
    
    codex_content = get_codex_content(args.source_lang)
    full_prompt = build_prompt(codex_content, args.source_lang, args.target_lang, new_text_to_translate)
    
    tokens = len(full_prompt) / 4
    print(f"Prompt size: ~{int(tokens)} tokens.")
    
    translation = translate_with_google_fallback(full_prompt)
    
    if "API ERROR" in translation or "ERROR:" in translation:
        print("\n" + "="*30)
        print(translation)
        print("[CANCELLED] Not saved due to error.")
        return

    print("\n--- TRANSLATION OUTPUT ---\n")
    print(translation)

    print("\n" + "="*30)
    print("UPDATING CODEX...")
    next_num = get_next_text_number(codex_content)
    formatted = format_for_codex(new_text_to_translate, translation)
    append_to_codex(args.source_lang, formatted, next_num)

if __name__ == "__main__":
    main()