import yaml
import requests
import json
import re
from tools.kalkulator import hitung_matematika
from tools.rag_coordinator import execute_rag
from tools.file_manager import handle_file_action, detect_file_action
from tools.llm_online import ask_online

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def is_math_query(text):
    return bool(re.search(r'\d+\s*[\+\-\*\/xX×]\s*\d+', text))

def chat_with_local_llm(messages, config, system_prompt=""):
    api_url = config["llm_local"]["api_url"]
    model_name = config["llm_local"]["model_name"]
    final_messages = messages.copy()
    if system_prompt: final_messages.insert(0, {"role": "system", "content": system_prompt})
    
    payload = {
        "model": model_name, "messages": final_messages,
        "max_tokens": config["llm_local"]["max_tokens"],
        "temperature": config["llm_local"]["temperature"],
        "repeat_penalty": 1.15, "stream": True
    }
    
    print(f"\n🤖 [Otak LLM Lokal] Memproses...\n")
    try:
        response = requests.post(api_url, json=payload, stream=True)
        response.raise_for_status()
        full_response = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str.strip() == "[DONE]": break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            print(content, end="", flush=True)
                            full_response += content
                    except: continue
        print("\n\n✅ Selesai.")
        return full_response
    except Exception as e:
        print(f"\n❌ Error LLM Lokal: {e}. Beralih ke Otak Online...")
        return None

def main():
    config = load_config()
    print("=== Mesin AI Modular v0.7 ===")
    print("Mode: Math + RAG + File System + 3 Otak Online (Groq/OR/Gemini)")
    print("Ketik 'exit' untuk berhenti.\n")
    
    messages = [] 
    
    while True:
        user_input = input(" Anda: ")
        if user_input.lower() in ["exit", "keluar"]: break
            
        # Routing Matematika
        if is_math_query(user_input):
            hasil = hitung_matematika(user_input)
            print(f"⚡ [Otak Cepat]: {hasil}")
            messages.append({"role": "user", "content": user_input})
            messages.append({"role": "assistant", "content": str(hasil)})
            continue

        # Routing File
        file_cmd = detect_file_action(user_input)
        if file_cmd:
            result = handle_file_action(file_cmd['action'], file_cmd['path'], file_cmd.get('content', ''), file_cmd.get('line_spec'))
            print(f"💾 [File Manager]: {result}")
            messages.append({"role": "user", "content": user_input})
            messages.append({"role": "assistant", "content": result})
            continue

        # Routing RAG + LLM
        print("\n🔍 [RAG Coordinator] Mencari sumber...")
        rag_context = execute_rag(user_input)
        
        # Coba Lokal dulu
        system_prompt = f"Jawab berdasarkan DATA SUMBER ini. Jangan mengarang.\n\nDATA SUMBER:\n{rag_context}\n\nPertanyaan: {user_input}"
        ai_response = chat_with_local_llm([], config, system_prompt=system_prompt)
        
        # Fallback ke Online jika Lokal gagal
        if not ai_response:
            print("\n🔄 [Fallback] Menggunakan Otak Online...")
            ai_response = ask_online([{"role": "user", "content": user_input}], rag_context)
            print(ai_response)

        if ai_response:
            messages.append({"role": "user", "content": user_input})
            messages.append({"role": "assistant", "content": ai_response})

if __name__ == "__main__":
    main()
