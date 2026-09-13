## What is this?

This is an old project of mine where I was translating posts in artificial languages from the website "Forgotten Languages" (FL for short). Most of the code here is "vibecoded", but the translations were thoroughly reviewed  manually by me (LLMs are very bad at breaking unknown tokens apart, so their translation accuracy was not the best. They were mainly responsible for translating the bigger and easier chunks of text, and I went behind fixing the potholes). I was able to translate almost all posts in Ladd Cryptolect from FL (I think the 23 missing were a variant of Ladd Cryptolect that would mess the Ladd codex up), and started Nymma (which seemed to contain more interesting posts than Ladd) with a little different approach, but the project was discontinued at this point.

## If you just want to read the translations (or about FL)

./FL Related/Translations
- All translations are here

./FL Related/Info, context and theories.docx
- Back when I did this project I compiled some resources to gather info about FL and wrote some of my theories at the time regarding it

./FL Related/By Ayndryl
- Ayndryl is a very important member from FL, and here you can find some of his own words about FL

./FL Related/Some Coords Related.kml
- At the time I found a list of coords apparently found around the FL website, so I went on google earth checking them and started schizophrenically marking anything that could be related lol

./FL Related/Translations (Images, Human made)
- The first translations I found that served as sample for me to start translating Ladd Cryptolect (finished) and Nymma (unfinished)

You may find text in portuguese in those files (I wasn't planning on posting them here, that's why they are in docx), but if you are down this rabbit hole, translating text in a known language should be no problem.

## How to use

Put the text you want to translate in the 'input.txt' file.

### Terminal commands:

translate.py (AI Model)
- Translates input.txt contents by an LLM API using codex rules and texts.

        python translate.py [source_lang] [input_file] -t [target_lang]

Example:
    python translate.py nymma input.txt -t english


generate_prompt.py (Manual Workflow)
- Generates a complete prompt for translation and update the codex.

        python generate_prompt.py [source_lang] [input_file] -t [target_lang]

Example:
    python generate_prompt.py nymma input.txt -t english


generate_rules.py (Statistical System)
- Reads Codex, learns new rules, saves rules on the codex.

        python generate_rules.py [source_lang]

Example:
    python generate_rules.py nymma
