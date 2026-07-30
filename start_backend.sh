#!/bin/bash
# 生活工作台 - 后端独立启动脚本
# FastAPI 后端 (端口 8000)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PORT=8000

# ============================================
# 工具函数
# ============================================

port_in_use() {
    local p=$1
    if command -v curl &>/dev/null; then
        curl -s -o /dev/null --connect-timeout 1 --max-time 2 "http://127.0.0.1:$p" 2>/dev/null
        return $?
    fi
    (echo >"/dev/tcp/127.0.0.1/$p") 2>/dev/null && return 0
    return 1
}

kill_by_pattern() {
    local pattern=$1
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            if [ -n "$pid" ] && [ "$pid" -gt 1 ] 2>/dev/null && [ "$pid" != "$$" ]; then
                local cmdline
                cmdline=$(cat "/proc/$pid/cmdline" 2>/dev/null | tr '\0' ' ' | cut -c1-60 || echo "unknown")
                echo "  ⚠ 发现残留进程 (PID: $pid)"
                echo "     $cmdline"
                kill -TERM "$pid" 2>/dev/null || true
                sleep 0.5
                if kill -0 "$pid" 2>/dev/null; then
                    echo "     → 强制终止..."
                    kill -KILL "$pid" 2>/dev/null || true
                    sleep 0.3
                fi
                echo "     ✓ 已终止"
            fi
        done
    fi
}

wait_for_port() {
    local p=$1
    local timeout=$2
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if port_in_use "$p"; then
            return 0
        fi
        sleep 0.5
        elapsed=$((elapsed + 1))
    done
    return 1
}

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   🐍  启动后端服务                   ║"
echo "  ║   FastAPI · 端口 $PORT               ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ============================================
# 1. 清理端口占用
# ============================================
if port_in_use $PORT; then
    echo "[1/3] 端口 $PORT 被占用，清理旧进程..."
    kill_by_pattern "python.*main.py"
    sleep 1

    # 二次确认
    if port_in_use $PORT; then
        echo "  ⚠ 尝试宽泛清理..."
        # 列出占用端口的可疑 python 进程
        local pids
        pids=$(pgrep -f "python" 2>/dev/null || true)
        for pid in $pids; do
            if [ "$pid" != "$$" ] && [ "$pid" -gt 1 ] 2>/dev/null; then
                local cmdline
                cmdline=$(cat "/proc/$pid/cmdline" 2>/dev/null | tr '\0' ' ' || "")
                if echo "$cmdline" | grep -qE "(uvicorn|fastapi|main\.py)"; then
                    echo "  ⚠ 终止残留: PID=$pid"
                    kill -KILL "$pid" 2>/dev/null || true
                fi
            fi
        done
        sleep 1
    fi

    if port_in_use $PORT; then
        echo "  ❌ 端口 $PORT 释放失败，请手动处理"
        echo "     提示: pgrep -f 'python.*main.py' | xargs kill -9"
        exit 1
    fi
    echo "  ✓ 端口已释放"
else
    # 端口空闲也清理一下残留
    kill_by_pattern "python.*main.py"
    echo "[1/3] ✓ 端口 $PORT 空闲"
fi

# ============================================
# 2. 检查依赖
# ============================================
echo "[2/3] 检查依赖..."
cd "$BACKEND_DIR"

if ! python -c "import fastapi" 2>/dev/null; then
    echo "  📦 安装 Python 依赖..."
    pip install -r requirements.txt -q
    echo "  ✓ 安装完成"
else
    echo "  ✓ Python 依赖已就绪"
fi

# ============================================
# 3. 启动服务
# ============================================
echo "[3/3] 启动服务..."
echo ""

cleanup() {
    echo ""
    echo "  ⏳ 正在停止后端..."
    kill $BACKEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    echo "  👋 后端已停止"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

python main.py &
BACKEND_PID=$!

echo -n "  ⏳ 等待服务就绪"
if wait_for_port $PORT 20; then
    echo ""
    echo ""
    echo "  ╔══════════════════════════════════════╗"
    echo "  ║  ✅  后端已启动！                   ║"
    echo "  ║                                    ║"
    echo "  ║  🔌 后端:  http://localhost:$PORT       ║"
    echo "  ║  📖 文档:  http://localhost:$PORT/docs   ║"
    echo "  ║                                    ║"
    echo "  ║  按 Ctrl+C 停止                     ║"
    echo "  ╚══════════════════════════════════════╝"
    echo ""
else
    echo ""
    echo "  ❌ 后端启动超时 (20s)"
    echo "     请手动运行: cd $BACKEND_DIR && python main.py"
    exit 1
fi

wait
