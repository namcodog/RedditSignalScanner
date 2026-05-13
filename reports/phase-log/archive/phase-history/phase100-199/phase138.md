# Phase 138 - Week2 全量验收尝试（被删除保护阻塞）

日期：2026-01-21

## 目标
执行全量验收中的 Week2（P1）验收流程。

## 执行记录
1) 运行命令（第一次）：
LOCAL_ACCEPT_ENV=local LOCAL_ACCEPT_BACKEND=http://localhost:8006 \
LOCAL_ACCEPT_FRONTEND=http://localhost:3006 LOCAL_ACCEPT_REDIS=redis://localhost:6379/0 \
LOCAL_ACCEPT_EMAIL=test@example.com LOCAL_ACCEPT_PASSWORD=*** \
MAKE="make -f Makefile -f makefiles/acceptance.mk" \
make -f Makefile -f makefiles/acceptance.mk week2-acceptance

结果：脚本使用 python3（3.13）执行，缺少 sqlalchemy 依赖，直接报错中断。

2) 运行命令（第二次，指定 PYTHON_BIN 为 .venv）：
PYTHON_BIN=.venv/bin/python ... make -f Makefile -f makefiles/acceptance.mk week2-acceptance

结果：脚本进入 backend 目录后找不到相对路径 .venv/bin/python，继续报错中断。

3) 运行命令（第三次，指定 PYTHON_BIN 为相对 backend 的路径）：
PYTHON_BIN=../.venv/bin/python ... make -f Makefile -f makefiles/acceptance.mk week2-acceptance

结果：清理数据库阶段失败，数据库触发器阻止 DELETE：
delete blocked: app.allow_delete not set

## 结论
Week2 验收未能完成，阻塞点是数据库删除保护开关未开启。
当前未发生任务/分析数据删除（被保护机制拦截）。

## 阻塞与处理建议
- 阻塞：week2_prepare.sh 清理 Task/Analysis 需要允许 delete。
- 处理方案（待确认）：
  1) 在运行脚本时临时设置连接参数：PGOPTIONS='-c app.allow_delete=1'
  2) 或在脚本内加入 `SET LOCAL app.allow_delete = '1'`（需改脚本）

## 下一步
等待确认是否允许开启删除开关后，继续跑 week2-acceptance。
