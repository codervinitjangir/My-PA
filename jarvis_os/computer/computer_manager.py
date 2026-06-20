from jarvis_os.computer.computer_snapshot import SnapshotSystem
from jarvis_os.computer.computer_analyzer import ComputerAnalyzer
from jarvis_os.computer.computer_models import AnalysisResult, ComputerSnapshot
from typing import Tuple

class ComputerManager:
    """
    Core manager for the Computer Awareness Layer.
    Only allows observing and analyzing the hardware state. NO CONTROL.
    """
    def __init__(self):
        self.snapshot_system = SnapshotSystem()
        self.analyzer = ComputerAnalyzer()
        
    def observe_and_analyze(self) -> Tuple[ComputerSnapshot, AnalysisResult]:
        """
        Generates a hardware snapshot and analyzes it via deterministic rules.
        """
        snapshot = self.snapshot_system.create_snapshot()
        analysis = self.analyzer.analyze_computer_state(snapshot)
        return snapshot, analysis
