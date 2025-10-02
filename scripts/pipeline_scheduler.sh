#!/bin/bash

# Sumbird Scheduler Script
# This script sets up or removes automatic scheduling for the sumbird pipeline

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
MAIN_SCRIPT="$SCRIPT_DIR/main.py"
LOG_FILE="$SCRIPT_DIR/logs/cron.log"
# Include proper PATH for cron environment to find FFmpeg and other tools
# First cron entry: 1:00 AM without Telegram distribution (ULTRA-SIMPLIFIED)
CRON_ENTRY_1AM="0 1 * * * cd $SCRIPT_DIR && echo 'Cron: Starting 1:00 AM pipeline (without Telegram)' >> $LOG_FILE && $PYTHON_PATH main.py --skip-telegram >> $LOG_FILE 2>&1"
# Second cron entry: 6:00 AM with full Telegram distribution (ULTRA-SIMPLIFIED)
CRON_ENTRY_6AM="0 6 * * * cd $SCRIPT_DIR && echo 'Cron: Starting 6:00 AM pipeline (with Telegram)' >> $LOG_FILE && $PYTHON_PATH main.py >> $LOG_FILE 2>&1"
# Schedule refresh entry: Run this script weekly to refresh wake schedules (since pmset repeat can only set one time)
CRON_REFRESH="0 0 * * 0 cd $SCRIPT_DIR && $SCRIPT_DIR/scripts/pipeline_scheduler.sh refresh-wake >> $LOG_FILE 2>&1"

# Function to print output with consistent formatting
print_info() {
    echo "[INFO] $1"
}

print_warning() {
    echo "[WARNING] $1" >&2
}

print_error() {
    echo "[ERROR] $1" >&2
}

# Function to check if script exists
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if [ ! -f "$PYTHON_PATH" ]; then
        print_error "Python virtual environment not found at: $PYTHON_PATH"
        exit 1
    fi
    
    if [ ! -f "$MAIN_SCRIPT" ]; then
        print_error "Main script not found at: $MAIN_SCRIPT"
        exit 1
    fi
    
    if [ ! -d "$SCRIPT_DIR/logs" ]; then
        print_info "Creating logs directory..."
        mkdir -p "$SCRIPT_DIR/logs"
    fi
    
    print_info "Prerequisites check passed!"
}

# Function to schedule wake events for the next 30 days
schedule_wake_events() {
    print_info "Scheduling wake events for the next 30 days..."
    
    # Set repeating schedule for 5:59 AM (for 6:00 AM job)
    if sudo pmset repeat wake MTWRFSU 05:59:00; then
        print_info "Repeating wake schedule set for 5:59 AM (for 6:00 AM job)"
    else
        print_error "Failed to set repeating wake schedule"
        return 1
    fi
    
    # Schedule specific wake events for 12:59 AM for the next 30 days
    for i in {0..29}; do
        # Calculate date for i days from now
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS date command
            wake_date=$(date -j -v+${i}d "+%m/%d/%y 00:59:00")
        else
            # Linux date command (fallback)
            wake_date=$(date -d "+${i} days" "+%m/%d/%y 00:59:00")
        fi
        
        # Schedule wake event for this specific date
        if sudo pmset schedule wake "$wake_date"; then
            if [ $i -eq 0 ]; then
                print_info "Scheduled specific wake events for 12:59 AM (first few days: $wake_date...)"
            fi
        else
            print_warning "Failed to schedule wake event for $wake_date"
        fi
    done
    
    print_info "Wake events scheduled successfully!"
}

# Function to refresh wake schedules (called weekly by cron)
refresh_wake_schedules() {
    print_info "Refreshing wake schedules..."
    
    # Clear existing specific schedules (but keep repeating ones)
    sudo pmset schedule cancelall 2>/dev/null
    
    # Re-schedule wake events
    schedule_wake_events
    
    print_info "Wake schedules refreshed!"
}

# Function to set up scheduling
setup_scheduling() {
    print_info "Setting up Sumbird Scheduling"
    
    check_prerequisites
    
    # Set up wake schedules
    print_info "Setting up wake schedules..."
    schedule_wake_events
    
    # Set up cron jobs (including refresh job)
    print_info "Setting up cron jobs..."
    # Create a temporary crontab with all entries
    TEMP_CRONTAB=$(mktemp)
    {
        echo "$CRON_ENTRY_1AM"
        echo "$CRON_ENTRY_6AM"
        echo "$CRON_REFRESH"
    } > "$TEMP_CRONTAB"
    
    if crontab "$TEMP_CRONTAB"; then
        print_info "Cron jobs set successfully!"
        rm "$TEMP_CRONTAB"
    else
        print_error "Failed to set cron jobs."
        rm "$TEMP_CRONTAB"
        exit 1
    fi
    
    # Verify setup
    print_info "Verifying setup..."
    echo
    print_info "Wake Schedules"
    pmset -g sched
    echo
    print_info "Cron Jobs"
    crontab -l
    echo
    
    print_info "Scheduling setup complete!"
    print_info "Your sumbird script will run:"
    print_info "  - Daily at 1:00 AM (without Telegram distribution)"
    print_info "  - Daily at 6:00 AM (with full Telegram distribution)"
    print_info "  - Weekly refresh of wake schedules (Sunday midnight)"
    print_info "Logs will be saved to: $LOG_FILE"
    print_info ""
    print_info "Note: Due to macOS pmset limitations, wake schedules are refreshed weekly."
}

# Function to remove scheduling
remove_scheduling() {
    print_info "Removing Sumbird Scheduling"
    
    # Remove wake schedules
    print_info "Removing wake schedules..."
    if sudo pmset repeat cancel; then
        print_info "Repeating wake schedules removed!"
    else
        print_warning "Failed to remove repeating wake schedules or none were set."
    fi
    
    if sudo pmset schedule cancelall; then
        print_info "Specific wake schedules removed!"
    else
        print_warning "Failed to remove specific wake schedules or none were set."
    fi
    
    # Remove cron jobs
    print_info "Removing cron jobs..."
    if crontab -l 2>/dev/null | grep -v "sumbird\|main.py\|pipeline_scheduler.sh" | crontab -; then
        print_info "Cron jobs removed!"
    else
        # If no crontab exists or grep removes all entries
        if crontab -r 2>/dev/null; then
            print_info "All cron jobs removed!"
        else
            print_warning "No cron jobs found to remove."
        fi
    fi
    
    # Verify removal
    print_info "Verifying removal..."
    echo
    print_info "Remaining Wake Schedules"
    pmset -g sched
    echo
    print_info "Remaining Cron Jobs"
    if crontab -l 2>/dev/null; then
        echo "Found remaining cron jobs (not related to sumbird)"
    else
        echo "No cron jobs found"
    fi
    echo
    
    print_info "Scheduling removal complete!"
}

# Function to show current status
show_status() {
    print_info "Current Sumbird Scheduling Status"
    
    echo
    print_info "Wake Schedules"
    
    # Check for repeating wake at 5:59 AM
    if pmset -g sched | grep -q "wake at 5:59AM"; then
        print_info "Repeating wake at 5:59 AM is SET (for 6:00 AM job)"
    else
        print_warning "No repeating wake schedule found for 5:59 AM"
    fi
    
    # Check for specific wake events at 12:59 AM
    if pmset -g sched | grep -q "wake at.*00:59:00"; then
        print_info "Specific wake events at 12:59 AM are SET (for 1:00 AM job)"
        # Count how many are scheduled
        count=$(pmset -g sched | grep -c "wake at.*00:59:00")
        print_info "    ($count specific wake events scheduled)"
    else
        print_warning "No specific wake events found for 12:59 AM"
    fi
    
    # Show all wake schedules
    echo
    print_info "All Wake Schedules"
    pmset -g sched
    
    echo
    print_info "Cron Jobs"
    if crontab -l 2>/dev/null | grep -q "0 1.*main.py --skip-telegram"; then
        print_info "1:00 AM cron job (without Telegram) is SET"
    else
        print_warning "No 1:00 AM cron job found"
    fi
    
    if crontab -l 2>/dev/null | grep -q "0 6.*main.py[^-]"; then
        print_info "6:00 AM cron job (with Telegram) is SET"
    else
        print_warning "No 6:00 AM cron job found"
    fi
    
    if crontab -l 2>/dev/null | grep -q "pipeline_scheduler.sh refresh-wake"; then
        print_info "Weekly refresh cron job is SET"
    else
        print_warning "No weekly refresh cron job found"
    fi
    
    # Show all sumbird-related cron jobs
    echo
    print_info "All Sumbird Cron Jobs"
    if crontab -l 2>/dev/null | grep -q "sumbird\|main.py\|pipeline_scheduler.sh"; then
        crontab -l | grep -E "sumbird|main.py|pipeline_scheduler.sh"
    else
        echo "No sumbird-related cron jobs found"
    fi
    
    echo
    print_info "File Status"
    if [ -f "$PYTHON_PATH" ]; then
        print_info "Python virtual environment found"
    else
        print_error "Python virtual environment missing"
    fi
    
    if [ -f "$MAIN_SCRIPT" ]; then
        print_info "Main script found"
    else
        print_error "Main script missing"
    fi
    
    if [ -d "$SCRIPT_DIR/logs" ]; then
        print_info "Logs directory exists"
    else
        print_warning "Logs directory missing"
    fi
}

# Function to test run
test_run() {
    print_info "Testing Sumbird Script"
    
    check_prerequisites
    
    echo "Choose which test to run:"
    echo "1. Test 1:00 AM version (without Telegram distribution)"
    echo "2. Test 6:00 AM version (with full Telegram distribution)"
    echo "3. Cancel"
    echo
    read -p "Enter your choice (1-3): " choice
    
    case "$choice" in
        1)
            print_info "Running: caffeinate -s $PYTHON_PATH main.py --skip-telegram"
            print_info "This will run the 1:00 AM version (without Telegram distribution)..."
            echo
            cd "$SCRIPT_DIR" && caffeinate -s "$PYTHON_PATH" main.py --skip-telegram
            ;;
        2)
            print_warning "WARNING: This will send messages to your Telegram channel!"
            read -p "Are you sure you want to continue? (y/N): " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                print_info "Running: caffeinate -s $PYTHON_PATH main.py"
                print_info "This will run the 6:00 AM version (with full Telegram distribution)..."
                echo
                cd "$SCRIPT_DIR" && caffeinate -s "$PYTHON_PATH" main.py
            else
                print_info "Test cancelled."
                return 0
            fi
            ;;
        3)
            print_info "Test cancelled."
            return 0
            ;;
        *)
            print_error "Invalid choice. Test cancelled."
            return 1
            ;;
    esac
    
    echo
    if [ $? -eq 0 ]; then
        print_info "Test run completed successfully!"
    else
        print_error "Test run failed. Check the output above for errors."
    fi
}

# Function to show usage
show_usage() {
    echo "Sumbird Scheduler Script"
    echo
    echo "Usage: $0 [OPTION]"
    echo
    echo "Options:"
    echo "  setup         Set up automatic scheduling (wake + cron)"
    echo "  remove        Remove all scheduling"
    echo "  status        Show current scheduling status"
    echo "  test          Test run the script once"
    echo "  refresh-wake  Refresh wake schedules (used internally by cron)"
    echo "  help          Show this help message"
    echo
    echo "Scheduling Details:"
    echo "  1:00 AM       Run pipeline without Telegram distribution"
    echo "  6:00 AM       Run pipeline with full Telegram distribution"
    echo "  Weekly        Refresh wake schedules (due to macOS pmset limitations)"
    echo
    echo "Examples:"
    echo "  $0 setup      # Set up dual scheduling (1:00 AM + 6:00 AM)"
    echo "  $0 remove     # Remove all scheduling"
    echo "  $0 status     # Check current status"
    echo "  $0 test       # Test run the script (choose version)"
    echo
    echo "Note: Due to macOS pmset limitations, wake schedules are refreshed weekly."
}

# Main script logic
case "$1" in
    "setup")
        setup_scheduling
        ;;
    "remove")
        remove_scheduling
        ;;
    "status")
        show_status
        ;;
    "test")
        test_run
        ;;
    "refresh-wake")
        refresh_wake_schedules
        ;;
    "help"|"--help"|"-h")
        show_usage
        ;;
    "")
        print_error "No option provided."
        echo
        show_usage
        exit 1
        ;;
    *)
        print_error "Unknown option: $1"
        echo
        show_usage
        exit 1
        ;;
esac 