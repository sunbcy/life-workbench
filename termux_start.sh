#!/bin/bash
# 生活工作台 - 一键启动脚本
# 同时启动 FastAPI 后端 (8000) 和 Vite 前端 (5173)
#
# 也可分别启动单个服务：
#   bash start_backend.sh    # 仅后端
#   bash start_frontend.sh   # 仅前端

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173

# ============================================
# 工具函数
# ============================================

port_in_use() {
    local p=$1
    curl -s -o /dev/null --connect-timeout 1 --max-time 2 "http://127.0.0.1:$p" 2>/dev/null && return 0
    return 1
}

kill_by_pattern() {
    local pattern=$1
    local label=$2
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            if [ -n "$pid" ] && [ "$pid" -gt 1 ] 2>/dev/null && [ "$pid" != "$$" ]; then
                local cmdline
                cmdline=$(cat "/proc/$pid/cmdline" 2>/dev/null | tr '\0' ' ' | cut -c1-60 || echo "unknown")
                echo "  ⚠ $label 残留进程 PID=$pid → 终止"
                kill -TERM "$pid" 2>/dev/null || true
                sleep 0.5
                kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true
            fi
        done
    fi
}

wait_for_port() {
    local p=$1 timeout=$2 elapsed=0
    while [ $elapsed -lt $timeout ]; do
        port_in_use "$p" && return 0
        sleep 0.5
        elapsed=$((elapsed + 1))
    done
    return 1
}

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   🏠  生活工作台  Life Workbench        ║"
echo "  ║   FastAPI + Vue3 + Vite + Tailwind      ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ============================================
# 1. 清理旧进程
# ============================================
echo "[1/4] 清理旧进程..."
port_in_use $BACKEND_PORT && kill_by_pattern "python.*main.py" "后端"
port_in_use $FRONTEND_PORT && kill_by_pattern "node.*vite" "前端"
sleep 1
if port_in_use $BACKEND_PORT || port_in_use $FRONTEND_PORT; then
    echo "  ❌ 端口释放失败，请手动处理"
    exit 1
fi
echo "  ✓ 端口已就绪"
echo ""

# ============================================
# 2-3. 依赖检查
# ============================================
echo "[2/4] 检查后端依赖..."
cd "$BACKEND_DIR"
python -c "import fastapi" 2>/dev/null && echo "  ✓ Python 依赖已就绪" || { pip install -r requirements.txt -q && echo "  ✓ 安装完成"; }

echo "[3/4] 检查前端依赖..."
cd "$FRONTEND_DIR"
[ -d "node_modules" ] && echo "  ✓ 前端依赖已就绪" || { yarn install --silent && echo "  ✓ 安装完成"; }

# ============================================
# 4. 启动服务
# ============================================
echo "[4/4] 启动服务..."
echo ""

cleanup() {
    echo ""
    echo "  ⏳ 正在停止..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    wait $FRONTEND_PID 2>/dev/null || true
    echo "  👋 已停止"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

cd "$BACKEND_DIR" && python main.py &
BACKEND_PID=$!
echo -n "  🐍 后端 :8000 "
wait_for_port $BACKEND_PORT 20 && echo "✓" || { echo "❌ 超时"; exit 1; }

cd "$FRONTEND_DIR" && node ./node_modules/vite/bin/vite.js --host &
FRONTEND_PID=$!
echo -n "  🎨 前端 :5173 "
wait_for_port $FRONTEND_PORT 15 && echo "✓" || { echo "❌ 超时"; exit 1; }

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║  ✅  服务已启动                         ║"
echo "  ║  📱 http://localhost:$FRONTEND_PORT  · 前端      ║"
echo "  ║  🔌 http://localhost:$BACKEND_PORT  · 后端      ║"
echo "  ║  📖 http://localhost:$BACKEND_PORT/docs · 文档  ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

wait
