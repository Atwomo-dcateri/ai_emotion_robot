#!/bin/bash

# 默认参数
COMMIT_MESSAGE=""
INTERVAL_MINUTES=0
MAX_COMMITS=0
LOG_FILE="git-auto-commit.log"
HELP=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -CommitMessage|--commit-message)
            COMMIT_MESSAGE="$2"
            shift 2
            ;;
        -IntervalMinutes|--interval)
            INTERVAL_MINUTES="$2"
            shift 2
            ;;
        -MaxCommits|--max-commits)
            MAX_COMMITS="$2"
            shift 2
            ;;
        -LogFile|--log-file)
            LOG_FILE="$2"
            shift 2
            ;;
        -Help|--help)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# 日志函数
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message"
    echo "[$timestamp] $message" >> "$LOG_FILE"
}

# 检查是否是 git 仓库
test_git_status() {
    if ! git status --porcelain &>/dev/null; then
        log_message "ERROR: Not a git repository or git command failed"
        return 1
    fi
    return 0
}

# 获取当前分支
get_git_branch() {
    git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown"
}

# 执行 git commit 和 push
invoke_git_commit() {
    local message="$1"
    
    if ! test_git_status; then
        return 1
    fi
    
    local branch=$(get_git_branch)
    log_message "Current branch: $branch"
    
    # 检查是否有更改
    if [[ -z "$(git status --porcelain)" ]]; then
        log_message "No changes to commit"
        return 0
    fi
    
    log_message "Adding all changes..."
    git add . 2>&1 | tee -a "$LOG_FILE" > /dev/null
    
    if [[ $? -ne 0 ]]; then
        log_message "ERROR: Failed to add changes"
        return 1
    fi
    
    if [[ -z "$message" ]]; then
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        message="Auto commit at $timestamp"
    fi
    
    log_message "Committing with message: $message"
    git commit -m "$message" 2>&1 | tee -a "$LOG_FILE" > /dev/null
    
    if [[ $? -ne 0 ]]; then
        log_message "ERROR: Failed to commit changes"
        return 1
    fi
    
    log_message "Pushing to remote..."
    git push origin "$branch" 2>&1 | tee -a "$LOG_FILE" > /dev/null
    
    if [[ $? -ne 0 ]]; then
        log_message "ERROR: Failed to push to remote"
        return 1
    fi
    
    log_message "SUCCESS: Changes committed and pushed successfully"
    return 0
}

# 显示帮助
show_help() {
    cat << 'EOF'
Git Auto Commit and Push Script
================================

Usage: ./git-auto-commit.sh [options]

Options:
    --commit-message <string>   Custom commit message (default: auto-generated timestamp)
    --interval <int>            Run every N minutes (0 = run once, default: 0)
    --max-commits <int>         Maximum number of commits (0 = unlimited, default: 0)
    --log-file <path>           Log file path (default: git-auto-commit.log)
    --help                      Show this help message

Examples:
    # Single commit with auto-generated message
    ./git-auto-commit.sh

    # Single commit with custom message
    ./git-auto-commit.sh --commit-message "Update documentation"

    # Run every 30 minutes with unlimited commits
    ./git-auto-commit.sh --interval 30

    # Run every 15 minutes, max 10 commits
    ./git-auto-commit.sh --interval 15 --max-commits 10

    # Custom log file location
    ./git-auto-commit.sh --log-file "/var/log/git-commits.log"

Note:
    - This script will add all changes (git add .)
    - Make sure you have push permissions to the remote repository
    - Press Ctrl+C to stop the script when running in interval mode
EOF
}

# 主程序
if [[ "$HELP" == true ]]; then
    show_help
    exit 0
fi

log_message "========================================"
log_message "Git Auto Commit Script Started"
log_message "========================================"

if [[ $INTERVAL_MINUTES -gt 0 ]]; then
    log_message "Running in interval mode: every $INTERVAL_MINUTES minutes"
    if [[ $MAX_COMMITS -gt 0 ]]; then
        log_message "Maximum commits: $MAX_COMMITS"
    else
        log_message "Maximum commits: unlimited"
    fi
    
    commit_count=0
    while true; do
        ((commit_count++))
        log_message "--- Commit #$commit_count ---"
        
        invoke_git_commit "$COMMIT_MESSAGE"
        
        if [[ $MAX_COMMITS -gt 0 ]] && [[ $commit_count -ge $MAX_COMMITS ]]; then
            log_message "Reached maximum commits limit ($MAX_COMMITS)"
            break
        fi
        
        log_message "Waiting $INTERVAL_MINUTES minutes until next commit..."
        sleep $((INTERVAL_MINUTES * 60))
    done
else
    log_message "Running in single commit mode"
    invoke_git_commit "$COMMIT_MESSAGE" > /dev/null
fi

log_message "========================================"
log_message "Git Auto Commit Script Finished"
log_message "========================================"