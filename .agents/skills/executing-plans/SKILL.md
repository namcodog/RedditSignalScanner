---
name: executing-plans
description: "用于已有实现计划后的按步骤执行，尤其是 writing-plans 完成后继续推进工程任务。"
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns
3. If concerns: Raise them before starting
4. If no concerns: Proceed

### Step 2: Execute Tasks
For each task:
1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed

### Step 3: Complete Development
After all tasks complete and verified:
- Run the full test suite
- Verify all requirements met
- Commit final changes

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## 触发场景（中文说明）

以下场景应自动调用本 skill：
- writing-plans 完成后，用户确认"开始执行"
- 用户说"按计划做"/"开始实现"
- 有明确的任务清单需要逐步执行
