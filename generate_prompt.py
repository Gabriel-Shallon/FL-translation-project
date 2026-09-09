import os
import re
import argparse
import itertools
import sys
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

CODEX_DIR = 'codices'

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
        print(f"\n[SUCCESS] Text {text_num} added to file '{path}'.")
        print("Remember to edit the (TITLE_HERE).")
    except Exception as e:
        print(f"\n[ERROR] Could not save to codex: {e}")

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
7.  If you encounter a word in the "{source_lang}" text that is NOT precisely defined in the Codex and whose meaning cannot be inferred with high certainty from its morphology and context, you MUST translate it with your best guess and enclose that guess in square brackets. DO NOT put more than one word inside brackets, even if there is 2 or more unknow words side by side.

--- START OF {source_lang.upper()} CODEX ---
{codex}
--- END OF CODEX ---

--- NEW TEXT TO TRANSLATE (from "{source_lang}" to "{target_lang}") ---
{new_text}
--- END OF NEW TEXT ---

TRANSLATION:
"""

def main():
    parser = argparse.ArgumentParser(description="Translation Tool with Manual Playground Workflow.")
    parser.add_argument("source_lang", type=str, help="The source language (filename in 'codices').")
    parser.add_argument("input_file", type=str, help="Path to the .txt file to be translated.")
    parser.add_argument("-t", "--target_lang", type=str, default="english", help="Target language.")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            new_text_to_translate = f.read()
    except Exception as e:
        print(f"ERROR READING INPUT FILE: {e}")
        return

    print(f"Preparing prompt for '{args.source_lang}' -> '{args.target_lang}'...")
    
    codex_content = get_codex_content(args.source_lang)
    full_prompt = build_prompt(codex_content, args.source_lang, args.target_lang, new_text_to_translate)
    
    try:
        if not PYPERCLIP_AVAILABLE:
            raise RuntimeError("Library 'pyperclip' not found. Displaying prompt for manual copy.")
        pyperclip.copy(full_prompt)
        print("\n[SUCCESS] The full prompt has been copied to your clipboard!")
    except Exception as e:
        print(f"\n[WARNING] {e}")
        print("--- START OF PROMPT (copy manually) ---")
        print(full_prompt)
        print("--- END OF PROMPT ---")

    print("\n" + "="*50)
    print("ACTION REQUIRED:")
    print("1. Go to the Gemini playground (e.g., aistudio.google.com).")
    print("2. Paste (Ctrl+V) the prompt and generate the translation.")
    print("3. Copy the generated translation.")
    print("4. Paste the complete translation here in the terminal.")
    print("5. Press Ctrl+D (Linux/macOS) or Ctrl+Z followed by Enter (Windows) to finish.")
    print("="*50)
    print("\nPaste the translation below and finalize with the EOF key:")

    translated_text = sys.stdin.read().strip()

    if not translated_text:
        print("\n[CANCELLED] No translation was entered. The codex was not updated.")
        return
        
    print("\n...Translation received. Updating the codex...")
    
    next_num = get_next_text_number(codex_content)
    formatted_entry = format_for_codex(new_text_to_translate, translated_text)
    append_to_codex(args.source_lang, formatted_entry, next_num)

if __name__ == "__main__":
    main()