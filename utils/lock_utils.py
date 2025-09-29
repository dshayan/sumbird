#!/usr/bin/env python3
"""
Lock utilities for Sumbird.

This module provides process locking functionality to prevent concurrent pipeline executions:
- File-based locking mechanism
- Automatic lock cleanup on exit
- Lock timeout handling
- Process ID tracking
"""
import os
import sys
import time
import atexit
from utils.logging_utils import log_info, log_error, log_warning
from utils.date_utils import format_datetime

# Global lock file path
LOCK_FILE_PATH = 'logs/sumbird.lock'

class PipelineLock:
    """Context manager for pipeline locking to prevent concurrent executions."""
    
    def __init__(self, timeout_minutes=120):
        """
        Initialize the pipeline lock.
        
        Args:
            timeout_minutes (int): Maximum time to wait for lock (default: 120 minutes)
        """
        self.lock_file_path = LOCK_FILE_PATH
        self.timeout_seconds = timeout_minutes * 60
        self.lock_acquired = False
        self.pid = os.getpid()
        
    def __enter__(self):
        """Acquire the lock."""
        if not self._acquire_lock():
            raise RuntimeError("Could not acquire pipeline lock - another instance may be running")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        self._release_lock()
        
    def _acquire_lock(self):
        """
        Acquire the pipeline lock.
        
        Returns:
            bool: True if lock acquired successfully, False otherwise
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout_seconds:
            try:
                # Try to create lock file exclusively
                with open(self.lock_file_path, 'x') as lock_file:
                    lock_file.write(f"{self.pid}\n")
                    lock_file.write(f"{format_datetime()}\n")
                    lock_file.write("Sumbird Pipeline Lock\n")
                
                self.lock_acquired = True
                log_info('PipelineLock', f"Pipeline lock acquired (PID: {self.pid})")
                
                # Register cleanup function
                atexit.register(self._cleanup_on_exit)
                return True
                
            except FileExistsError:
                # Lock file exists, check if it's stale
                if self._is_lock_stale():
                    log_warning('PipelineLock', "Found stale lock file, attempting to remove it")
                    try:
                        os.remove(self.lock_file_path)
                        continue  # Try to acquire lock again
                    except OSError:
                        pass  # Continue waiting
                
                # Wait before retrying
                time.sleep(10)
                continue
                
            except Exception as e:
                log_error('PipelineLock', f"Error acquiring lock: {e}")
                return False
        
        # Timeout reached
        log_error('PipelineLock', f"Timeout waiting for lock after {self.timeout_seconds} seconds")
        return False
    
    def _is_lock_stale(self):
        """
        Check if the existing lock file is stale (from a dead process).
        
        Returns:
            bool: True if lock is stale, False otherwise
        """
        try:
            with open(self.lock_file_path, 'r') as lock_file:
                pid_line = lock_file.readline().strip()
                if not pid_line.isdigit():
                    return True  # Invalid PID format
                
                lock_pid = int(pid_line)
                
                # Check if process is still running
                try:
                    os.kill(lock_pid, 0)  # Signal 0 just checks if process exists
                    return False  # Process is still running
                except (OSError, ProcessLookupError):
                    return True  # Process is dead
                    
        except (FileNotFoundError, ValueError, OSError):
            return True  # Lock file is invalid or doesn't exist
    
    def _release_lock(self):
        """Release the pipeline lock."""
        if self.lock_acquired:
            try:
                if os.path.exists(self.lock_file_path):
                    os.remove(self.lock_file_path)
                log_info('PipelineLock', f"Pipeline lock released (PID: {self.pid})")
            except OSError as e:
                log_error('PipelineLock', f"Error releasing lock: {e}")
            finally:
                self.lock_acquired = False
    
    def _cleanup_on_exit(self):
        """Cleanup function called on process exit."""
        if self.lock_acquired:
            self._release_lock()

def check_lock_status():
    """
    Check the current status of the pipeline lock.
    
    Returns:
        dict: Lock status information
    """
    if not os.path.exists(LOCK_FILE_PATH):
        return {
            'locked': False,
            'message': 'No lock file found'
        }
    
    try:
        with open(LOCK_FILE_PATH, 'r') as lock_file:
            lines = lock_file.readlines()
            if len(lines) >= 2:
                pid = lines[0].strip()
                timestamp = lines[1].strip()
                
                # Check if process is still running
                try:
                    if pid.isdigit():
                        os.kill(int(pid), 0)
                        return {
                            'locked': True,
                            'pid': pid,
                            'timestamp': timestamp,
                            'message': f'Pipeline locked by PID {pid} since {timestamp}'
                        }
                except (OSError, ProcessLookupError):
                    return {
                        'locked': False,
                        'pid': pid,
                        'timestamp': timestamp,
                        'message': f'Stale lock from PID {pid} at {timestamp}'
                    }
    except (OSError, ValueError):
        pass
    
    return {
        'locked': False,
        'message': 'Invalid lock file'
    }

def force_release_lock():
    """
    Force release the pipeline lock (use with caution).
    
    Returns:
        bool: True if lock was released, False otherwise
    """
    try:
        if os.path.exists(LOCK_FILE_PATH):
            os.remove(LOCK_FILE_PATH)
            log_info('PipelineLock', "Pipeline lock force-released")
            return True
    except OSError as e:
        log_error('PipelineLock', f"Error force-releasing lock: {e}")
        return False
    
    return False
