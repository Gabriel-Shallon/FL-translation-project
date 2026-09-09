Put the text you want to translate in the 'input.txt' file.

Terminal commands:


--- For translate.py (AI Model)
Translates input.txt contents by an LLM API using codex rules and texts.

python translate.py [source_lang] [input_file] -t [target_lang]

Example:
python translate.py nymma input.txt -t english


--- For generate_prompt.py (Manual Workflow)
Generates a complete prompt for translation and update the codex.

python generate_prompt.py [source_lang] [input_file] -t [target_lang]

Example:
python generate_prompt.py nymma input.txt -t english


--- For generate_rules.py (Statistical System)
Reads Codex, learns new rules, saves rules on the codex.

python generate_rules.py [source_lang]

Example:
python generate_rules.py nymma