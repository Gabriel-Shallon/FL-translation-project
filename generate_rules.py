import os
import re
import argparse
from collections import defaultdict
import sys

CODEX_DIR = 'codices'
AFFIX_LENGTHS = [2, 3, 4]
MIN_WORD_COUNT_THRESHOLD = 7
TOP_N_MAPPINGS = 3
MIN_FAMILY_PREFIX_LENGTH = 4

def get_codex_path(lang: str) -> str:
    """Retorna o caminho para o arquivo de códice com base no idioma."""
    return os.path.join(CODEX_DIR, f"{lang}.txt")

def parse_codex(codex_content: str) -> list[tuple[str, str, int]]:
    """Analisa o conteúdo do códice e extrai pares de texto fonte e traduzido."""
    text_blocks = re.findall(r'--- START OF TEXT (\d+).*?---\n(.*?)\n--- END OF TEXT \d+ ---', codex_content, re.DOTALL)
    
    all_pairs = []
    for text_num, block in text_blocks:
        paragraphs = block.strip().split('\n \n')
        for para in paragraphs:
            if ':::' in para:
                parts = para.split('\n:::\n')
                if len(parts) == 2:
                    source, translated = parts
                    all_pairs.append((source.strip(), translated.strip(), int(text_num)))
    return all_pairs

def preprocess_text(text: str, lang: str) -> str:
    """Limpa e prepara o texto para tokenização."""
    text = text.lower()
    text = text.replace('“', '"').replace('”', '"')

    if lang == 'source':
        text = re.sub(r"\b(sh)'(\w)", r"\1 \2", text)
    else:
        text = text.replace('-', ' ')
        # Remove completamente as palavras incertas e seu conteúdo
        text = re.sub(r'\[.*?\]', '', text)
        
    return text

def tokenize(text: str) -> list[str]:
    """Divide o texto em uma lista de tokens (palavras e pontuação)."""
    tokens = re.findall(r"[\w']+|[^\s\w]", text)
    return [token for token in tokens if token]

def align_tokens(source_tokens: list[str], translated_tokens: list[str]) -> list[tuple[str, str, int, int]]:
    """Alinha tokens entre o texto fonte e o traduzido usando palavras âncora."""
    anchors = []
    source_map = defaultdict(list)
    for i, token in enumerate(source_tokens):
        source_map[token].append(i)

    for i, token in enumerate(translated_tokens):
        if token in source_map:
            best_source_idx = min(source_map[token], key=lambda x: abs(x - i))
            anchors.append((best_source_idx, i))

    anchors.insert(0, (-1, -1))
    anchors.append((len(source_tokens), len(translated_tokens)))
    unique_anchors = sorted(list(set(anchors)))
    
    aligned_pairs = []
    for i in range(len(unique_anchors) - 1):
        start_anchor_src, start_anchor_trans = unique_anchors[i]
        end_anchor_src, end_anchor_trans = unique_anchors[i+1]
        
        source_segment = source_tokens[start_anchor_src + 1 : end_anchor_src]
        source_indices = range(start_anchor_src + 1, end_anchor_src)
        
        translated_segment = translated_tokens[start_anchor_trans + 1 : end_anchor_trans]
        translated_indices = range(start_anchor_trans + 1, end_anchor_trans)
        
        if source_segment and translated_segment and len(source_segment) == len(translated_segment):
            aligned_pairs.extend(zip(source_segment, translated_segment, source_indices, translated_indices))
            
    return aligned_pairs

def get_cv_pattern(affix: str) -> str:
    """Gera um padrão de Consoante/Vogal para um determinado afixo."""
    vowels = "aeiouäëïöü"
    pattern = ""
    for char in affix:
        pattern += 'V' if char in vowels else 'C'
    return pattern

def analyze_morphology(aligned_pairs: list[tuple[str, str, int, int]]) -> tuple[dict, dict]:
    """Analisa os pares alinhados para encontrar estatísticas de prefixos e sufixos."""
    prefix_stats = defaultdict(lambda: defaultdict(lambda: {'mappings': defaultdict(int), 'words': set()}))
    suffix_stats = defaultdict(lambda: defaultdict(lambda: {'mappings': defaultdict(int), 'words': set()}))

    for length in AFFIX_LENGTHS:
        for source_word, translated_word, _, _ in aligned_pairs:
            is_punct_source = not any(char.isalnum() for char in source_word)
            if is_punct_source: continue
            
            if len(source_word) > length and len(translated_word) > length:
                src_prefix = source_word[:length]
                trans_prefix = translated_word[:length]
                pattern = get_cv_pattern(src_prefix)
                prefix_stats[pattern][src_prefix]['mappings'][trans_prefix] += 1
                prefix_stats[pattern][src_prefix]['words'].add(source_word)

                src_suffix = source_word[-length:]
                trans_suffix = translated_word[-length:]
                pattern = get_cv_pattern(src_suffix)
                suffix_stats[pattern][src_suffix]['mappings'][trans_suffix] += 1
                suffix_stats[pattern][src_suffix]['words'].add(source_word)
    
    return prefix_stats, suffix_stats

def build_statistics(pairs: list[tuple[str, str, int, int]]) -> dict:
    """Constrói estatísticas de tradução palavra por palavra."""
    stats = defaultdict(lambda: defaultdict(int))
    for source_word, translated_word, _, _ in pairs:
        is_punct_source = not any(char.isalnum() for char in source_word)
        is_punct_translated = not any(char.isalnum() for char in translated_word)
        
        if not is_punct_source and not is_punct_translated:
            stats[source_word][translated_word] += 1
    return stats

def get_pos_from_word(english_word: str, word_to_pos_map: dict) -> str:
    """Determina a classe gramatical (Part-of-Speech) de uma palavra em inglês."""
    if english_word in word_to_pos_map:
        return word_to_pos_map[english_word]
    if english_word.endswith('ing') or english_word.endswith('ed'):
        return "VERB"
    if english_word.endswith('ly'):
        return "ADV"
    if english_word.endswith(('tion', 'sion', 'ness', 'ment', 'ity')):
        return "NOUN"
    if english_word.endswith(('al', 'ous', 'ful', 'less', 'able', 'ible')):
        return "ADJ"
    return "NOUN"

def build_pos_statistics(aligned_pairs: list[tuple[str, str, int, int]]) -> tuple[dict, dict]:
    """Constrói estatísticas de classe gramatical para as palavras da língua fonte."""
    pos_map = {
        'NOUN': ['time', 'world', 'language', 'part', 'life', 'man', 'people', 'god', 'way', 'word', 'hand', 'day'],
        'VERB': ['is', 'are', 'was', 'be', 'have', 'has', 'do', 'does', 'can', 'could', 'will', 'would', 'may', 'might', 'should'],
        'ADJ': ['other', 'more', 'new', 'good', 'great', 'first', 'last', 'own', 'same', 'old', 'little', 'much'],
        'PREP': ['of', 'in', 'to', 'for', 'with', 'on', 'at', 'from', 'by', 'about', 'as', 'into', 'like', 'through', 'after', 'over'],
        'DET': ['the', 'a', 'an', 'this', 'that', 'these', 'those', 'all', 'some', 'any', 'no', 'every', 'each'],
        'CONJ': ['and', 'but', 'or', 'so', 'if', 'when', 'because', 'that'],
        'PRON': ['it', 'he', 'you', 'they', 'we', 'who', 'which', 'what', 'his', 'your', 'their', 'us', 'them']
    }
    word_to_pos = {word: pos for pos, words in pos_map.items() for word in words}
    nymma_pos_counts = defaultdict(lambda: defaultdict(int))
    for nymma_word, english_word, _, _ in aligned_pairs:
        pos = get_pos_from_word(english_word, word_to_pos)
        nymma_pos_counts[nymma_word][pos] += 1
    return nymma_pos_counts, word_to_pos

def analyze_semantics(aligned_pairs: list[tuple[str, str, int, int]]) -> dict:
    """Analisa a semântica para agrupar palavras da língua fonte por radical em inglês."""
    stem_to_nymma = defaultdict(lambda: defaultdict(int))
    def simple_english_stemmer(word):
        if len(word) < 4: return word
        suffixes = ['s', 'es', 'ed', 'ing', 'ly', 'er', 'or', 'ion', 'tion', 'ation', 'ity', 'ness']
        for suffix in sorted(suffixes, key=len, reverse=True):
            if word.endswith(suffix): return word[:-len(suffix)]
        return word

    for nymma_word, english_word, _, _ in aligned_pairs:
        is_punct_source = not any(char.isalnum() for char in nymma_word)
        if is_punct_source: continue
        
        stem = simple_english_stemmer(english_word)
        if len(stem) > 2: stem_to_nymma[stem][nymma_word] += 1
    return stem_to_nymma

def format_morphology_report(prefix_stats: dict, suffix_stats: dict) -> str:
    """Formata a seção de morfologia do relatório."""
    prefix_details, suffix_details = {}, {}
    
    def _process_affix_stats(pattern_dict: dict, affix_type: str, details_dict: dict) -> list:
        processed_list = []
        for affix, data in pattern_dict.items():
            word_count = len(data['words'])
            if word_count < MIN_WORD_COUNT_THRESHOLD: continue
            
            total_mappings = sum(data['mappings'].values())
            if total_mappings == 0: continue

            sorted_mappings = sorted(data['mappings'].items(), key=lambda item: item[1], reverse=True)
            top_mappings = sorted_mappings[:TOP_N_MAPPINGS]
            
            mapping_str_parts = []
            for trans_affix, count in top_mappings:
                percentage = (count / total_mappings) * 100
                display_affix = f"{trans_affix}-" if affix_type == 'prefix' else f"-{trans_affix}"
                mapping_str_parts.append(f"{display_affix} ({percentage:.0f}%)")
            mapping_str = f"[{', '.join(mapping_str_parts)}]"
            
            details_dict[affix] = f"-> {mapping_str:<40} (Found in {word_count} words)"
            processed_list.append({'affix': affix, 'word_count': word_count})

        processed_list.sort(key=lambda x: x['word_count'], reverse=True)
        return processed_list

    report_lines = ["[1. DETECTED MORPHOLOGY (Structural & Probabilistic Mapping)]"]
    
    report_lines.append("   --- PREFIXES (Start of word) ---")
    for pattern in sorted(prefix_stats.keys()):
        processed = _process_affix_stats(prefix_stats[pattern], 'prefix', prefix_details)
        if processed:
            report_lines.append(f"   [Pattern: {pattern}-]")
            for item in processed:
                line = f"      {item['affix'] + '-':<7} {prefix_details[item['affix']]}"
                report_lines.append(line)

    report_lines.append("\n   --- SUFFIXES (End of word) ---")
    for pattern in sorted(suffix_stats.keys()):
        processed = _process_affix_stats(suffix_stats[pattern], 'suffix', suffix_details)
        if processed:
            report_lines.append(f"   [Pattern: -{pattern}]")
            for item in processed:
                line = f"      {'-' + item['affix']:<7} {suffix_details[item['affix']]}"
                report_lines.append(line)

    return "\n".join(report_lines)

def format_dictionary_report(stats: dict, pos_stats: dict) -> str:
    """Formata a seção de dicionário do relatório."""
    pos_order = ['NOUN', 'VERB', 'ADJ', 'FUNC', 'ADV', 'UNCLASSIFIED']
    pos_headers = {'NOUN': 'NOUNS', 'VERB': 'VERBS', 'ADJ': 'ADJECTIVES', 'FUNC': 'FUNCTION WORDS (Pronouns, Prepositions, etc.)', 'ADV': 'ADVERBS', 'UNCLASSIFIED': 'UNCLASSIFIED'}
    def get_pos_category(p):
        return 'FUNC' if p in ['PREP', 'DET', 'CONJ', 'PRON'] else (p if p in pos_order else 'UNCLASSIFIED')
    
    categorized_words = defaultdict(list)
    for source_word, translations in stats.items():
        total = sum(translations.values())
        if total == 0: continue
        
        most_likely_pos = max(pos_stats.get(source_word, {}), key=pos_stats[source_word].get, default='UNCLASSIFIED')
        categorized_words[get_pos_category(most_likely_pos)].append({'source': source_word, 'translations': translations, 'total': total})
    
    report_lines = ["[2. DICTIONARY (Categorized by Part-of-Speech)]"]
    for i, pos_key in enumerate(pos_order):
        if categorized_words[pos_key]:
            section_letter = chr(ord('A') + i)
            report_lines.append(f"\n   [2.{section_letter}. {pos_headers[pos_key]}]")
            
            sorted_entries = sorted(categorized_words[pos_key], key=lambda x: -x['total'])
            
            for entry in sorted_entries:
                sorted_translations = sorted(entry['translations'].items(), key=lambda x: -x[1])
                for trans, count in sorted_translations:
                    conf = count / entry['total']
                    line = f"      {'[VERIFIED]':<15} {entry['source']:<15} = {trans:<15} (Conf: {conf:.0%} | Seen: {count}x)"
                    report_lines.append(line)
    return "\n".join(report_lines)

def format_semantic_report(stem_groups: dict) -> str:
    """Formata a seção de famílias de palavras do relatório."""
    family_lines = ["\n[3. WORD FAMILIES (Stem-based)]"]
    fam_list = []
    for stem, nymma_words_dict in stem_groups.items():
        if len(nymma_words_dict) < 2: continue
        prefix_to_words = defaultdict(list)
        for nymma_word in nymma_words_dict.keys():
            if len(nymma_word) >= MIN_FAMILY_PREFIX_LENGTH:
                prefix_to_words[nymma_word[:MIN_FAMILY_PREFIX_LENGTH]].append(nymma_word)
        for prefix, family in prefix_to_words.items():
            if len(family) > 1:
                fam_list.append({'stem': stem, 'prefix': prefix, 'family': sorted(family)})
    fam_list.sort(key=lambda x: (x['stem'], x['prefix']))
    for item in fam_list:
        family_lines.append(f"   - Root: '{item['stem']}' -> Nymma Family ({item['prefix']}-): [{', '.join(item['family'])}]")
    return "\n".join(family_lines)

def write_report_to_codex(filepath: str, report: str):
    """Escreve o relatório gerado de volta no arquivo de códice, sob a seção MANUAL."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except FileNotFoundError:
        print(f"[ERROR] Codex file not found at '{filepath}'")
        sys.exit(1)

    manual_block_regex = re.compile(r'^--- MANUAL ---\n.*?\n--- END OF MANUAL ---\n', re.DOTALL | re.MULTILINE)
    new_manual_section = f"--- MANUAL ---\n{report}\n\n--- END OF MANUAL ---\n"
    
    if manual_block_regex.search(original_content):
        new_content = manual_block_regex.sub(new_manual_section, original_content, 1)
    else:
        new_content = new_manual_section + "\n" + original_content

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        print(f"[ERROR] Could not write to codex file: {e}")
        sys.exit(1)

def main():
    """Função principal que orquestra a análise do códice e a geração do relatório."""
    parser = argparse.ArgumentParser(description="Generate statistical translation rules from a codex file.")
    parser.add_argument("source_lang", type=str, help="The source language (filename in 'codices').")
    
    args = parser.parse_args()
    codex_path = get_codex_path(args.source_lang)
    
    try:
        with open(codex_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: Codex file '{codex_path}' not found.")
        return
        
    print(f"Processing codex: {codex_path}")
    
    text_pairs = parse_codex(content)
    if not text_pairs:
        print("No text pairs found in the codex. Exiting.")
        return
        
    all_aligned_pairs = []
    for source, trans, num in text_pairs:
        processed_source = preprocess_text(source, 'source')
        processed_trans = preprocess_text(trans, 'translated')
        source_tokens = tokenize(processed_source)
        trans_tokens = tokenize(processed_trans)
        aligned = align_tokens(source_tokens, trans_tokens)
        all_aligned_pairs.extend(aligned)
        
    prefix_stats, suffix_stats = analyze_morphology(all_aligned_pairs)
    morphology_report = format_morphology_report(prefix_stats, suffix_stats)
    
    pos_stats, _ = build_pos_statistics(all_aligned_pairs)
    dictionary_stats = build_statistics(all_aligned_pairs)
    semantic_groups = analyze_semantics(all_aligned_pairs)

    dictionary_report = format_dictionary_report(dictionary_stats, pos_stats)
    semantic_report = format_semantic_report(semantic_groups)
    
    full_report = f"{morphology_report}\n\n{dictionary_report}\n{semantic_report}"
    
    write_report_to_codex(codex_path, full_report)
    
    print(f"\n[SUCCESS] Analysis complete. The manual has been updated in '{codex_path}'.")

if __name__ == "__main__":
    main()