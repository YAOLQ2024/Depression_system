#!/usr/bin/env bash
set -uo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

zenity --question --title='清理 MinIO 数据' --width=480 \
  --text='确定删除 mcs-multimodal 桶中的全部对象吗？\n\n音频、脑电等文件将被删除，无法恢复；数据库记录会保留，可能无法再访问对应文件。' \
  --ok-label='删除全部对象' --cancel-label='取消' || exit 0

exec 9>"${XDG_RUNTIME_DIR:-/tmp}/mcs-clean-minio-$(id -u).lock"
if ! flock -n 9; then
  zenity --info --title='清理 MinIO 数据' --text='清理正在进行，请稍候。'
  exit 0
fi
output="$("$root/一键清理MinIO数据.sh" 2>&1)"
status=$?
if [[ $status -eq 0 ]]; then
  zenity --info --title='清理 MinIO 数据' --width=480 --text="$output"
else
  zenity --error --title='MinIO 清理失败' --width=520 --text="$output"
  exit "$status"
fi
