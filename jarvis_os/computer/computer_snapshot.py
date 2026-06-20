from jarvis_os.computer.computer_observer import ComputerObserver
from jarvis_os.computer.computer_models import ComputerSnapshot

class SnapshotSystem:
    def __init__(self):
        self.observer = ComputerObserver()
        
    def create_snapshot(self) -> ComputerSnapshot:
        return ComputerSnapshot(
            system=self.observer.get_system_info(),
            cpu=self.observer.get_cpu_usage(),
            memory=self.observer.get_memory_usage(),
            disk=self.observer.get_disk_usage(),
            battery=self.observer.get_battery_status(),
            network=self.observer.get_network_status(),
            applications=self.observer.get_running_applications()
        )
