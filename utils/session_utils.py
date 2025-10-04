#!/usr/bin/env python3
"""
Session management utilities for Sumbird.
Simplified session management with mode-based configuration.
"""
import random
from typing import Dict, Any


class SessionManager:
    """Simplified session management with mode-based configuration."""
    
    MODES = {
        'conservative': {
            'base_delay_min': 8.0,
            'base_delay_max': 12.0,
            'batch_delay_jitter': 15.0,
            'session_recovery_delay': 90.0,
            'session_backoff_delay': 180.0,
            'error_threshold': 2,
            'adaptive_factor': 2.0,
            'max_adaptive_delay': 120.0
        },
        'balanced': {
            'base_delay_min': 5.0,
            'base_delay_max': 8.0,
            'batch_delay_jitter': 10.0,
            'session_recovery_delay': 60.0,
            'session_backoff_delay': 120.0,
            'error_threshold': 3,
            'adaptive_factor': 1.5,
            'max_adaptive_delay': 60.0
        },
        'aggressive': {
            'base_delay_min': 3.0,
            'base_delay_max': 5.0,
            'batch_delay_jitter': 5.0,
            'session_recovery_delay': 30.0,
            'session_backoff_delay': 60.0,
            'error_threshold': 5,
            'adaptive_factor': 1.2,
            'max_adaptive_delay': 30.0
        }
    }
    
    def __init__(self, mode: str = 'conservative', base_delay: float = 5.0, batch_delay: float = 30.0):
        """Initialize session manager with mode-based configuration.
        
        Args:
            mode (str): Session mode ('conservative', 'balanced', 'aggressive')
            base_delay (float): Base delay between requests
            batch_delay (float): Base delay between batches
        """
        self.mode = mode.lower()
        self.base_delay = base_delay
        self.batch_delay = batch_delay
        
        if self.mode not in self.MODES:
            from utils.logging_utils import log_warning
            log_warning('SessionManager', f"Unknown session mode '{mode}', using 'conservative'")
            self.mode = 'conservative'
        
        self.settings = self.MODES[self.mode]
    
    def get_base_delay(self) -> float:
        """Get base delay with jitter.
        
        Returns:
            float: Base delay in seconds
        """
        return random.uniform(self.settings['base_delay_min'], self.settings['base_delay_max'])
    
    def get_batch_delay(self) -> float:
        """Get batch delay with jitter.
        
        Returns:
            float: Batch delay in seconds
        """
        return self.batch_delay + random.uniform(0, self.settings['batch_delay_jitter'])
    
    def get_session_recovery_delay(self) -> float:
        """Get session recovery delay.
        
        Returns:
            float: Session recovery delay in seconds
        """
        return self.settings['session_recovery_delay']
    
    def get_session_backoff_delay(self) -> float:
        """Get session backoff delay.
        
        Returns:
            float: Session backoff delay in seconds
        """
        return self.settings['session_backoff_delay']
    
    def get_error_threshold(self) -> int:
        """Get 429 error threshold.
        
        Returns:
            int: Number of errors before session exhaustion detection
        """
        return self.settings['error_threshold']
    
    def get_adaptive_delay(self, consecutive_failures: int) -> float:
        """Get adaptive delay based on failures.
        
        Args:
            consecutive_failures (int): Number of consecutive failures
            
        Returns:
            float: Adaptive delay in seconds
        """
        base = self.get_base_delay()
        adaptive = base * (self.settings['adaptive_factor'] ** consecutive_failures)
        return min(adaptive, self.settings['max_adaptive_delay'])
    
    def should_apply_session_recovery(self, consecutive_429_errors: int, last_429_time: float) -> bool:
        """Check if session recovery should be applied.
        
        Args:
            consecutive_429_errors (int): Number of consecutive 429 errors
            last_429_time (float): Timestamp of last 429 error
            
        Returns:
            bool: True if session recovery should be applied
        """
        import time
        now = time.time()
        return (consecutive_429_errors >= self.get_error_threshold() and 
                (now - last_429_time) < 300)  # 5 minutes
    
    def get_mode_info(self) -> Dict[str, Any]:
        """Get information about the current mode.
        
        Returns:
            Dict[str, Any]: Mode information
        """
        return {
            'mode': self.mode,
            'base_delay_range': f"{self.settings['base_delay_min']}-{self.settings['base_delay_max']}s",
            'batch_delay': f"{self.batch_delay}s + {self.settings['batch_delay_jitter']}s jitter",
            'session_recovery': f"{self.settings['session_recovery_delay']}s",
            'error_threshold': self.settings['error_threshold'],
            'adaptive_factor': self.settings['adaptive_factor']
        }
