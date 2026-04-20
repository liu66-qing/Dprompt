#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "用法: bash scripts/run_experiment.sh 实验名 \"启动命令\""
  echo "示例: bash scripts/run_experiment.sh 20260420_M3 \"python train.py --data_cfg configs/paths.local.yaml --epochs 50 --batch_size 4\""
  exit 1
fi

EXP_NAME="$1"
shift
CMD="$*"

STAMP=$(date '+%Y%m%d_%H%M%S')
HUMAN_TIME=$(date '+%Y-%m-%d %H:%M:%S')

LOG_DIR="logs"
CKPT_DIR="checkpoints/${STAMP}_${EXP_NAME}"
RES_DIR="results/${STAMP}_${EXP_NAME}"
LOG_FILE="${LOG_DIR}/${STAMP}_${EXP_NAME}.log"
PID_FILE="${LOG_DIR}/${STAMP}_${EXP_NAME}.pid"

mkdir -p "$LOG_DIR" "$CKPT_DIR" "$RES_DIR" docs

echo "时间: $HUMAN_TIME"
echo "实验名称: $EXP_NAME"
echo "启动命令: $CMD"
echo "日志文件: $LOG_FILE"
echo "Checkpoint目录: $CKPT_DIR"
echo "结果目录: $RES_DIR"

cat >> docs/实验启动记录.md <<EOF

### [$HUMAN_TIME]
- 实验名称：$EXP_NAME
- 实验阶段：待补充
- 实验目的：待补充
- 使用数据配置：
  - \`configs/paths.local.yaml\`
- 启动命令：
  \`\`\`bash
  $CMD
  \`\`\`
- 日志文件：
  - \`$LOG_FILE\`
- checkpoint 路径：
  - \`$CKPT_DIR\`
- 结果输出路径：
  - \`$RES_DIR\`
- 关键参数：
  - 待补充
- 备注：
  - 使用统一启动脚本创建
  - 日志应精简，不打印大张量
EOF

nohup bash -lc "$CMD" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "已启动，PID=$(cat "$PID_FILE")"
echo "请确认命令中已包含：--data_cfg configs/paths.local.yaml"
echo "请确认训练脚本已设置：精简日志、保存 best/last checkpoint、保存结果路径"