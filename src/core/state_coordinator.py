# src/core/state_coordinator.py

import time
from PySide6.QtCore import QObject, Signal, QTimer
from .models import AppState

class ConnectionStateMachine(QObject):
    """
    Formal, centralized State Machine transition controller for Tailscale/Headscale Client.
    Manages transition guards, timeout ownership, retry ownership, explicit side effects,
    and reconnect policies.
    """
    state_changed = Signal(AppState)

    def __init__(self, coordinator, ts_manager):
        super().__init__()
        self.coordinator = coordinator
        self.ts_manager = ts_manager
        self._state = AppState.DISCONNECTED
        self._retry_count = 0
        self._max_retries = 3
        
        # SSO Timeout Timer owned by State Machine
        self.sso_timer = QTimer(self)
        self.sso_timer.setSingleShot(True)
        self.sso_timer.timeout.connect(self._on_sso_timeout)
        
        # Reconnect Timer owned by State Machine
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.setSingleShot(True)
        self.reconnect_timer.timeout.connect(self._on_reconnect_timer_fired)
        
        self.last_connect_args = None

    @property
    def state(self):
        return self._state

    def transition_to(self, new_state, info_text="", force=False):
        """
        Transition function with Guards, Timeout/Retry Ownership, Reconnect Policies, and Side Effects.
        """
        old_state = self._state
        if old_state == new_state and not force:
            return True
            
        # 1. TRANSITION GUARDS (Validate if transition is allowed)
        if not force and not self._check_transition_guard(old_state, new_state):
            # Block invalid transition silently to prevent race conditions or stale states
            return False
            
        # 2. STATE EXIT SIDE EFFECTS (Perform cleanups when leaving certain states)
        self._on_state_exit(old_state, new_state)
        
        # Apply state change
        self._state = new_state
        
        # 3. STATE ENTRY SIDE EFFECTS & ACTIONS (Trigger timeouts, retries, or side effects)
        self._on_state_entry(old_state, new_state, info_text)
        
        # Emit signal to notify views and coordinators
        self.state_changed.emit(new_state)
        return True

    def _check_transition_guard(self, old_state, new_state):
        """
        Guards that prevent race conditions, reconnect loops, and stale state transitions.
        """
        # Guard: Cannot transition to CONNECTED directly from LOGGED_OUT without CONNECTING
        if old_state == AppState.LOGGED_OUT and new_state == AppState.CONNECTED:
            return False
            
        # Guard: Cannot trigger redundant CONNECTING transition if already CONNECTING
        if old_state == AppState.CONNECTING and new_state == AppState.CONNECTING:
            return False
            
        # Guard: If already DISCONNECTED, ignore redundant DISCONNECTED transitions
        if old_state == AppState.DISCONNECTED and new_state == AppState.DISCONNECTED:
            return False
            
        return True

    def _on_state_exit(self, old_state, new_state):
        """
        Clean up timers and state variables upon exiting a state.
        """
        if old_state == AppState.CONNECTING:
            # Stop the SSO timeout timer immediately when leaving CONNECTING
            self.sso_timer.stop()
            
        if old_state == AppState.ERROR:
            # Stop any pending reconnect timers
            self.reconnect_timer.stop()

    def _on_state_entry(self, old_state, new_state, info_text):
        """
        Trigger actions, retry policies, and timeouts upon entering a state.
        """
        if new_state == AppState.CONNECTED:
            # Reset reconnect count upon successful connection
            self._retry_count = 0
            self.sso_timer.stop()
            self.reconnect_timer.stop()
            
        elif new_state == AppState.CONNECTING:
            # Start SSO login timeout timer
            sso_time = getattr(self.coordinator.manager.settings, 'sso_timeout', 120)
            self.sso_timer.start(sso_time * 1000)
            
        elif new_state == AppState.ERROR:
            # Implement Exponential Backoff Reconnect Policy
            self._handle_reconnect_policy(info_text)

    def _handle_reconnect_policy(self, error_msg):
        """
        Defines the reconnect policy using exponential backoff to avoid flood loops.
        """
        if self.last_connect_args and self._retry_count < self._max_retries:
            self._retry_count += 1
            # Exponential Backoff delay: 3s, 6s, 12s
            delay = (2 ** (self._retry_count - 1)) * 3000
            
            # Notify of auto reconnect attempt
            self.ts_manager.worker.error_received.emit(
                f"Connection lost: {error_msg}. "
                f"Retrying automatically (Attempt {self._retry_count}/{self._max_retries}) in {delay/1000:.0f}s..."
            )
            self.reconnect_timer.start(delay)
        else:
            # Max retries reached or no connection arguments, stay in ERROR state
            self.ts_manager.worker.error_received.emit("Maximum reconnection attempts reached. Please connect manually.")
            self._retry_count = 0

    def _on_sso_timeout(self):
        """SSO Timeout ownership callback."""
        if self._state == AppState.CONNECTING:
            self.ts_manager.worker.cleanup()
            self.transition_to(AppState.ERROR, "SSO Login timed out.")
            self.ts_manager.worker.error_received.emit("SSO Login timed out. Please try connecting again.")

    def _on_reconnect_timer_fired(self):
        """Retry execution callback."""
        if self.last_connect_args:
            # Safeguard: Force state to CONNECTING before retrying
            self.transition_to(AppState.CONNECTING, force=True)
            self.ts_manager.connect(
                login_server=self.last_connect_args.get("login_server"),
                auth_key=self.last_connect_args.get("auth_key"),
                use_sso=self.last_connect_args.get("use_sso"),
                profile_name=self.last_connect_args.get("profile_name"),
                exit_node=self.last_connect_args.get("exit_node"),
                routes=self.last_connect_args.get("routes")
            )


class StateCoordinator(QObject):
    """
    Decoupled State Coordinator that centralizes all app states,
    caches background status queries to prevent CPU spikes,
    and coordinates state changes through the formal ConnectionStateMachine.
    """
    connection_status_changed = Signal(bool, str)
    state_changed = Signal(object)
    
    def __init__(self, manager, ts_manager):
        super().__init__()
        self.manager = manager
        self.ts_manager = ts_manager
        
        # Instantiate and coordinate via formal State Machine Transition Controller
        self.state_machine = ConnectionStateMachine(self, ts_manager)
        self.state_machine.state_changed.connect(self._on_state_machine_changed)
        
        # Forward signals from real manager to views
        self.ts_manager.connection_status_changed.connect(self._on_status_changed)
        
        # Cache status to prevent multiple background processes
        self._cached_status = None
        self._last_status_query_time = 0
        self._query_cooldown_seconds = 2.0  # Coalesce queries within 2 seconds
        
        # Self-healing and Observability metrics
        self._last_tick_time = time.time()
        self._last_adapters = []
        self._observability_metrics = {
            'reconnect_count': 0,
            'relay_usage_pct': 0,
            'auth_failures': 0,
            'latency_spikes': 0,
            'daemon_restart_count': 0
        }
        
    @property
    def worker(self):
        return self.ts_manager.worker

    @property
    def current_state(self):
        return self.state_machine.state

    @property
    def use_local_api(self):
        return self.ts_manager.use_local_api

    @use_local_api.setter
    def use_local_api(self, val):
        self.ts_manager.use_local_api = val

    @property
    def sso_timeout(self):
        return self.ts_manager.sso_timeout

    @use_local_api.setter
    def sso_timeout(self, val):
        self.ts_manager.sso_timeout = val

    @property
    def cache(self):
        return self.ts_manager.cache

    def start_service(self):
        self.ts_manager.start_service()

    def logout_sync(self):
        self._cached_status = None
        self.state_machine.transition_to(AppState.LOGGED_OUT, force=True)
        self.ts_manager.logout_sync()

    def check_status(self):
        """
        Deduplicates and coalesces status queries. If a query is requested 
        within the cooldown window, returns the cached result immediately 
        without spawning a background process, eliminating CPU spikes.
        
        Also acts as an active watchdog for system sleep/wake and network changes.
        """
        now = time.time()
        
        # 1. Sleep/Wake Sensor Watchdog
        if (now - self._last_tick_time) > 10.0:
            # Detected system wakeup! Invalidate cache and trigger reconnect
            self._observability_metrics['reconnect_count'] += 1
            self._cached_status = None
            QTimer.singleShot(0, self.check_status_sync)
        self._last_tick_time = now
        
        # 2. WiFi / Network Switch Watchdog
        try:
            import psutil
            current_adapters = list(psutil.net_if_addrs().keys())
            if self._last_adapters and self._last_adapters != current_adapters:
                # Network adapter changed! Clear cache to force clean state refresh
                self._cached_status = None
            self._last_adapters = current_adapters
        except Exception:
            pass
            
        if self._cached_status is not None and (now - self._last_status_query_time) < self._query_cooldown_seconds:
            return self._cached_status
            
        status = self.ts_manager.check_status()
        self._cached_status = status
        self._last_status_query_time = now
        return status

    def check_status_sync(self):
        return self.ts_manager.check_status_sync()

    def connect(self, login_server, auth_key=None, use_sso=False, profile_name=None, exit_node=None, routes=None):
        self._cached_status = None  # Invalidate cache on action
        
        # Register connection arguments with the State Machine
        self.state_machine.last_connect_args = {
            "login_server": login_server,
            "auth_key": auth_key,
            "use_sso": use_sso,
            "profile_name": profile_name,
            "exit_node": exit_node,
            "routes": routes
        }
        
        # Transition to CONNECTING state via State Machine transition controller
        self.state_machine.transition_to(AppState.CONNECTING, force=True)
        
        self.ts_manager.connect(
            login_server=login_server,
            auth_key=auth_key,
            use_sso=use_sso,
            profile_name=profile_name,
            exit_node=exit_node,
            routes=routes
        )

    def switch_profile(self, native_profile_name, profile_name=None):
        self._cached_status = None
        self.state_machine.transition_to(AppState.CONNECTING, force=True)
        self.ts_manager.switch_profile(native_profile_name, profile_name)

    def logout(self, profile_name=None):
        self._cached_status = None
        self.state_machine.transition_to(AppState.LOGGED_OUT, force=True)
        self.ts_manager.logout(profile_name)

    def cleanup(self):
        self.ts_manager.cleanup()

    def get_stats(self):
        return self.ts_manager.get_stats()

    def _on_status_changed(self, is_connected, status_text):
        self._cached_status = (is_connected, status_text)
        self._last_status_query_time = time.time()
        
        # Drive the state machine based on incoming connection status text
        new_state = AppState.DISCONNECTED
        if status_text == "Connected":
            new_state = AppState.CONNECTED
        elif status_text == "Connecting...":
            new_state = AppState.CONNECTING
        elif status_text == "Logged Out":
            new_state = AppState.LOGGED_OUT
        elif status_text == "Pending Admin Approval":
            new_state = AppState.PENDING_APPROVAL
        elif "error" in status_text.lower():
            new_state = AppState.ERROR
            
        self.state_machine.transition_to(new_state, status_text)
        self.connection_status_changed.emit(is_connected, status_text)

    def _on_state_machine_changed(self, state):
        self.state_changed.emit(state)
