import json
import subprocess
import re
import os
import sys

class FunctionCallAgent:
    def __init__(self, tools_dir="tools"):
        self.tools_dir = tools_dir
        self.enabled_tools = {
            "haversine": self._run_haversine,
            "aqi": self._run_aqi,
            "calc": self._run_calc,
            "time": self._run_time,
            "check_system": self._run_check_system
        }

    def _run_haversine(self, args):
        try:
            lat1, lon1 = args.get('lat1'), args.get('lon1')
            lat2, lon2 = args.get('lat2'), args.get('lon2')
            if not all([lat1, lon1, lat2, lon2]): return "Error: Argumen koordinat tidak lengkap."
            
            cmd = ["python3", os.path.join(self.tools_dir, "kalkulator.py"), "haversine", str(lat1), str(lon1), str(lat2), str(lon2)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return res.stdout.strip() if res.returncode == 0 else f"Error: {res.stderr.strip()}"
        except Exception as e: return f"Error sistem haversine: {str(e)}"

    def _run_aqi(self, args):
        try:
            cmd = ["bash", os.path.join(self.tools_dir, "check_aqi.sh")] # Sesuaikan nama script AQI lu
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return res.stdout.strip() if res.returncode == 0 else f"Error AQI: {res.stderr.strip()}"
        except Exception as e: return f"Error sistem AQI: {str(e)}"

    def _run_calc(self, args):
        try:
            expr = args.get('expression')
            if not expr: return "Error: Tidak ada ekspresi matematika."
            cmd = ["python3", os.path.join(self.tools_dir, "kalkulator.py"), "eval", expr]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return res.stdout.strip() if res.returncode == 0 else f"Error Hitung: {res.stderr.strip()}"
        except Exception as e: return f"Error sistem kalkulator: {str(e)}"

    def _run_time(self, args):
        try:
            res = subprocess.check_output(["date", "+%H:%M WIB, %A %d %B %Y"], timeout=5)
            return "Sekarang pukul " + res.decode().strip()
        except Exception as e: return f"Error waktu: {str(e)}"

    def _run_check_system(self, args):
        try:
            sys.path.insert(0, os.path.join(self.tools_dir, ".."))
            from tools.check_system import check_system
            result = check_system()
            ram = result.get("available_ram_mb", "?")
            p8080 = result.get("port_8080", "?")
            p8082 = result.get("port_8082", "?")
            lines = [
                f"RAM tersedia: ~{ram}MB",
                f"Port 8080 (router text): {p8080}",
                f"Port 8082 (mata/vision): {p8082}",
            ]
            if ram is not None:
                if ram < 1200:
                    lines.append("⚠️ RAM kritis — tidak cukup untuk spawn model 4B (butuh min 1200MB).")
                elif ram < 2800:
                    lines.append("⚠️ RAM pas-pasan untuk model 4B (~2800MB). Lepas model utama dulu.")
                else:
                    lines.append("✅ RAM cukup untuk model 4B.")
            return " | ".join(lines)
        except Exception as e:
            return f"Error cek sistem: {str(e)}"

    def process_llm_response(self, llm_text):
        pattern = r"<call>(.*?)</call>"
        match = re.search(pattern, llm_text, re.DOTALL)

        if match:
            try:
                json_str = match.group(1).strip()
                if json_str.startswith("```json"): json_str = json_str.replace("```json", "").replace("```", "").strip()
                elif json_str.startswith("```"): json_str = json_str.replace("```", "").strip()

                data = json.loads(json_str)
                tool_name = data.get("tool")
                args = data.get("args", {})

                if tool_name in self.enabled_tools:
                    print(f"\n🤖 [TOOL] Memanggil '{tool_name}' dengan args: {args}")
                    result = self.enabled_tools[tool_name](args)
                    print(f"✅ [TOOL] Hasil: {result}\n")
                    return result, True 
                else:
                    return f"Error: Tool '{tool_name}' tidak ada di daftar.", False
            except json.JSONDecodeError:
                return "Error: Format JSON dari AI rusak.", False
            except Exception as e:
                return f"Error sistem: {str(e)}", False

        return None, False