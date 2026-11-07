import re

file_path = "tools/rag_coordinator.py"
with open(file_path, 'r') as f:
    lines = f.readlines()

target_found = False
for i, line in enumerate(lines):
    if "context_parts.append" in line and "item['url']" in line:
        # Hitung jumlah spasi di awal baris target
        stripped = line.lstrip(' ')
        num_spaces = len(line) - len(stripped)
        
        # Buat indentasi dasar (sama dengan context_parts)
        base_indent = ' ' * num_spaces
        
        # Kode Auto-Learn dengan indentasi yang disesuaikan
        auto_learn_code = [
            f"{base_indent}from core.memory_manager import add_web_knowledge\n",
            f"{base_indent}fact_snippet = cleaned[:300].split('.')[0] + '.'\n",
            f"{base_indent}skip_phrases = ['dengan mengakses', 'by accessing', 'cookie', 'privacy policy', 'terms of use', 'copyright', 'hubungi kami']\n",
            f"{base_indent}if len(fact_snippet) > 15 and not any(s in fact_snippet.lower() for s in skip_phrases):\n",
            f"{base_indent}    try:\n",
            f"{base_indent}        status = add_web_knowledge(query, fact_snippet, item.get('url', ''))\n",
            f"{base_indent}        if status != 'duplicate':\n",
            f"{base_indent}            print(f'   💾 [Memory] Fakta baru disimpan: {fact_snippet[:70]}...')\n",
            f"{base_indent}    except Exception as e:\n",
            f"{base_indent}        print(f'   ⚠️ [Memory] Gagal simpan: {e}')\n"
        ]
        
        # Sisipkan kode tepat sebelum baris target
        for j, code_line in enumerate(auto_learn_code):
            lines.insert(i + j, code_line)
        target_found = True
        break

if target_found:
    with open(file_path, 'w') as f:
        f.writelines(lines)
    print("✅ Indentasi diperbaiki dan Auto-Learn disuntikkan!")
else:
    print("⚠️ Target tidak ditemukan.")
