"""Tool cek kondisi sistem: RAM, port 8080, port 8082."""
import json
import socket


def check_system():
    """
    Mengembalikan dict berisi:
      - available_ram_mb: RAM tersedia (MB)
      - port_8080: status port router LLM text
      - port_8082: status port vision server (mata)
    Dipanggil oleh FunctionCallAgent sebagai tool 'check_system'.
    """
    result = {}

    # 1) Available RAM
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    result["available_ram_mb"] = int(line.split()[1]) // 1024
                    break
    except Exception:
        result["available_ram_mb"] = None

    # 2) Cek port 8080 (router text)
    result["port_8080"] = _port_open(8080)

    # 3) Cek port 8082 (mata/vision)
    result["port_8082"] = _port_open(8082)

    return result


def _port_open(port, host="127.0.0.1", timeout=2):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return "aktif"
    except Exception:
        return "tidur"
