from jarvis_os.computer.computer_models import ComputerSnapshot, AnalysisResult

class ComputerAnalyzer:
    """
    Deterministic rules. NO AI.
    Analyzes the hardware snapshot to build human-readable state flags and summaries.
    """
    def analyze_computer_state(self, snapshot: ComputerSnapshot) -> AnalysisResult:
        flags = []
        
        if snapshot.cpu.percent > 85.0:
            flags.append("high_load")
            
        if snapshot.memory.percent > 90.0:
            flags.append("memory_pressure")
            
        if snapshot.battery.exists and not snapshot.battery.power_plugged and snapshot.battery.percent < 20.0:
            flags.append("low_battery")
            
        if not snapshot.battery.exists or snapshot.battery.power_plugged:
            flags.append("desktop_mode")
            
        if len(snapshot.applications) >= 8:
            flags.append("multitasking")
            
        if snapshot.disk.percent > 95.0:
            flags.append("storage_critical")
            
        summary = self.build_computer_summary(snapshot, flags)
        
        return AnalysisResult(
            state_flags=flags,
            summary=summary
        )
        
    def build_computer_summary(self, snapshot: ComputerSnapshot, flags: list) -> str:
        """
        Human Summary Function
        Constructs a plain-english summary of the hardware state.
        """
        cpu_str = "high" if "high_load" in flags else "normal"
        mem_str = "high" if "memory_pressure" in flags else "moderate"
        apps_count = len(snapshot.applications)
        
        summary = f"Boss, CPU usage is {cpu_str}. {apps_count} applications are running. Memory usage is {mem_str}."
        
        if "low_battery" in flags:
            summary += " Warning: Battery is critically low."
            
        if "desktop_mode" in flags:
            summary += " System is in desktop mode (AC power)."
            
        return summary
