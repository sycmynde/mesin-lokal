#!/bin/bash

set -u

echo "========================================"
echo " MESIN AI v0.8 — FULL REGRESSION CHECK"
echo "========================================"
echo

FAIL=0

echo "▶ Syntax check..."

python3 -m py_compile \
    main.py \
    providers/local.py \
    core/dispatcher.py \
    test_tier_v08.py \
    test_dispatcher_v08.py \
    2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Syntax OK"
else
    echo "❌ Syntax FAIL"
    FAIL=1
fi

echo
echo "▶ Tier architecture test..."

python3 test_tier_v08.py
if [ $? -ne 0 ]; then
    FAIL=1
fi

echo
echo "▶ Dispatcher mock test..."

python3 test_dispatcher_v08.py
if [ $? -ne 0 ]; then
    FAIL=1
fi

echo
echo "▶ Context isolation test..."

python3 test_context_v08.py
if [ $? -ne 0 ]; then
    FAIL=1
fi

echo
echo "▶ Memory isolation test..."

python3 test_memory_v08.py
if [ $? -ne 0 ]; then
    FAIL=1
fi

echo
echo "▶ Context budget test..."
python3 test_context_budget_v08.py
if [ $? -ne 0 ]; then
    FAIL=1
fi

echo
echo "========================================"

if [ "$FAIL" -eq 0 ]; then
    echo "✅ MESIN AI v0.8 — SEMUA TEST LULUS"
    echo
    echo "   ⚡ 0.8B  → Local Instan"
    echo "   🎯 2B    → Local Default"
    echo "   ☁️ Cloud → Online AI"
    echo "   💾 4B    → Standby / isolated"
    exit 0
else
    echo "❌ MESIN AI v0.8 — TEST GAGAL"
    exit 1
fi
