# CN-Monitoring-System
Final project of Computer Network course at Amirkabir University of Technology. THe project is the implementation of a monitoring prometheus metric client that receive metrics from different agent and merge them in prometheus metrics and expose them for Prometheus Scraper.

## Requirements
```
prometheus-client
psutil
```
You can install them just by entering:
```bash
pip install -r requirements.txt
```

## How to use it?
To run this project, at first, you should run metric_server to initiate a MetricServer and start to listen for metrics of other agents.
```bash
python3 metric_server.py
```

then in separate shell, run metric_agent to initiate a MetricAgent to extract metrics from the system and send them to the MetricServer. You can pass a name and an interval (in seconds) to this agents. If you don't do that, based on current time, a hash code assigned to it and default interval is set to 2 seconds.
```bash
python3 metric_agent.py <agent_name:str> <agent_interval:int>
```

## Metrics
- Percentage of CPU Utilization
- CPUs Average Frequency
- CPU Temperature
- CPU Fan Speed
- Percentage of Memory Usage
- Bytes of Memory Used
- Percentage of Swap Usage
- Bytes of Swap Used
- \# of Packets Sent over Network
- \# of Packets Received over Network
- \# of Connections (INET connections)
- Percentage of Battery Power
